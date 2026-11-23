"""Refine stereo cloud poses with RGB silhouettes while retaining 3-D evidence.

Fits use training depth blocks only. Check blocks and native-depth comparisons
are diagnostic and are not used to choose a pose.
"""
import argparse
import json
from pathlib import Path
import time
import cv2
import numpy as np
import open3d as o3d
import torch
import nvdiffrast.torch as dr
from scipy.spatial.transform import Rotation


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=Path,required=True);a=p.parse_args();root=a.run
    inventory=json.loads((root/'inventory.json').read_text());session=Path(inventory['source_session'])
    calibration=json.loads((root/'calibration.json').read_text());Kc=np.array(calibration['K_color']);Tci=np.array(calibration['T_color_from_ir'])
    model=np.load(root/'model.npz');V,F=model['vertices'],model['triangles']
    mesh=o3d.geometry.TriangleMesh(o3d.utility.Vector3dVector(V),o3d.utility.Vector3iVector(F));scene=o3d.t.geometry.RaycastingScene(nthreads=4);scene.add_triangles(o3d.t.geometry.TriangleMesh.from_legacy(mesh))
    verts=torch.tensor(V,dtype=torch.float32,device='cuda');faces=torch.tensor(F,dtype=torch.int32,device='cuda');ctx=dr.RasterizeCudaContext();side=512
    reports=[]
    for name in inventory['selected_inspection_ids']:
        out=root/'fits'/name;coarse=json.loads((out/'coarse_pose.json').read_text());obs=np.load(out/'observations.npz');mask=cv2.imread(str(session/'masks'/f'{name}.png'),0)
        yy,xx=np.where(mask>0);span=int(max(xx.max()-xx.min(),yy.max()-yy.min())*1.22)+2
        x0=int((xx.max()+xx.min()-span)/2);y0=int((yy.max()+yy.min()-span)/2);scale=side/span
        K=Kc.copy();K[0,2]-=x0;K[1,2]-=y0;K[:2]*=scale
        affine=np.array([[scale,0,-x0*scale],[0,scale,-y0*scale]],np.float32)
        rgb=cv2.imread(str(session/'frames'/name/'color.png'));crop=cv2.warpAffine(rgb,affine,(side,side));mask_crop=cv2.warpAffine(mask,affine,(side,side),flags=cv2.INTER_NEAREST)
        cv2.imwrite(str(out/'color_crop.png'),crop);cv2.imwrite(str(out/'mask_crop.png'),mask_crop)
        (out/'crop.json').write_text(json.dumps({'x0':x0,'y0':y0,'span':span,'scale':scale,'K':K.tolist()},indent=2))
        target=torch.tensor(mask_crop>0,device='cuda');fx,fy,cx,cy=K[0,0],K[1,1],K[0,2],K[1,2]
        q=obs['xyz_color'][obs['fit']];rng=np.random.default_rng(23);q=q[rng.choice(len(q),min(900,len(q)),replace=False)];q_tensor=torch.tensor(q,dtype=torch.float32,device='cuda')
        def silhouette(R,t):
            v=verts@R.T+t;x,y,z=v.unbind(1)
            clip=torch.stack([2*fx/side*x+(2*cx/side-1)*z,-2*fy/side*y+(1-2*cy/side)*z,1.00002*z-.00200002,z],dim=1)[None]
            rast,_=dr.rasterize(ctx,clip,faces,resolution=[side,side]);hard=(rast[...,3:]>0).float();soft=dr.antialias(hard,rast,clip,faces)[0,...,0].flip(0)
            return soft
        def iou(pred):
            pred=pred>.5;return float((pred&target).sum()/(pred|target).sum().clamp(min=1))
        def distances(points,T):
            local=(points-T[:3,3])@T[:3,:3]
            return scene.compute_distance(o3d.core.Tensor(local.astype(np.float32))).numpy()*1000
        def metrics(T):
            points=obs['xyz_color'];fit=distances(points[obs['fit']],T);check=distances(points[~obs['fit']],T)
            R=torch.tensor(T[:3,:3],dtype=torch.float32,device='cuda');t=torch.tensor(T[:3,3],dtype=torch.float32,device='cuda')
            return {'rgb_mask_iou':iou(silhouette(R,t)),'fit_median_mm':float(np.median(fit)),'fit_p90_mm':float(np.quantile(fit,.9)),'check_median_mm':float(np.median(check)),'check_p90_mm':float(np.quantile(check,.9))}
        def optimize(initial,depth_weight):
            R0=torch.tensor(initial[:3,:3],dtype=torch.float32,device='cuda');t0=torch.tensor(initial[:3,3],dtype=torch.float32,device='cuda')
            parameters=torch.zeros(6,device='cuda',requires_grad=True);opt=torch.optim.Adam([parameters],lr=.025)
            best=None;best_value=float('inf');start=time.perf_counter()
            for step in range(240):
                opt.zero_grad();bounded=torch.tanh(parameters);w=bounded[:3]*.15;z=w[0]*0
                skew=torch.stack([z,-w[2],w[1],w[2],z,-w[0],-w[1],w[0],z]).reshape(3,3)
                R=torch.matrix_exp(skew)@R0;t=t0+bounded[3:]*torch.tensor([.003,.003,.005],device='cuda')
                pred=silhouette(R,t);pixel_loss=((pred-target.float())**2).sum()/target.sum().clamp(min=1)
                if step%10==0:
                    Rd=R.detach().cpu().numpy();td=t.detach().cpu().numpy();local=(q-td)@Rd
                    closest=scene.compute_closest_points(o3d.core.Tensor(local.astype(np.float32)))['points'].numpy()
                    corresponding=torch.tensor(closest,dtype=torch.float32,device='cuda')
                delta=(corresponding@R.T+t-q_tensor)/.001
                # Euclidean closest-surface residual, in units of 1 mm; robust to outliers.
                depth_loss=torch.nn.functional.smooth_l1_loss(delta,torch.zeros_like(delta),beta=.5,reduction='mean')
                loss=pixel_loss+depth_weight*depth_loss+.001*bounded.square().sum()
                value=float(loss.detach())
                if value<best_value:best_value=value;best=(R.detach().cpu().numpy().copy(),t.detach().cpu().numpy().copy())
                loss.backward();opt.step()
            result=np.eye(4);result[:3,:3],result[:3,3]=best
            return {'T_color_from_model':result.tolist(),'objective':best_value,'seconds':time.perf_counter()-start,'depth_weight':depth_weight,**metrics(result)}
        T0=np.array(coarse['best']['T_color_from_model']);baseline=metrics(T0)
        pixel_only=optimize(T0,0.)
        # Preserve geometrically plausible discrete alternatives from cloud fit.
        candidates=[c for c in coarse['distinct_candidates'][:4] if c['score']<=coarse['best']['score']+.8]
        joint=[]
        for index,candidate in enumerate(candidates):
            result=optimize(np.array(candidate['T_color_from_model']),.30);result['coarse_candidate_index']=index;joint.append(result)
        selected=min(joint,key=lambda x:x['objective']);T=np.array(selected['T_color_from_model']);Tir=np.linalg.inv(Tci)@T
        R0=T0[:3,:3];angle=float(np.degrees(Rotation.from_matrix(R0.T@T[:3,:3]).magnitude()))
        check_ok=(selected['check_median_mm']<=baseline['check_median_mm']+.2 and selected['check_p90_mm']<=baseline['check_p90_mm']+.5)
        image_ok=selected['rgb_mask_iou']>baseline['rgb_mask_iou']+.005
        # These are provisional diagnostic gates, not metrology tolerances.
        status='joint_improves_image_without_large_check_depth_regression' if check_ok and image_ok else 'review_required'
        report={'id':name,'status':status,'coarse':{'T_color_from_model':T0.tolist(),**baseline},'pixel_only':pixel_only,'joint':selected,'joint_candidates':joint,'T_ir_from_model':Tir.tolist(),'translation_change_mm':float(np.linalg.norm(T[:3,3]-T0[:3,3])*1000),'rotation_change_deg':angle,'check_depth_guard_passed':check_ok,'image_improved':image_ok,'model_rescaled':False,'physical_pose_accuracy_validated':False,'test_points_used_for_optimization_or_ranking':False,'diagnostic_thresholds':{'max_check_median_increase_mm':.2,'max_check_p90_increase_mm':.5,'min_iou_improvement':.005}}
        ranked=sorted(joint,key=lambda x:x['objective'])
        margin=ranked[1]['objective']-ranked[0]['objective'] if len(ranked)>1 else None
        report.update(joint_objective_margin=margin,near_alternative_requires_review=margin is not None and margin<.03,orientation_branch_changed_from_coarse=angle>45)
        (out/'pixel_refinement.json').write_text(json.dumps(report,indent=2));reports.append(report)
        fine=o3d.geometry.TriangleMesh(o3d.utility.Vector3dVector(V@Tir[:3,:3].T+Tir[:3,3]),o3d.utility.Vector3iVector(F));o3d.io.write_triangle_mesh(str(out/'refined_mesh_ir.ply'),fine)
        (root/'refinement_summary.json').write_text(json.dumps(reports,indent=2));print(name,'IoU',baseline['rgb_mask_iou'],'->',selected['rgb_mask_iou'],'check P90',baseline['check_p90_mm'],'->',selected['check_p90_mm'],status,flush=True)


if __name__=='__main__':main()
