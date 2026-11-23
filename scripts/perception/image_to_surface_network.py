"""Image-only, known-shape complete surface estimator prototype.

Templates and camera intrinsics are configuration buffers, not per-image pose
inputs. A full-frame encoder predicts attention centers, differentiable native
image crops provide detail, and independent pose heads place complete templates.
No scale or unconstrained deformation is predicted. Weights require training.
"""
import json
from pathlib import Path
import numpy as np
import torch
from torch import nn
from torch.nn import functional as F
from torchvision.models import resnet18


def rotation_6d(d):
    """First two ROWS, matching the PyTorch3D convention; robust degenerate fallback."""
    a,b=d[...,:3],d[...,3:]
    default=torch.zeros_like(a);default[...,0]=1
    e1=torch.where(a.norm(dim=-1,keepdim=True)>1e-6,F.normalize(a,dim=-1),default)
    v=b-(e1*b).sum(-1,keepdim=True)*e1
    basis=F.one_hot(e1.abs().argmin(-1),3).to(d.dtype)
    fallback=F.normalize(basis-(basis*e1).sum(-1,keepdim=True)*e1,dim=-1)
    e2=torch.where(v.norm(dim=-1,keepdim=True)>1e-6,F.normalize(v,dim=-1),fallback)
    return torch.stack([e1,e2,torch.linalg.cross(e1,e2,dim=-1)],dim=-2)


def fisheye_rays(pixels,K,D):
    x=(pixels[...,0]-K[0,2])/K[0,0];y=(pixels[...,1]-K[1,2])/K[1,1]
    r=torch.sqrt(x*x+y*y+1e-12);theta=r.clamp(max=1.5)
    for _ in range(8):
        t2=theta*theta
        value=theta*(1+D[0]*t2+D[1]*t2**2+D[2]*t2**3+D[3]*t2**4)
        deriv=1+3*D[0]*t2+5*D[1]*t2**2+7*D[2]*t2**3+9*D[3]*t2**4
        theta=(theta-(value-r)/deriv.clamp(min=.05)).clamp(0,1.5)
    scale=torch.tan(theta)/r
    return torch.stack([x*scale,y*scale,torch.ones_like(x)],-1)


def project_fisheye(points,K,D):
    xy=points[...,:2]/points[...,2:].clamp(min=1e-5)
    r=torch.sqrt((xy*xy).sum(-1)+1e-12);t=torch.atan(r);t2=t*t
    td=t*(1+D[0]*t2+D[1]*t2**2+D[2]*t2**3+D[3]*t2**4)
    warped=xy*(td/r)[...,None]
    return torch.stack([K[0,0]*warped[...,0]+K[0,2],K[1,1]*warped[...,1]+K[1,2]],-1)


class Encoder(nn.Module):
    def __init__(self):
        super().__init__();r=resnet18(weights=None)
        self.stem=nn.Sequential(r.conv1,r.bn1,r.relu,r.maxpool)
        self.layer1=r.layer1;self.layer2=r.layer2;self.layer3=r.layer3;self.layer4=r.layer4

    def forward(self,x):
        f=self.layer2(self.layer1(self.stem(x)));g=self.layer4(self.layer3(f))
        return f,g


