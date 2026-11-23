"""Merge a complete finite catalog and independently verify every saved label."""
import argparse,json,shutil,sys
from pathlib import Path
import numpy as np,mujoco
from PIL import Image
from scipy.spatial.transform import Rotation
from generate_sim_wrist_dataset import read,sha,transform,camera_transform
from generate_grid_perception import SOURCE,MOUTH,TIP,relation
from preview_three_variable_grasp import measurements
sys.path.insert(0,'/data/omi_runtime/assets/daimon/wrist_grasp_contact_r01/scripts')
from grasp_status import grasp_status

def merge(root):
 shards=sorted((root/'shards').glob('shard_*'));assert len(shards)==8
 for s in shards:
  if not (s/'complete.json').exists():raise ValueError('Incomplete shard '+str(s))
 out=root/'data';out.mkdir(exist_ok=False);(out/'shards').symlink_to(root/'shards',target_is_directory=True);records=[];rejects=[];grasps={};grasp_sources={}
 for s in shards:
  for row in map(json.loads,(s/'records.jsonl').read_text().splitlines()):
   row['id']=row['sample_id'];row['episode']=row['grasp_id'];row['is_temporal_sequence']=False
   for key in ['image','instance_mask','state']:row[key]='shards/'+s.name+'/'+row[key]
   row['source_shard']=s.name;records.append(row)
  rejects.extend(map(json.loads,(s/'rejected.jsonl').read_text().splitlines()))
  for g in read(s/'grasp_records.json'):
   gid=g['grasp_id'];grasp_sources.setdefault(gid,[]).append(str(s/'grasps'/f'{gid}.npz'))
   if gid in grasps:
    if grasps[gid]['accepted']!=g['accepted'] or not np.allclose(grasps[gid]['T_tool_module'],g['T_tool_module'],atol=1e-10,rtol=0):raise ValueError('Repeated nominal grasp differs between shards')
   else:grasps[gid]=g
 cal=read(SOURCE/'calibration.json');K=np.array(cal['K']);D=np.array(cal['D'])
 def projected(q):
  radius=np.linalg.norm(q[:2]);theta=np.arctan2(radius,q[2]);theta_d=theta*(1+sum(D[i]*theta**(2*(i+1)) for i in range(4)));xy=q[:2]*theta_d/max(radius,1e-15);uv=(K@np.r_[xy,1])[:2];return uv.tolist()
 for row in records:
  row['keypoints']={}
  for name,kind,point in [('module_tip_reference','module',TIP),('module_grasp_reference','module',np.array([0,.025,0])),('socket_mouth_center','socket',MOUTH)]:
   T=np.array(row['T_camera_from_'+kind]);q=T[:3,:3]@point+T[:3,3];uv=projected(q);row['keypoints'][name]={'camera_xyz_m':q.tolist(),'image_xy_px':uv,'in_image':bool(q[2]>0 and 0<=uv[0]<cal['image_width'] and 0<=uv[1]<cal['image_height']),'visibility':'not asserted; fixed geometric reference may be occluded or inside geometry'}
 records.sort(key=lambda x:x['sample_id']);rejects.sort(key=lambda x:x['sample_id'])
 expected={x['sample_id'] for x in map(json.loads,(root/'candidates.jsonl').read_text().splitlines())};valid={x['sample_id'] for x in records};invalid={x['sample_id'] for x in rejects}
 if len(valid)!=len(records) or len(invalid)!=len(rejects) or valid&invalid or valid|invalid!=expected:raise ValueError('Candidate coverage is not a disjoint complete partition')
 if len(grasps)!=read(root/'plan.json')['module_grasp_groups']:raise ValueError('Missing grasp grid cells')
 for name,rows in [('records.jsonl',records),('rejected.jsonl',rejects)]: (out/name).write_text(''.join(json.dumps(x)+'\n' for x in rows))
 (out/'grasps.json').write_text(json.dumps(grasps,indent=2));(out/'grasp_sources.json').write_text(json.dumps(grasp_sources,indent=2))
 for name in ['scene.xml','calibration.json','dependencies.json']:shutil.copy2(SOURCE/name,out/name)
 hashes={sha(s/'physics_scene.xml') for s in shards}
 if len(hashes)!=1:raise ValueError('Different physical scenes')
 shutil.copy2(shards[0]/'physics_scene.xml',out/'physics_scene.xml')
 cfg=read(shards[0]/'config.json');cfg.update(plan=read(root/'plan.json'),shard_paths=[str(x) for x in shards],contact_asset='GC-r01',frames_are_independent_static_views=True,continuous_motion_validated=False,scope='static contact-qualified pre-insertion visual pretraining corpus');(out/'config.json').write_text(json.dumps(cfg,indent=2))
 reasons={}
 for x in rejects:reasons[x['reason']]=reasons.get(x['reason'],0)+1
 report={'candidate_images':len(expected),'accepted_images':len(records),'rejected_images':len(rejects),'rejection_reasons':reasons,'grasp_grid_cells_checked':len(grasps),'grasp_grid_cells_passed':sum(g['accepted'] for g in grasps.values()),'grasp_groups_with_images':len({x['grasp_id'] for x in records}),'split_images':{s:sum(r['split']==s for r in records) for s in ['train','val','test']},'coverage_partition_complete':True,'training_performed':False}
 (out/'complete.json').write_text(json.dumps(report,indent=2));return out

