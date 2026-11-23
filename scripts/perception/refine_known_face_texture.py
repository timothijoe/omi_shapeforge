"""Known-face, local 6-D refinement using reference texture and metric stereo.

Only one reference-label region is manually defined. Target-frame annotated
corners are evaluation-only. This is reference-based refinement, not blind pose
recognition or an independent metrology validation.
"""
import argparse
import json
from pathlib import Path
import time
import cv2
import numpy as np
import open3d as o3d
import torch
import torch.nn.functional as functional
import nvdiffrast.torch as dr
from scipy.spatial.transform import Rotation


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stereo-run',type=Path,required=True)
    parser.add_argument('--audit',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--initializers',type=Path,help='Known-face cloud/mask initializers; no target landmarks')
    parser.add_argument('--end-contour-weight',type=float,default=0.)
    args=parser.parse_args();root=args.output;root.mkdir(parents=True,exist_ok=False)
    base=args.stereo_run;session=Path(json.loads((base/'inventory.json').read_text())['source_session'])
    audit=json.loads((args.audit/'marker_consistency.json').read_text());ref=next(x for x in audit['rows'] if x['id']=='optical_0360')
    reference_corners=np.array(ref['corners_model_mm'])/1000
    target_annotations={x['id']:np.array(x['corners_rgb']) for x in audit['rows']+audit['rejected']}
    K=np.array(json.loads((base/'calibration.json').read_text())['K_color']);kt=torch.tensor(K,dtype=torch.float32,device='cuda')
    ref_pose=np.array(json.loads((base/'fits/optical_0360/pixel_refinement.json').read_text())['joint']['T_color_from_model'])
    image_ref=cv2.imread(str(session/'frames/optical_0360/color.png'),0).astype(np.float32)/255
    # Only the interior print drives alignment; outer corners are not fitted.
    u,v=np.meshgrid(np.linspace(.17,.83,42),np.linspace(.17,.83,46));u=u.ravel();v=v.ravel()
    xyz=(1-u[:,None])*(1-v[:,None])*reference_corners[0]+u[:,None]*(1-v[:,None])*reference_corners[1]+u[:,None]*v[:,None]*reference_corners[2]+(1-u[:,None])*v[:,None]*reference_corners[3]
    cam_ref=xyz@ref_pose[:3,:3].T+ref_pose[:3,3];uv_ref=cam_ref@K.T;uv_ref=uv_ref[:,:2]/uv_ref[:,2,None]
    points=torch.tensor(xyz,dtype=torch.float32,device='cuda')
    model=np.load(base/'model.npz');V,F=model['vertices'],model['triangles'];scene=o3d.t.geometry.RaycastingScene(nthreads=4)
    scene.add_triangles(o3d.t.geometry.TriangleMesh.from_legacy(o3d.geometry.TriangleMesh(o3d.utility.Vector3dVector(V),o3d.utility.Vector3iVector(F))))
    mesh_vertices=torch.tensor(V,dtype=torch.float32,device='cuda');mesh_faces=torch.tensor(F,dtype=torch.int32,device='cuda');ctx=dr.RasterizeCudaContext()
    records=[]
    provided_initializers=json.loads(args.initializers.read_text()) if args.initializers else None
    for name in ['optical_0270','optical_0450','optical_0885']:
        previous=json.loads((base/'fits'/name/'pixel_refinement.json').read_text());initial=np.array(previous['joint']['T_color_from_model'])
        face_flipped=name=='optical_0885'
        if face_flipped:initial=initial@np.diag([-1.,1.,-1.,1.])
        if provided_initializers is not None:
            initial=np.array(provided_initializers['poses'][name]['T_color_from_model'])
        gray=cv2.imread(str(session/'frames'/name/'color.png'),0).astype(np.float32)/255;h,w=gray.shape
        crop=json.loads((base/'fits'/name/'crop.json').read_text());Kcrop=np.array(crop['K'])
        end_mask=cv2.imread(str(base/'fits'/name/'mask_crop.png'),0)>0
        yy=np.where(end_mask)[0];end_start=int(yy.min()+.83*(yy.max()-yy.min()))
        end_target=torch.tensor(end_mask,dtype=torch.float32,device='cuda')
        end_region=torch.tensor(np.indices(end_mask.shape)[0]>=end_start,dtype=torch.float32,device='cuda')
        def end_loss(R,t):
            v=mesh_vertices@R.T+t;x,y,z=v.unbind(1)
            clip=torch.stack([2*Kcrop[0,0]/512*x+(2*Kcrop[0,2]/512-1)*z,-2*Kcrop[1,1]/512*y+(1-2*Kcrop[1,2]/512)*z,1.00002*z-.00200002,z],1)[None]
            rast,_=dr.rasterize(ctx,clip,mesh_faces,resolution=[512,512])
            pred=dr.antialias((rast[...,3:]>0).float(),rast,clip,mesh_faces)[0,...,0].flip(0)
            return (((pred-end_target)**2)*end_region).sum()/(end_target*end_region).sum().clamp(min=1)
        obs=np.load(base/'fits'/name/'observations.npz');train=obs['xyz_color'][obs['fit']];rng=np.random.default_rng(27);train=train[rng.choice(len(train),min(1000,len(train)),replace=False)]
        qt=torch.tensor(train,dtype=torch.float32,device='cuda');R0=torch.tensor(initial[:3,:3],dtype=torch.float32,device='cuda');t0=torch.tensor(initial[:3,3],dtype=torch.float32,device='cuda')
        parameters=torch.zeros(6,dtype=torch.float32,device='cuda',requires_grad=True)
        def make_pose():
            raw=parameters[:3];magnitude=torch.linalg.norm(raw)+1e-8;rv=.15*torch.tanh(magnitude)*raw/magnitude;z=rv[0]*0
            S=torch.stack([z,-rv[2],rv[1],rv[2],z,-rv[0],-rv[1],rv[0],z]).reshape(3,3)
            return torch.matrix_exp(S)@R0,t0+torch.tanh(parameters[3:])*torch.tensor([.003,.003,.006],device='cuda')
        stages=[];started=time.perf_counter()
        for sigma,steps,lr in [(2.,140,.020),(1.,180,.010),(0.,220,.004)]:
            ref_image=cv2.GaussianBlur(image_ref,(0,0),sigma) if sigma else image_ref
            target_image=cv2.GaussianBlur(gray,(0,0),sigma) if sigma else gray
            ref_values=cv2.remap(ref_image,uv_ref[:,0].astype(np.float32)[None],uv_ref[:,1].astype(np.float32)[None],cv2.INTER_LINEAR).ravel()
            ref_tensor=torch.tensor(ref_values,dtype=torch.float32,device='cuda');ref_tensor=(ref_tensor-ref_tensor.mean())/ref_tensor.std().clamp(min=.02)
            target_tensor=torch.tensor(target_image,dtype=torch.float32,device='cuda')[None,None]
            optimizer=torch.optim.Adam([parameters],lr=lr);best=None;best_loss=1e9
            for step in range(steps):
                optimizer.zero_grad();R,t=make_pose();q=points@R.T+t;uv=q@kt.T;uv=uv[:,:2]/uv[:,2:]
                grid=torch.stack([2*uv[:,0]/(w-1)-1,2*uv[:,1]/(h-1)-1],1)[None,None]
                target_values=functional.grid_sample(target_tensor,grid,align_corners=True,padding_mode='border')[0,0,0]
                target_values=(target_values-target_values.mean())/target_values.std().clamp(min=.02)
                photo_loss=functional.smooth_l1_loss(target_values,ref_tensor,beta=.5)
                if step%10==0:
                    rd=R.detach().cpu().numpy();td=t.detach().cpu().numpy();local=(train-td)@rd
                    cp=scene.compute_closest_points(o3d.core.Tensor(local.astype(np.float32)))['points'].numpy();correspondence=torch.tensor(cp,dtype=torch.float32,device='cuda')
                delta=(correspondence@R.T+t-qt)/.001
                geometry_loss=functional.smooth_l1_loss(delta,torch.zeros_like(delta),beta=.5)
                loss=photo_loss+.20*geometry_loss+.0005*torch.tanh(parameters).square().sum()
                if args.end_contour_weight:
                    loss=loss+args.end_contour_weight*end_loss(R,t)
                if float(loss.detach())<best_loss:best_loss=float(loss.detach());best=parameters.detach().clone()
                loss.backward();optimizer.step()
            with torch.no_grad():parameters.copy_(best)
            stages.append({'sigma':sigma,'objective':best_loss})
        R,t=make_pose();T=np.eye(4);T[:3,:3]=R.detach().cpu().numpy();T[:3,3]=t.detach().cpu().numpy()
        def evaluate(pose):
            p=reference_corners@pose[:3,:3].T+pose[:3,3];uv=p@K.T;uv=uv[:,:2]/uv[:,2,None]
            error=np.linalg.norm(uv-target_annotations[name],axis=1)
            check=obs['xyz_color'][~obs['fit']];local=(check-pose[:3,3])@pose[:3,:3];d=scene.compute_distance(o3d.core.Tensor(local.astype(np.float32))).numpy()*1000
            return {'heldout_label_corner_rmse_px':float(np.sqrt(np.mean(error**2))),'heldout_label_corner_errors_px':error.tolist(),'check_cloud_median_mm':float(np.median(d)),'check_cloud_p90_mm':float(np.quantile(d,.9)),'projected_label_corners':uv.tolist()}
        row={'id':name,'known_face_flip_applied':face_flipped,'initial_T_color_from_model':initial.tolist(),'T_color_from_model':T.tolist(),'initial':evaluate(initial),'refined':evaluate(T),'seconds':time.perf_counter()-started,'stages':stages,'delta_translation_mm':float(np.linalg.norm(T[:3,3]-initial[:3,3])*1000),'delta_rotation_deg':float(np.degrees(Rotation.from_matrix(initial[:3,:3].T@T[:3,:3]).magnitude()))}
        records.append(row);print(name,row['initial'],row['refined'],flush=True)
        (root/(name+'.json')).write_text(json.dumps(row,indent=2))
    report={'method':'Known face + fixed reference texture interior + metric stereo geometry','reference_frame':'optical_0360','reference_definition':'Manually selected label region lifted by reference stereo plane and prior pose','initializers':str(args.initializers) if args.initializers else 'Previous joint pose, face flip only','end_contour_weight':args.end_contour_weight,'end_contour_used_for_fitting':bool(args.end_contour_weight),'target_manual_points_used_for_optimization':False,'target_manual_points_used_for_evaluation':True,'model_scale_changed':False,'green_handle_excluded':True,'physical_pose_accuracy_validated':False,'records':records}
    (root/'report.json').write_text(json.dumps(report,indent=2))


if __name__=='__main__':main()
