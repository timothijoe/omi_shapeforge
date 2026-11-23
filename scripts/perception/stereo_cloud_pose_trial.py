"""New fixed-scale V3 point-cloud fits from recorded, freshly inferred stereo.

Only the object masks and a head-up visual prior are reused; no saved object
poses or 2-D corner correspondences initialize these fits.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
os.environ.setdefault('OMP_NUM_THREADS','4')
os.environ.setdefault('OPENBLAS_NUM_THREADS','4')
import cv2
import numpy as np
import open3d as o3d
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation


def transform(q,T):return q@T[:3,:3].T+T[:3,3]


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=Path,required=True);a=p.parse_args();root=a.run
    inv=json.loads((root/'inventory.json').read_text());session=Path(inv['source_session'])
    meta=json.loads((session/'frames/manifest.json').read_text());cal=meta['calibrations']['optical']
    K=np.array(cal['calibration']['left']['K']).reshape(3,3);Kc=np.array(cal['calibration']['color']['K']).reshape(3,3)
    Tci=np.eye(4);Tci[:3,:3]=np.array(cal['extrinsics']['depth_to_color']['rotation']).reshape(3,3,order='F');Tci[:3,3]=cal['extrinsics']['depth_to_color']['translation']
    assert np.allclose(cal['calibration']['color']['D'],0)
    body=np.load('/data/omi_runtime/runs/pointcloud_v3_overlay_20261121_face_corrected/body_mesh.npz');V,F=body['vertices'],body['triangles']
    mesh=o3d.geometry.TriangleMesh(o3d.utility.Vector3dVector(V),o3d.utility.Vector3iVector(F));mesh.compute_vertex_normals()
    scene=o3d.t.geometry.RaycastingScene(nthreads=4);scene.add_triangles(o3d.t.geometry.TriangleMesh.from_legacy(mesh))
    o3d.utility.random.seed(17);sample=mesh.sample_points_uniformly(24000).voxel_down_sample(.00065);P=np.asarray(sample.points)
    normals=scene.compute_closest_points(o3d.core.Tensor(P.astype(np.float32)))['primitive_normals'].numpy().astype(float);sample.normals=o3d.utility.Vector3dVector(normals)
    np.savez_compressed(root/'model.npz',vertices=V,triangles=F)
    (root/'calibration.json').write_text(json.dumps({'K_ir':K.tolist(),'K_color':Kc.tolist(),'T_color_from_ir':Tci.tolist(),'baseline_m':abs(cal['extrinsics']['depth_to_infra2']['translation'][0]),'distortion_color':cal['calibration']['color']['D']},indent=2))
    output=root/'fits';output.mkdir(exist_ok=False);results=[]
    for name in inv['selected_inspection_ids']:
        out=output/name;out.mkdir()
        cache=session/'stereo'/name;info=json.loads((cache/'inference.json').read_text())
        cache_verified={}
        for filename,expected in info['files'].items():
            with (cache/filename).open('rb') as f:actual=hashlib.file_digest(f,'sha256').hexdigest()
            if actual!=expected:raise ValueError((name,filename,'cache hash mismatch'))
            cache_verified[filename]=True
        z=np.load(root/'fresh_stereo'/name/'depth_filtered.npy')
        vv,uu=np.where(z>0);Q=np.c_[(uu-K[0,2])/K[0,0],(vv-K[1,2])/K[1,1],np.ones(len(uu))]*z[vv,uu,None]
        Qc=transform(Q,Tci);uv=Qc@Kc.T;uv=uv[:,:2]/uv[:,2,None]
        mask=cv2.imread(str(session/'masks'/f'{name}.png'),0)
        inner=cv2.erode(mask,np.ones((5,5),np.uint8));pix=np.rint(uv).astype(int)
        inside=(pix[:,0]>=0)&(pix[:,0]<mask.shape[1])&(pix[:,1]>=0)&(pix[:,1]<mask.shape[0]);selected=np.zeros(len(Q),bool)
        selected[inside]=inner[pix[inside,1],pix[inside,0]]>0
        zz=Q[selected,2];hist,bins=np.histogram(zz,bins=np.arange(.1,1.02,.01));mode=bins[np.argmax(hist)]+.005;selected&=(abs(Q[:,2]-mode)<.03)
        Q=Q[selected];uv=uv[selected];uu=uu[selected];vv=vv[selected]
        # Withhold spatial blocks, not adjacent random samples, from refinement.
        hold=((uu//4+2*(vv//4))%5)==0
        train=Q[~hold];check=Q[hold]
        rng=np.random.default_rng(19);train_fit=train[rng.choice(len(train),min(1800,len(train)),replace=False)]
        np.savez_compressed(out/'observations.npz',xyz_ir=Q,xyz_color=transform(Q,Tci),rgb_uv=uv,u=uu,v=vv,fit=~hold)
        cloud=o3d.geometry.PointCloud(o3d.utility.Vector3dVector(Q));o3d.io.write_point_cloud(str(out/'observed_cloud_ir.ply'),cloud)
        source=o3d.geometry.PointCloud(o3d.utility.Vector3dVector(train_fit))
        # Midbody plane and principal axis are derived from the current cloud.
        center=np.median(train_fit,axis=0);_,_,axes=np.linalg.svd(train_fit-center,full_matrices=False);ey=axes[0]
        if ey[1]>0:ey=-ey
        axial=(train_fit-center)@ey;lo,hi=np.quantile(axial,[.005,.995]);fraction=(axial-lo)/(hi-lo)
        middle=train_fit[(fraction>.25)&(fraction<.65)]
        plane_cloud=o3d.geometry.PointCloud(o3d.utility.Vector3dVector(middle));o3d.utility.random.seed(17)
        plane,inliers=plane_cloud.segment_plane(.0012,3,400);normal=np.array(plane[:3]);plane_d=-plane[3]
        if normal@middle.mean(0)>0:normal=-normal;plane_d=-plane_d
        ey=ey-normal*(normal@ey);ey/=np.linalg.norm(ey);ex=np.cross(ey,normal);ex/=np.linalg.norm(ex)
        c=normal*plane_d+ey*np.mean(np.quantile(train_fit@ey,[.005,.995]))+ex*np.mean(np.quantile(train_fit@ex,[.005,.995]))
        Rbase=np.column_stack([ex,ey,normal]);qtree=cKDTree(train_fit)
        def distances(points,T):
            qlocal=transform(points,np.linalg.inv(T)).astype(np.float32)
            return scene.compute_distance(o3d.core.Tensor(qlocal)).numpy()*1000
        def support(T):
            points=transform(P,T);ns=normals@T[:3,:3].T;idx=np.where(np.sum(ns*-points,axis=1)>0)[0][::3];pts=points[idx]
            invT=np.linalg.inv(T);dirs=pts/pts[:,2,None]
            rays=np.c_[np.broadcast_to(invT[:3,3],pts.shape),dirs@T[:3,:3]].astype(np.float32)
            hits=scene.cast_rays(o3d.core.Tensor(rays))['t_hit'].numpy();pts=pts[np.isfinite(hits)&(abs(hits-pts[:,2])<.0005)]
            # Reject model surface samples occluded by measured foreground.
            uvp=pts@K.T;uvp=np.rint(uvp[:,:2]/uvp[:,2,None]).astype(int);valid=(uvp[:,0]>=0)&(uvp[:,0]<z.shape[1])&(uvp[:,1]>=0)&(uvp[:,1]<z.shape[0]);observed=np.zeros(len(pts));observed[valid]=z[uvp[valid,1],uvp[valid,0]]
            pts=pts[(observed==0)|(observed>pts[:,2]-.004)]
            d=qtree.query(pts)[0]*1000 if len(pts) else np.array([99.])
            return float(np.mean(d<3)),float(np.median(d))
        choices=[];reg=o3d.pipelines.registration
        for face in range(4):
            R=Rbase@Rotation.from_euler('y',face*90,degrees=True).as_matrix()
            offset=.5*(abs(normal@R[:,0])*.017542425+abs(normal@R[:,2])*.007838253)
            for along in [-.003,0,.003]:
                for shift in [-.0006,.0006]:
                    T=np.eye(4);T[:3,:3]=R;T[:3,3]=c-normal*offset+ey*along+normal*shift;cur=np.linalg.inv(T)
                    for threshold,iterations in [(.008,35),(.004,45),(.0025,45)]:
                        res=reg.registration_icp(source,sample,threshold,cur,reg.TransformationEstimationPointToPlane(reg.TukeyLoss(k=.0025)),reg.ICPConvergenceCriteria(max_iteration=iterations));cur=res.transformation
                    T=np.linalg.inv(cur);d=distances(train_fit,T);sup=support(T);score=float(np.median(d)+.35*np.quantile(d,.9)+1.5*(1-sup[0]))
                    choices.append({'T_ir_from_model':T.tolist(),'T_color_from_model':(Tci@T).tolist(),'score':score,'fit_median_mm':float(np.median(d)),'fit_p90_mm':float(np.quantile(d,.9)),'visible_support_3mm':sup[0],'face_seed':face})
        choices.sort(key=lambda x:x['score']);unique=[]
        for ch in choices:
            Tc=np.array(ch['T_ir_from_model'])
            if all(np.degrees(Rotation.from_matrix(Tc[:3,:3].T@np.array(b['T_ir_from_model'])[:3,:3]).magnitude())>12 or np.linalg.norm(Tc[:3,3]-np.array(b['T_ir_from_model'])[:3,3])>.002 for b in unique):unique.append(ch)
        best=choices[0];T=np.array(best['T_ir_from_model']);hold_d=distances(check,T)
        oldz=np.load(cache/'depth_filtered.npy');valid_old=oldz[vv,uu]>0;delta=(z[vv,uu]-oldz[vv,uu])*1000
        report={'id':name,'point_count':len(Q),'fit_points':len(train),'check_points':len(check),'best':best,'distinct_candidates':unique[:6],'initializations':len(choices),'check_median_mm':float(np.median(hold_d)),'check_p90_mm':float(np.quantile(hold_d,.9)),'historical_cache_hashes_verified':cache_verified,'fresh_minus_cached_depth_median_mm':float(np.median(delta[valid_old])),'fresh_minus_cached_depth_abs_p90_mm':float(np.quantile(abs(delta[valid_old]),.9)),'mask_source':'Existing SAM2.1 metal-body mask, excludes green handle/hand','initial_pose_source':'New current-frame stereo point cloud PCA/plane and multi-start ICP','head_tail_prior':'Raised head/handle end toward upper image; observed in sample contact sheet','pixel_contour_used_in_pose_fit':False,'mask_used_to_select_cloud':True,'saved_object_pose_used':False,'model_scale_changed':False,'physical_accuracy_validated':False}
        (out/'coarse_pose.json').write_text(json.dumps(report,indent=2));results.append(report)
        posed=o3d.geometry.TriangleMesh(o3d.utility.Vector3dVector(transform(V,T)),o3d.utility.Vector3iVector(F));o3d.io.write_triangle_mesh(str(out/'coarse_mesh_ir.ply'),posed)
        (root/'coarse_summary.json').write_text(json.dumps(results,indent=2));print(name,'points',len(Q),'check median/P90',report['check_median_mm'],report['check_p90_mm'],flush=True)


if __name__=='__main__':main()