class ImageToCompleteSurface(nn.Module):
    def __init__(self,template_dir,calibration,counts=None):
        super().__init__();template_dir=Path(template_dir)
        self.spec=json.loads((template_dir/'manifest.json').read_text())
        self.names=('module','socket');self.counts=counts or self.spec['recommended_counts']
        self.encoder=Encoder();self.context=nn.Conv2d(512,64,1);self.attention=nn.Conv2d(130,2,1)
        self.pose_heads=nn.ModuleDict();self.visibility_heads=nn.ModuleDict()
        self.register_buffer('K',torch.tensor(calibration['K'],dtype=torch.float32).reshape(3,3))
        self.register_buffer('D',torch.tensor(calibration['D'],dtype=torch.float32))
        self.image_size=(int(calibration['image_width']),int(calibration['image_height']))
        self.register_buffer('mean',torch.tensor([.485,.456,.406]).reshape(1,3,1,1))
        self.register_buffer('std',torch.tensor([.229,.224,.225]).reshape(1,3,1,1))
        self.register_buffer('attention_prior_centers',torch.zeros(2,2))
        self.register_buffer('attention_prior_enabled',torch.tensor(False))
        # These are crop extents in normalized full-image coordinates, not
        # provided boxes or pose annotations. Centers come from image attention.
        self.crop_scales={'module':(.20,.38),'socket':(.32,.48)}
        self.feature_heads=nn.ModuleDict()
        for i,name in enumerate(self.names):
            with np.load(template_dir/f'{name}_{self.counts[name]}.npz') as a:
                self.register_buffer(name+'_template',torch.from_numpy(a['points_m'].copy()))
                self.register_buffer(name+'_normals',torch.from_numpy(a['normals'].copy()))
                levels=a['representation_level'].copy() if 'representation_level' in a.files else np.zeros(len(a['points_m']),dtype=np.uint8)
                self.register_buffer(name+'_levels',torch.from_numpy(levels))
            self.feature_heads[name]=nn.Sequential(nn.Linear(64*4*6+128+512,256),nn.SiLU(),nn.Linear(256,128),nn.SiLU())
            self.pose_heads[name]=nn.Linear(128,10)
            self.visibility_heads[name]=nn.Sequential(nn.Linear(128+128+6,64),nn.SiLU(),nn.Linear(64,1))
            nn.init.normal_(self.pose_heads[name].weight,std=.001);nn.init.zeros_(self.pose_heads[name].bias)
            # A positive depth and front-facing orientation are initial biases,
            # not a learned scene estimate and not copied from annotations.
            with torch.no_grad():
                self.pose_heads[name].bias[2]=torch.log(torch.expm1(torch.tensor(.25 if i==0 else .40)))
                self.pose_heads[name].bias[3:9]=torch.tensor([-1.,0,0,0,1,0])
        self.weights_status='untrained_prototype'

    def initialize_from_training_prior(self,transforms):
        """Initialize only from TRAIN-set means; inference still receives RGB only."""
        with torch.no_grad():
            nn.init.zeros_(self.attention.weight);nn.init.zeros_(self.attention.bias)
            yy,xx=torch.meshgrid((torch.arange(45,dtype=self.K.dtype,device=self.K.device)+.5)/45*2-1,(torch.arange(80,dtype=self.K.dtype,device=self.K.device)+.5)/80*2-1,indexing='ij')
            grid=torch.stack([xx,yy],-1).reshape(-1,2);size=torch.tensor(self.image_size,device=self.K.device,dtype=self.K.dtype)
            for i,name in enumerate(self.names):
                T=transforms[name].to(self.K);pixels=project_fisheye(T[None,:3,3],self.K,self.D)[0];center=2*(pixels+.5)/size-1
                self.attention_prior_centers[i]=center
                probabilities=(-((grid-center)/.22).square().sum(-1)/2).softmax(0);actual=probabilities@grid
                self.pose_heads[name].bias[:2]=torch.atanh(((center-actual)/.2).clamp(-.95,.95))
                self.pose_heads[name].bias[2]=torch.log(torch.expm1((T[2,3]-.05).clamp(min=.01)))
                self.pose_heads[name].bias[3:9]=T[:2,:3].reshape(6)
            self.attention_prior_enabled.fill_(True)

    def load_pretrained_encoder(self,state):
        mapped={}
        for key in self.encoder.state_dict():
            source=key.replace('stem.0.','conv1.').replace('stem.1.','bn1.')
            if source in state:mapped[key]=state[source]
            elif key.endswith('num_batches_tracked'):mapped[key]=self.encoder.state_dict()[key]
            else:raise KeyError('Missing pretrained encoder parameter: '+source)
        self.encoder.load_state_dict(mapped,strict=True)

    def _estimate(self,images):
        """Only dynamic input: RGB float tensor [B,3,H,W], values in [0,1]."""
        if images.ndim!=4 or images.shape[1]!=3:raise ValueError('Expected B x 3 x H x W RGB')
        if not images.is_floating_point() or not torch.isfinite(images).all() or images.min()<0 or images.max()>1:
            raise ValueError('RGB input must be finite floating point values in [0,1]')
        if tuple(images.shape[-2:])!=(self.image_size[1],self.image_size[0]):
            raise ValueError('Input resolution must match the camera configuration; resize inside this model only')
        small=F.interpolate(images,size=(360,640),mode='bilinear',align_corners=False)
        f,g=self.encoder((small-self.mean)/self.std);B,C,H,W=f.shape
        yy,xx=torch.meshgrid((torch.arange(H,device=f.device,dtype=f.dtype)+.5)/H*2-1,(torch.arange(W,device=f.device,dtype=f.dtype)+.5)/W*2-1,indexing='ij')
        grid=torch.stack([xx,yy],-1).reshape(-1,2)
        logits=self.attention(torch.cat([f,grid.T.reshape(1,2,H,W).expand(B,-1,-1,-1)],1))
        if bool(self.attention_prior_enabled):
            prior=-((grid[None]-self.attention_prior_centers[:,None])/.22).square().sum(-1)/2
            logits=logits+prior.reshape(1,2,H,W)
        attention=logits.flatten(2).softmax(-1);centers=attention@grid
        attended=torch.einsum('bon,bcn->boc',attention,f.flatten(2))
        context=F.adaptive_avg_pool2d(self.context(g),(4,6)).flatten(1)
        results={};details={}
        for i,name in enumerate(self.names):
            center=centers[:,i];sx,sy=self.crop_scales[name]
            affine=torch.zeros(B,2,3,device=f.device,dtype=f.dtype)
            affine[:,0,0]=sx;affine[:,1,1]=sy;affine[:,:,2]=center
            crop_grid=F.affine_grid(affine,(B,3,224,224),align_corners=False)
            crop=F.grid_sample(images,crop_grid,align_corners=False,padding_mode='zeros')
            local_features,local_global=self.encoder((crop-self.mean)/self.std)
            feature=self.feature_heads[name](torch.cat([context,attended[:,i],local_global.mean((-1,-2))],-1))
            raw=self.pose_heads[name](feature)
            center_refined=(center+.2*raw[:,:2].tanh()).clamp(-.98,.98)
            size=torch.tensor(self.image_size,device=f.device,dtype=f.dtype)
            pixels=(center_refined+1)*.5*size-.5
            depth=.05+F.softplus(raw[:,2:3]);t=fisheye_rays(pixels,self.K,self.D)*depth
            R=rotation_6d(raw[:,3:9])
            T=torch.eye(4,device=f.device,dtype=f.dtype).repeat(B,1,1);T[:,:3,:3]=R;T[:,:3,3]=t
            results[name]={'T_camera_from_model':T,'presence_logits':raw[:,9],
                           'crop_center_normalized':center,'center_pixels':pixels}
            details[name]=(local_features,feature,center)
        return results,details

    def estimate_poses(self,images):
        """Training fast path: avoid computing unsupervised dense visibility heads."""
        return self._estimate(images)[0]

    def forward(self,images):
        results,details=self._estimate(images)
        for name in self.names:
            o=results[name];T=o['T_camera_from_model'];R=T[:,:3,:3];t=T[:,:3,3]
            local_features,feature,center=details[name];B=len(images);sx,sy=self.crop_scales[name]
            template=getattr(self,name+'_template');normals=getattr(self,name+'_normals')
            points=torch.einsum('bij,nj->bni',R,template)+t[:,None,:]
            camera_normals=torch.einsum('bij,nj->bni',R,normals)
            size=torch.tensor(self.image_size,device=images.device,dtype=images.dtype)
            projected=project_fisheye(points,self.K,self.D);raw_grid=2*(projected+.5)/size-1
            point_grid=(raw_grid-center[:,None,:])/torch.tensor([sx,sy],device=images.device,dtype=images.dtype)
            image_features=F.grid_sample(local_features,point_grid.unsqueeze(2),align_corners=False,padding_mode='zeros').squeeze(-1).transpose(1,2)
            shape_features=torch.cat([template/.1,normals],-1)[None].expand(B,-1,-1)
            visibility=self.visibility_heads[name](torch.cat([image_features,feature[:,None,:].expand(-1,len(template),-1),shape_features],-1)).squeeze(-1)
            results[name].update(points_m=points,normals=camera_normals,visibility_logits=visibility,
                           representation_level=getattr(self,name+'_levels')[None].expand(B,-1),
                           projected_pixels=projected,points_in_front=points[...,2]>.001)
        return results


