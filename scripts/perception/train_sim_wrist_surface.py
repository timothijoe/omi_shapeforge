"""Train image-only two-object pose / complete-surface prediction on sim videos.

Only RGB enters the model. Privileged poses are supervision and evaluation.
Normalization and initial pose/attention priors use the training split only.
"""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import time
import numpy as np
from PIL import Image
import torch
from torch import nn
from torch.nn import functional as F
from torch.utils.data import Dataset,DataLoader
from image_to_surface_network import ImageToCompleteSurface,project_fisheye,supervised_surface_loss


def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
NAMES=('module','socket')


class Frames(Dataset):
    def __init__(self,root,rows):self.root=Path(root);self.rows=rows
    def __len__(self):return len(self.rows)
    def __getitem__(self,i):
        r=self.rows[i]
        if r.get('training_label_valid') is not True or r.get('real_world_ground_truth') is not False:raise ValueError('Not an approved simulation label')
        im=np.asarray(Image.open(self.root/r['image']).convert('RGB')).copy()
        T=np.array([r['T_camera_from_module'],r['T_camera_from_socket']],np.float32)
        return torch.from_numpy(im).permute(2,0,1),torch.from_numpy(T),r['id']


def training_statistics(rows):
    result={}
    for name in NAMES:
        matrices=np.array([r['T_camera_from_'+name] for r in rows]);u,_,vt=np.linalg.svd(matrices[:,:3,:3].mean(0));R=u@vt
        if np.linalg.det(R)<0:u[:,-1]*=-1;R=u@vt
        mean=np.eye(4);mean[:3,:3]=R;mean[:3,3]=matrices[:,:3,3].mean(0)
        std=np.maximum(matrices[:,:3,3].std(0),.0005)
        rotation_scale=max(float(np.sqrt(np.mean((matrices[:,:3,:3]-R)**2))),.01)
        result[name]={'mean_T':mean.tolist(),'translation_std_m':std.tolist(),'rotation_matrix_std':rotation_scale}
    return result


def freeze_bn(module):
    if isinstance(module,nn.BatchNorm2d):module.eval()


def errors(pred,gt):
    # Double precision keeps very small angles from the acos trace numerics.
    pred=pred.double();gt=gt.double();dt=torch.linalg.vector_norm(pred[:,:,:3,3]-gt[:,:,:3,3],dim=-1)*1000
    dr=pred[:,:,:3,:3]@gt[:,:,:3,:3].transpose(-1,-2);angle=torch.acos(((dr.diagonal(dim1=-2,dim2=-1).sum(-1)-1)/2).clamp(-1,1))*180/np.pi
    tip=torch.tensor([0,-.0350931697,0],dtype=pred.dtype,device=pred.device)
    def relative(T):
        R=T[:,1,:3,:3].transpose(-1,-2)@T[:,0,:3,:3]
        t=(T[:,1,:3,:3].transpose(-1,-2)@(T[:,0,:3,3]-T[:,1,:3,3]).unsqueeze(-1)).squeeze(-1)
        return R@tip+t
    rel=relative(pred)-relative(gt)
    return {'translation_mm':dt.cpu().numpy(),'rotation_deg':angle.cpu().numpy(),'tip_in_socket_error_mm':(rel.norm(dim=-1)*1000).cpu().numpy(),'tip_axis_error_mm':(rel.abs()*1000).cpu().numpy()}


def summarize(e):
    result={}
    for i,name in enumerate(NAMES):
        result[name]={}
        for key in ['translation_mm','rotation_deg']:
            a=e[key][:,i];result[name][key]={'mean':float(a.mean()),'median':float(np.median(a)),'p90':float(np.quantile(a,.9))}
    a=e['tip_in_socket_error_mm'];result['relative_tip_error_mm']={'mean':float(a.mean()),'median':float(np.median(a)),'p90':float(np.quantile(a,.9))}
    result['relative_tip_axis_mae_mm']=e['tip_axis_error_mm'].mean(0).tolist()
    return result