def audit(folder):
 cfg=read(folder/'config.json');rows=list(map(json.loads,(folder/'records.jsonl').read_text().splitlines()));grasps=read(folder/'grasps.json');cal=read(folder/'calibration.json')
 m=mujoco.MjModel.from_xml_path(str(folder/'scene.xml'));d=mujoco.MjData(m);m.opt.disableflags|=int(mujoco.mjtDisableBit.mjDSBL_CONTACT);pm=mujoco.MjModel.from_xml_path(str(folder/'physics_scene.xml'));pd=mujoco.MjData(pm);pm.opt.gravity[:]=[0,0,-9.81]
 assert not pm.opt.disableflags&int(mujoco.mjtDisableBit.mjDSBL_CONTACT)
 cam=m.camera('wrist_rgb').id;mb=m.body('sim_module').id;sb=m.body('sim_socket').id;tb=m.body('audit_tool').id
 for i in range(pm.neq):
  if pm.eq_type[i]==mujoco.mjtEq.mjEQ_WELD and pm.body('sim_module').id in [pm.eq_obj1id[i],pm.eq_obj2id[i]]:raise ValueError('Module weld found')
 anchor=np.array(read('/data/omi_runtime/runs/three_variable_grasp_preview_20261123_r01/manifest.json')['nominal_grasp_reference_in_tool_m']);seen={};maxerr=0.;minforce=float('inf');minimum_gap=float('inf');max_target_translation=0.;max_target_angle=0.;bad=[]
 for index,row in enumerate(rows):
  if grasps[row['grasp_id']]['split']!=row['split']:raise ValueError('Group split mismatch')
  h=sha(folder/row['image']);maskh=sha(folder/row['instance_mask'])
  if h!=row['image_sha256'] or maskh!=row['mask_sha256']:raise ValueError('Hash mismatch')
  if h in seen and seen[h]!=row['split']:raise ValueError('Identical image across splits')
  seen[h]=row['split']
  with Image.open(folder/row['image']) as image:assert image.size==(cal['image_width'],cal['image_height'])
  mask=np.array(Image.open(folder/row['instance_mask']));assert mask.shape==(cal['image_height'],cal['image_width']) and np.isin(mask,[0,1,2]).all()
  for name,value in [('module',1),('socket',2)]:
   ys,xs=np.where(mask==value);bbox=[int(xs.min()),int(ys.min()),int(xs.max()),int(ys.max())];assert len(xs)==row['qa'][name]['visible_pixels'] and bbox==row['qa'][name]['bbox_xyxy']
  state=np.load(folder/row['state']);trace=state['trace'];assert trace.shape==(10,4) and trace[:,1:3].min()>=.1 and trace[:,3].max()<=.05
  for data in [d,pd]:
   for key in ['qpos','qvel','mocap_pos','mocap_quat','ctrl']:getattr(data,key)[:]=state[key]
  mujoco.mj_forward(pm,pd);contact=grasp_status(pm,pd)
  if not contact['held']:raise ValueError('Replayed view has lost bilateral contact')
  minforce=min(minforce,min(contact['pad_normal_force_n'].values()));mujoco.mj_forward(m,d);Twc=camera_transform(d,cam);Twt=transform(d,tb);Twm=transform(d,mb);Tws=transform(d,sb)
  for name,b in [('module',mb),('socket',sb)]:maxerr=max(maxerr,float(np.max(abs(np.linalg.inv(Twc)@transform(d,b)-row['T_camera_from_'+name]))))
  maxerr=max(maxerr,float(np.max(abs(Twc-row['T_world_from_camera']))),float(np.max(abs(np.linalg.inv(Twt)@Twm-row['T_tcp_from_module']))))
  meas=measurements(np.linalg.inv(Twt)@Twm,anchor)
  for key,tol in [('fore_aft_mm',.1),('height_mm',.1),('pitch_deg',.5)]:
   if abs(meas[key]-row['requested_module'][key])>tol:raise ValueError('Actual module left requested grid cell tolerance')
  if abs(meas['lateral_center_mm'])>.1 or meas['non_pitch_rotation_deg']>.5:raise ValueError('Three-variable prior failed')
  actual=relation(np.linalg.inv(Tws)@Twm);req=row['requested_socket_relation'];err=max(abs(actual[k]-req[k]) for k in ['lateral_mm','vertical_mm','tip_gap_mm']);max_target_translation=max(max_target_translation,err);ang=float(np.degrees(Rotation.from_matrix(Rotation.from_euler('xyz',req['rotation_socket_xyz_deg'],degrees=True).as_matrix().T@(np.linalg.inv(Tws)@Twm)[:3,:3]).magnitude()));max_target_angle=max(max_target_angle,ang)
  if err>.1 or ang>.5:raise ValueError('Requested socket relation not achieved')
  if row['socket_mesh_collision'] or not row['visible_grasp_gate']['accepted'] or row['minimum_surface_mouth_plane_gap_mm']<0:raise ValueError('Invalid mesh geometry')
  minimum_gap=min(minimum_gap,row['minimum_surface_mouth_plane_gap_mm'])
  if index%1000==0:print(json.dumps({'audited':index+1,'total':len(rows)}),flush=True)
 if maxerr>1e-9:raise ValueError('Pose label differs from independently replayed state')
 for path,h in read(folder/'dependencies.json').items():
  if sha(path)!=h:raise ValueError('Source dependency changed')
 report={'accepted_for_sim_supervision':True,'images_checked':len(rows),'mask_hashes_values_pixel_counts_and_bboxes_checked':True,'all_actual_poses_independently_replayed':True,'max_pose_matrix_difference':maxerr,'all_frame_bilateral_contacts_recomputed':True,'replayed_min_each_force_N':minforce,'requested_socket_translation_max_difference_mm':max_target_translation,'requested_socket_rotation_max_difference_deg':max_target_angle,'minimum_module_surface_mouth_plane_gap_mm':minimum_gap,'shared_source_assets_unchanged':True,'module_no_weld':True,'module_prior_checked_each_frame':True,'grouped_split_no_identical_image_leakage':True,'coverage_partition':read(folder/'complete.json'),'real_world_accuracy_validated':False,'socket_insertion_contact_validated':False,'continuous_motion_validated':False,'template_manifest':cfg['pointcloud_templates'],'template_manifest_sha256':sha(cfg['pointcloud_templates'])}
 (folder/'label_audit.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--run',type=Path);p.add_argument('--data',type=Path);a=p.parse_args();audit(merge(a.run) if a.run else a.data)
