"""Annotation-conditioned socket alignment; optical-module handle excluded. Units: metres."""
import os
os.environ['OMP_NUM_THREADS']='4';os.environ['OPENBLAS_NUM_THREADS']='4'
import argparse, hashlib, json,itertools,time
from pathlib import Path
import numpy as np,open3d as o3d
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation
from matplotlib.path import Path as Polygon
parser=argparse.ArgumentParser(description="Conditional fixed-scale OS-001 fit on the annotated 100k-point SGBM scene")
parser.add_argument('--cloud',type=Path,required=True)
parser.add_argument('--socket-inputs',type=Path,required=True)
parser.add_argument('--module-report',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
a=parser.parse_args()
module_report=json.loads(a.module_report.read_text())
assert module_report['input_sha256']=='efdf00062690651d2123d57f4eac48abc0bfca2c2a49ef5de29fc53d2201ee85'
module_cloud=np.load(a.module_report.parent/'cloud.npz')
p=np.load(a.cloud)
assert np.array_equal(p['xyz'],module_cloud['xyz']) and np.array_equal(p['gray'],module_cloud['gray'])
root=a.output;root.mkdir(parents=True,exist_ok=False)
Q=p['xyz'].astype(float)
# Manual ROI in the reproduced oblique view; coordinates are not camera pixels.
view_center=np.array([.015,-.025,.65]);yaw=-.3;pitch=-.5
ca,sa=np.cos(yaw),np.sin(yaw);cb,sb=np.cos(pitch),np.sin(pitch)
view_R=np.array([[ca,0,sa],[sb*sa,cb,-sb*ca],[-cb*sa,sb,cb*ca]])
view_points=((Q-view_center)*[1,-1,1])@view_R.T
uv=np.c_[500+750*view_points[:,0]/(view_points[:,2]+.45),500-750*view_points[:,1]/(view_points[:,2]+.45)]
np.savez_compressed(root/'projection.npz',xyz=Q,gray=p['gray'],uv=uv)
poly=[[320,232],[450,235],[469,335],[332,354]]
mask=Polygon(poly).contains_points(uv)&(Q[:,2]>.71)&(Q[:,2]<.815);ids=np.where(mask)[0];q=Q[ids]
np.savez_compressed(root/'socket_roi.npz',indices=ids,xyz=q,polygon=poly)
cloud=o3d.geometry.PointCloud(o3d.utility.Vector3dVector(q));o3d.utility.random.seed(7)
plane,inliers=cloud.segment_plane(.0015,3,500);plane=np.array(plane);plane=plane if plane[2]>0 else -plane;print('plane',plane,'inliers',len(inliers), 'q',len(q),flush=True)
np.savez_compressed(root/'plane.npz',plane=plane,indices=ids[inliers])
signed=q@np.array(plane[:3])+plane[3]
keep=(signed>-.024)&(signed<.004)
raw_ids=ids.copy();ids=ids[keep];q=Q[ids];hold=(np.arange(len(q))%5==0);np.savez_compressed(root/'socket_roi_refined.npz',indices=ids,xyz=q,fit=~hold,raw_indices=raw_ids,polygon=poly,plane=plane)
cloud=o3d.geometry.PointCloud(o3d.utility.Vector3dVector(q[~hold]));print('retained',len(q), 'hold',hold.sum(),flush=True)
base=a.socket_inputs;man=json.loads((base/'manifest.json').read_text());vs=[];fs=[];offset=0
assert hashlib.sha256(Path(man['socket']['source']).read_bytes()).hexdigest() == man['socket']['source_sha256']
for rec in man['socket']['parts']:
 if rec['group']=='stand':continue
 d=np.load(base/'socket'/rec['file']);v=d['vertices']/1000;f=d['faces'];vs.append(v);fs.append(f+offset);offset+=len(v)
V=np.concatenate(vs);F=np.concatenate(fs);np.savez_compressed(root/'socket_upper_mesh.npz',vertices=V,triangles=F)
mesh=o3d.geometry.TriangleMesh(o3d.utility.Vector3dVector(V),o3d.utility.Vector3iVector(F));mesh.compute_vertex_normals();scene=o3d.t.geometry.RaycastingScene(nthreads=4);scene.add_triangles(o3d.t.geometry.TriangleMesh.from_legacy(mesh))
o3d.utility.random.seed(11);sample=mesh.sample_points_uniformly(50000).voxel_down_sample(.0007);P=np.asarray(sample.points);sample.normals=o3d.utility.Vector3dVector(scene.compute_closest_points(o3d.core.Tensor(P.astype(np.float32)))['primitive_normals'].numpy().astype(float))
rawtree=cKDTree(Q[:,:2]/Q[:,2,None]);qtree=cKDTree(q[~hold])
def apply(p,T):return p@T[:3,:3].T+T[:3,3]
def dist(T):return scene.compute_distance(o3d.core.Tensor(apply(q,np.linalg.inv(T)).astype(np.float32))).numpy()*1000
def visibility(T):
 points=apply(P,T);norm=np.asarray(sample.normals)@T[:3,:3].T;idx=np.where(np.sum(norm*-points,axis=1)>0)[0][::3];pts=points[idx];inv=np.linalg.inv(T);dirs=pts/pts[:,2,None];rays=np.c_[np.broadcast_to(inv[:3,3],pts.shape),dirs@T[:3,:3]].astype(np.float32);hit=scene.cast_rays(o3d.core.Tensor(rays))['t_hit'].numpy();vis=np.isfinite(hit)&(abs(hit-pts[:,2])<.0005);pts=pts[vis];ang,nn=rawtree.query(pts[:,:2]/pts[:,2,None]);covered=ang<.0025;occluded=covered&(Q[nn,2]<pts[:,2]-.006);pts=pts[~occluded];d=qtree.query(pts)[0]*1000
 return float(np.mean(d<3)),float(np.median(d)),len(d)
R0=np.array(module_report['T_camera_from_model'])[:3,:3]
center=(np.quantile(q,.02,axis=0)+np.quantile(q,.98,axis=0))/2
# PCB/housing assembly center near model (-10,-35,0)mm; multistart accounts for occluded PCB.
mc=np.array([-.01,-.035,0]);choices=[];reg=o3d.pipelines.registration
for perm in itertools.permutations(range(3)):
 for signs in itertools.product([-1,1],repeat=3):
  S=np.eye(3)[:,perm]@np.diag(signs)
  if np.linalg.det(S)<0:continue
  R=R0@S
  for dx in [-.008,0,.008]:
   T=np.eye(4);T[:3,:3]=R;T[:3,3]=center-R@mc+R[:,0]*dx
   cur=np.linalg.inv(T)
   for thresh,iters in [(.018,50),(.009,55),(.004,60)]:
    result=reg.registration_icp(cloud,sample,thresh,cur,reg.TransformationEstimationPointToPlane(reg.TukeyLoss(k=.004)),reg.ICPConvergenceCriteria(max_iteration=iters));cur=result.transformation
   T=np.linalg.inv(cur);d=dist(T)[~hold];vis=visibility(T);score=float(np.quantile(d,.75)+.4*np.quantile(d,.9)+3*(1-vis[0]));choices.append({'T':T.tolist(),'score':score,'median':float(np.median(d)),'p90':float(np.quantile(d,.9)),'coverage3mm':float(np.mean(d<3)),'visibility':vis,'perm':perm,'signs':signs,'dx':dx})
  print('done',len(choices),'best',min(c['score'] for c in choices),flush=True)
choices.sort(key=lambda c:c['score']);unique=[]
for c in choices:
 T=np.array(c['T'])
 if all(np.degrees(Rotation.from_matrix(T[:3,:3].T@np.array(b['T'])[:3,:3]).magnitude())>5 or np.linalg.norm(T[:3,3]-np.array(b['T'])[:3,3])>.003 for b in unique):unique.append(c)
(root/'socket_candidates_refined.json').write_text(json.dumps({'choices':choices,'distinct':unique},indent=2));print('TOP',json.dumps(unique[:5],indent=2),flush=True)

# Check points are not used in ICP or candidate scoring; ROI/plane/initialization
# still use the entire observation, so this is not independent pose accuracy.
T=np.array(unique[0]['T'])
def stats(points):
 d=scene.compute_distance(o3d.core.Tensor(apply(points,np.linalg.inv(T)).astype(np.float32))).numpy()*1000
 return {'count':len(d),'median_mm':float(np.median(d)),'p90_mm':float(np.quantile(d,.9)),'within_3mm_fraction':float(np.mean(d<3))}
Tm=np.array(module_report['T_camera_from_model']);relative=np.linalg.inv(T)@Tm
module_tip=relative@np.array([0,-.035093169659,.0007,1])
report={'status':'conditional_coarse_socket_fit','socket_asset':'OS-001 r04 width-review candidate',
 'socket_source':man['socket']['source'],'socket_source_sha256':man['socket']['source_sha256'],
 'cloud_source_sha256':module_report['input_sha256'],'module_report':str(a.module_report),
 'module_pose_changed':False,'module_green_pull_arms_used_for_fitting':False,
 'socket_T_cloud_from_model':T.tolist(),'module_T_cloud_from_model':Tm.tolist(),
 'T_socket_from_module':relative.tolist(),'module_tip_in_socket_frame_m':module_tip[:3].tolist(),
 'module_tip_reference_note':'Nominal body-axis probe at module [0,-35.093169659,0.7] mm; not a measured contact point',
 'socket_channel_axis_x_m':-.0005,'module_tip_lateral_offset_from_channel_mm':float((module_tip[0]+.0005)*1000),
 'model_scale_changed':False,'model_deformed':False,'absolute_pose_accuracy_validated':False,
 'orientation_unique':False,'socket_stand_used_for_fit':False,
 'roi_polygon_in_reproduced_view':poly,'depth_gate_m':[.71,.815],
 'plane_band_m':[-.024,.004],'initializations':len(choices),
 'fit':stats(q[~hold]),'check':stats(q[hold]),'all_raw_roi':stats(Q[raw_ids]),
 'check_note':'Check subset excluded from refinement/scoring, but ROI, plane and initialization use overall observation',
 'selection':'Lowest geometric score; repeated openings leave near alternatives; no forced module/socket mating constraint',
 'rotation_determinant':float(np.linalg.det(T[:3,:3])),
 'rotation_orthogonality_error':float(np.linalg.norm(T[:3,:3].T@T[:3,:3]-np.eye(3)))}
(root/'report.json').write_text(json.dumps(report,indent=2))
mesh.transform(T);o3d.io.write_triangle_mesh(str(root/'matched_socket_upper.ply'),mesh)
print(json.dumps(report,indent=2),flush=True)