def supervised_surface_loss(predictions,target_transforms,templates,valid=None,level_weights=(.2,.5,.3)):
    """Correspondence-aware metric point loss, not a free-shape Chamfer fit.

    Target transforms must have been reviewed separately. Do not silently use
    incomplete stereo observations as complete surface supervision.
    """
    losses=[]
    for name,pred in predictions.items():
        if name not in target_transforms:continue
        T=target_transforms[name];p=templates[name]
        target=torch.einsum('bij,nj->bni',T[:,:3,:3],p)+T[:,None,:3,3]
        per_point=F.smooth_l1_loss(pred['points_m']*1000,target*1000,reduction='none',beta=1).mean(2)
        levels=pred.get('representation_level')
        if levels is None:
            error=per_point.mean(1)
        else:
            if levels.ndim==1:levels=levels[None].expand_as(per_point)
            if levels.shape!=per_point.shape or levels.min()<0 or levels.max()>2:raise ValueError('Expected global/surface/edge levels 0/1/2')
            error=torch.zeros_like(per_point[:,0]);normalizer=torch.zeros_like(error)
            for level,weight in enumerate(level_weights):
                included=levels==level;count=included.sum(1);active=(count>0).to(error.dtype)
                error+=weight*(per_point*included).sum(1)/count.clamp(min=1);normalizer+=weight*active
            error=error/normalizer.clamp(min=1e-8)
        mask=torch.ones_like(error,dtype=torch.bool) if valid is None else valid[name].bool()
        if mask.any():losses.append(error[mask].mean())
    if not losses:raise ValueError('No valid reviewed pose supervision in this batch')
    return torch.stack(losses).mean()


def require_reviewed_annotation(annotation):
    if annotation.get('training_label_valid') is not True:
        raise ValueError('Candidate or merely visually reviewed annotation is not valid training supervision')
    return annotation