@torch.no_grad()
def evaluate(model,loader,device,mean_pose):
    model.eval();predictions=[];truth=[];indices=[]
    for images,T,idx in loader:
        out=model.estimate_poses(images.to(device,non_blocking=True).float()/255)
        predictions.append(torch.stack([out[n]['T_camera_from_model'] for n in NAMES],1).cpu());truth.append(T);indices.append(idx)
    pred=torch.cat(predictions);gt=torch.cat(truth);idx=torch.cat(indices)
    model_errors=errors(pred,gt);baseline_errors=errors(mean_pose[None].expand(len(gt),-1,-1,-1),gt)
    return {'network':summarize(model_errors),'constant_train_mean':summarize(baseline_errors),'frames':len(gt)}, {'pred':pred.numpy(),'gt':gt.numpy(),'frame_ids':idx.numpy(),**model_errors}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--data',type=Path,required=True);p.add_argument('--templates',type=Path,default=Path('/data/omi_runtime/runs/interaction_surface_representation_20261122/network_templates'));p.add_argument('--output',type=Path,required=True);p.add_argument('--epochs',type=int,default=25);p.add_argument('--batch-size',type=int,default=16);p.add_argument('--workers',type=int,default=4);p.add_argument('--seed',type=int,default=5221);p.add_argument('--encoder-lr',type=float,default=3e-5);p.add_argument('--head-lr',type=float,default=3e-4);p.add_argument('--pretrained',type=Path,default=Path('/data/omi_runtime/models/vision/resnet18-f37072fd.pth'));p.add_argument('--resume',type=Path);p.add_argument('--init-checkpoint',type=Path,help='Warm-start learned parameters only; new data, templates, optimizer and training priors');a=p.parse_args()
    if a.resume and a.init_checkpoint:raise ValueError('Choose resume or new-data warm start, not both')
    if not (a.data/'complete.json').exists():raise ValueError('Capture is incomplete')
    audit=read(a.data/'label_audit.json')
    if not audit.get('accepted_for_sim_supervision'):raise ValueError('Dataset labels not audited')
    a.output.mkdir(parents=True,exist_ok=a.resume is not None);torch.set_num_threads(4);torch.manual_seed(a.seed);np.random.seed(a.seed)
    device='cuda' if torch.cuda.is_available() else 'cpu';torch.backends.cudnn.benchmark=True
    rows=[json.loads(s) for s in (a.data/'records.jsonl').read_text().splitlines()]
    splits={s:[r for r in rows if r['split']==s] for s in ['train','val','test']}
    if not all(splits.values()):raise ValueError('Need nonempty train, validation and test splits')
    stats=training_statistics(splits['train']);cal=read(a.data/'calibration.json')
    model=ImageToCompleteSurface(a.templates,cal);model.load_pretrained_encoder(torch.load(a.pretrained,map_location='cpu',weights_only=True))
    model.initialize_from_training_prior({n:torch.tensor(stats[n]['mean_T'],dtype=torch.float32) for n in NAMES})
    initialization=None
    if a.init_checkpoint:
        previous=torch.load(a.init_checkpoint,map_location='cpu',weights_only=True)
        weights=previous['model'];loaded=[]
        with torch.no_grad():
            for name,param in model.named_parameters():
                if name not in weights or weights[name].shape!=param.shape:raise ValueError('Warm-start parameter mismatch: '+name)
                param.copy_(weights[name]);loaded.append(name)
        # Preserve frozen encoder normalization learned in the parent model.
        with torch.no_grad():
            for name,buffer in model.named_buffers():
                if name.startswith('encoder.') and name in weights:buffer.copy_(weights[name])
        initialization={'checkpoint':str(a.init_checkpoint),'sha256':sha(a.init_checkpoint),'learned_parameter_tensors':len(loaded),'new_optimizer':True,'template_and_calibration_from_new_config':True,'attention_prior_from_new_training_split':True}

    for p_ in model.visibility_heads.parameters():p_.requires_grad_(False)
    model=model.to(device)
    mean_pose=torch.tensor([stats[n]['mean_T'] for n in NAMES],dtype=torch.float32)
    position_std=torch.tensor([stats[n]['translation_std_m'] for n in NAMES],device=device,dtype=torch.float32)
    rotation_std=torch.tensor([stats[n]['rotation_matrix_std'] for n in NAMES],device=device,dtype=torch.float32)
    generator=torch.Generator().manual_seed(a.seed)
    train=DataLoader(Frames(a.data,splits['train']),batch_size=a.batch_size,shuffle=True,generator=generator,num_workers=a.workers,pin_memory=device=='cuda',persistent_workers=a.workers>0,drop_last=False)
    val=DataLoader(Frames(a.data,splits['val']),batch_size=a.batch_size,shuffle=False,num_workers=a.workers,pin_memory=device=='cuda',persistent_workers=a.workers>0)
    test=DataLoader(Frames(a.data,splits['test']),batch_size=a.batch_size,shuffle=False,num_workers=a.workers,pin_memory=device=='cuda',persistent_workers=a.workers>0)
    encoder=list(model.encoder.parameters());other=[p_ for name,p_ in model.named_parameters() if not name.startswith(('encoder.','visibility_heads.'))]
    optimizer=torch.optim.AdamW([{'params':encoder,'lr':a.encoder_lr},{'params':other,'lr':a.head_lr}],weight_decay=1e-4)
    scheduler=torch.optim.lr_scheduler.CosineAnnealingLR(optimizer,T_max=a.epochs,eta_min=3e-6)
    # Balanced fixed representative points for loss; inference still returns all
    # 22,528 / 43,008 points from the exact same learned rigid transforms.
    sampled={};levels={}
    for name in NAMES:
        level=getattr(model,name+'_levels');indices=[]
        for k,count in [(0,256),(1,512),(2,256)]:
            ids=torch.where(level==k)[0]
            if not len(ids):continue
            indices.append(ids[torch.linspace(0,len(ids)-1,min(count,len(ids)),device=device).long()])
        indices=torch.cat(indices);sampled[name]=getattr(model,name+'_template')[indices];levels[name]=level[indices]
    config={'data':str(a.data),'records_sha256':sha(a.data/'records.jsonl'),'data_config_sha256':sha(a.data/'config.json'),'templates':str(a.templates),'template_manifest_sha256':sha(a.templates/'manifest.json'),
            'training_domain':('GC-r01 dynamic contact-qualified grasp with FK robot visual context; pre-insertion only' if read(a.data/'config.json').get('contact_asset') else 'MuJoCo kinematic randomized grasp/arm rendering'),'initialization':initialization,'calibration':cal,'seed':a.seed,'epochs':a.epochs,'batch_size':a.batch_size,'pretrained':str(a.pretrained),'pretrained_sha256':sha(a.pretrained),
            'training_statistics':stats,'mean_prior_source':'train split only','image_only_at_inference':True,'privileged_pose_used_only_as_supervision':True,
            'train_frames':len(splits['train']),'val_frames':len(splits['val']),'test_frames':len(splits['test']),'test_used_for_checkpoint_selection':False,
            'visibility_head_trained':False,'presence_head_calibrated':False,'backbone_batchnorm':'frozen ImageNet running statistics','photometric_augmentation_only':True,
            'encoder_lr':a.encoder_lr,'head_lr':a.head_lr,'loss':'normalized translation + normalized rotation matrix + .1 * multiscale Huber-mm + .05 * image attention center',
            'source_hashes':{str(Path(__file__)):sha(__file__),str(Path(__file__).with_name('image_to_surface_network.py')):sha(Path(__file__).with_name('image_to_surface_network.py'))},'device':device,'torch':str(torch.__version__)}
    (a.output/'config.json').write_text(json.dumps(config,indent=2));history=[];best=float('inf');start_epoch=0;updates=0
    if a.resume:
        state=torch.load(a.resume,map_location=device,weights_only=True)
        if state['config']['records_sha256']!=config['records_sha256']:raise ValueError('Resume dataset changed')
        model.load_state_dict(state['model']);optimizer.load_state_dict(state['optimizer']);scheduler.load_state_dict(state['scheduler']);start_epoch=state['epoch']+1;updates=state['updates'];best=state['best_score'];history=state['history']
        generator.set_state(state['loader_rng'].cpu());torch.set_rng_state(state['torch_rng'].cpu())
        if device=='cuda':torch.cuda.set_rng_state_all([r.cpu() for r in state['cuda_rng']])
    started=time.time()
    initial,initial_arrays=evaluate(model,val,device,mean_pose)
    (a.output/'initial_validation.json').write_text(json.dumps(initial,indent=2))
    print(json.dumps({'stage':'initial_validation','metrics':initial}),flush=True)
    for epoch in range(start_epoch,a.epochs):
        model.train();model.apply(freeze_bn);sum_loss=0.;examples=0;epoch_start=time.time()
        for images,truth,idx in train:
            images=images.to(device,non_blocking=True).float()/255;truth=truth.to(device)
            brightness=torch.empty((len(images),1,1,1),device=device).uniform_(.9,1.1);contrast=torch.empty_like(brightness).uniform_(.9,1.1)
            images=((images-.5)*contrast+.5)*brightness;images=images.clamp(0,1)
            out=model.estimate_poses(images);pred=torch.stack([out[n]['T_camera_from_model'] for n in NAMES],1)
            position=F.smooth_l1_loss((pred[:,:,:3,3]-truth[:,:,:3,3])/position_std,torch.zeros_like(pred[:,:,:3,3]))
            rotation=F.smooth_l1_loss((pred[:,:,:3,:3]-truth[:,:,:3,:3])/rotation_std[None,:,None,None],torch.zeros_like(pred[:,:,:3,:3]))
            pc={};target={};center_losses=[]
            size=torch.tensor(model.image_size,device=device)
            for i,name in enumerate(NAMES):
                T=pred[:,i];p_=sampled[name];pc[name]={'points_m':torch.einsum('bij,nj->bni',T[:,:3,:3],p_)+T[:,None,:3,3],'representation_level':levels[name]};target[name]=truth[:,i]
                pixel=project_fisheye(truth[:,i,:3,3],model.K,model.D);center=2*(pixel+.5)/size-1
                center_losses.append(F.smooth_l1_loss((out[name]['crop_center_normalized']-center)/.04,torch.zeros_like(center)))
            point=supervised_surface_loss(pc,target,sampled)
            loss=position+rotation+.1*point+.05*torch.stack(center_losses).mean()
            if not torch.isfinite(loss):raise ValueError('Nonfinite training loss')
            optimizer.zero_grad(set_to_none=True);loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),5.);optimizer.step();updates+=1
            sum_loss+=float(loss.detach())*len(images);examples+=len(images)
        scheduler.step();validation,_=evaluate(model,val,device,mean_pose)
        score=validation['network']['relative_tip_error_mm']['mean']+.25*sum(validation['network'][n]['rotation_deg']['mean'] for n in NAMES)
        improved=score<best;best=min(best,score)
        record={'epoch':epoch+1,'updates':updates,'train_loss':sum_loss/examples,'epoch_seconds':time.time()-epoch_start,'elapsed_seconds':time.time()-started,'validation':validation,'selection_score':score,'best':improved};history.append(record)
        checkpoint={'model':model.state_dict(),'optimizer':optimizer.state_dict(),'scheduler':scheduler.state_dict(),'epoch':epoch,'updates':updates,'best_score':best,'config':config,'history':history,
                    'loader_rng':generator.get_state(),'torch_rng':torch.get_rng_state(),'cuda_rng':torch.cuda.get_rng_state_all() if device=='cuda' else []}
        torch.save(checkpoint,a.output/'last.pt')
        if improved:torch.save(checkpoint,a.output/'best.pt')
        (a.output/'history.json').write_text(json.dumps(history,indent=2));print(json.dumps(record),flush=True)
    checkpoint=torch.load(a.output/'best.pt',map_location=device,weights_only=True);model.load_state_dict(checkpoint['model']);test_metrics,test_arrays=evaluate(model,test,device,mean_pose)
    np.savez_compressed(a.output/'test_predictions.npz',**test_arrays)
    report={'status':'trained_and_heldout_simulation_evaluated','selected_epoch':checkpoint['epoch']+1,'optimizer_updates_total':updates,'selected_checkpoint_updates':checkpoint['updates'],
            'checkpoint_selection':'validation only','test_metrics':test_metrics,'training_seconds':time.time()-started,'training_performed':True,'real_image_accuracy_validated':False,
            'visibility_head_trained':False,'output_counts':model.counts,'parameters':sum(p_.numel() for p_ in model.parameters()),'checkpoint_sha256':sha(a.output/'best.pt')}
    (a.output/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)


if __name__=='__main__':main()
