"""Capture an explicit bounded catalog with real GC-r01 clamp and static views.

Physics-only scene preserves dynamic masses, joints and collision geometry.
Each camera/arm view is independently initialized from a qualified grasp and
settled under gravity; no continuous robot trajectory/insertion is claimed.
"""
import argparse,json,os,sys,time,copy,hashlib
from pathlib import Path
import xml.etree.ElementTree as ET
os.environ.setdefault('MUJOCO_GL','egl')
import numpy as np,mujoco,trimesh
from scipy.spatial.transform import Rotation
from PIL import Image
from generate_contact_wrist_dataset import ContactRenderer,GC
from generate_sim_wrist_dataset import read,sha,transform
from preview_three_variable_grasp import pose,measurements
from cached_contact_geometry import CachedGraspGate
sys.path.insert(0,str(GC/'scripts'))
from grasp_status import grasp_status
SOURCE=Path('/data/omi_runtime/runs/contact_wrist_surface_20261123_r01/data')
ANCHOR=np.array(read('/data/omi_runtime/runs/three_variable_grasp_preview_20261123_r01/manifest.json')['nominal_grasp_reference_in_tool_m'])
TIP=np.array([0,-.0350931697,0.]);MOUTH=np.array([-.0003,.00185,.0003])

def strip_physics(source,dst):
 root=ET.parse(source).getroot()
 for parent in list(root.iter()):
  for c in list(parent):
   if c.tag=='geom' and int(c.get('contype','1'))==0 and int(c.get('conaffinity','1'))==0:parent.remove(c)
   elif c.tag in ['camera','light']:parent.remove(c)
   elif c.tag=='body' and c.get('name','').startswith('robot_'):parent.remove(c)
 needed={g.get('mesh') for g in root.findall('.//geom') if g.get('mesh')}
 for e in list(root.find('asset')):
  if e.tag!='mesh' or e.get('name') not in needed:root.find('asset').remove(e)
 for g in root.findall('.//geom'):g.attrib.pop('material',None)
 ET.indent(root);ET.ElementTree(root).write(dst,encoding='unicode')

def set_free(d,name,T):d.joint(name).qpos[:]=np.r_[T[:3,3],np.roll(Rotation.from_matrix(T[:3,:3]).as_quat(),1)]

def relation(T):
 p=T[:3,:3]@TIP+T[:3,3];return {'lateral_mm':float((p[0]-MOUTH[0])*1000),'vertical_mm':float((p[2]-MOUTH[2])*1000),'tip_gap_mm':float((p[1]-MOUTH[1])*1000),'rotation_socket_xyz_deg':Rotation.from_matrix(T[:3,:3]).as_euler('xyz',degrees=True).tolist()}

def wanted_relation(s):
 T=np.eye(4);T[:3,:3]=Rotation.from_euler('xyz',s['rotation_socket_xyz_deg'],degrees=True).as_matrix();T[:3,3]=MOUTH+np.array([s['lateral_mm'],s['tip_gap_mm'],s['vertical_mm']])/1000-T[:3,:3]@TIP;return T

class Capture:
 def __init__(self,out,face=672):
  self.out=out;self.r=ContactRenderer(SOURCE/'scene.xml',read(SOURCE/'calibration.json'),face);strip_physics(SOURCE/'scene.xml',out/'physics_scene.xml');self.m=mujoco.MjModel.from_xml_path(str(out/'physics_scene.xml'));self.d=mujoco.MjData(self.m);self.tool=self.m.body('audit_tool').id;self.module=self.m.body('sim_module').id;self.mocap=int(self.m.body_mocapid[self.m.body('grasp_target').id]);self.joint_names=[self.m.joint(i).name for i in range(self.m.njnt)]
  assert self.joint_names==[self.r.m.joint(i).name for i in range(self.r.m.njnt)] and self.m.nq==self.r.m.nq
  for name in ['audit_tool','trial_jaw_left','trial_jaw_right','sim_module']:
   a=self.m.body(name).id;b=self.r.m.body(name).id
   for field in ['body_mass','body_inertia','body_ipos','body_iquat']:np.testing.assert_allclose(getattr(self.m,field)[a],getattr(self.r.m,field)[b],rtol=0,atol=1e-12)
  self.nominal,self.base_q,_,_=self.r.ik(self.r.nominal_tcp+self.r.Rs@np.array([0,.035,0]),self.r.nominal_R);mujoco.mj_forward(self.r.m,self.r.d);self.Tws=transform(self.r.d,self.r.socket)
  self.socket=trimesh.collision.CollisionManager();root=ET.parse(SOURCE/'scene.xml').getroot();meshes={x.get('name'):x.get('file') for x in root.findall('asset/mesh')}
  for g in root.findall(".//body[@name='sim_socket']/geom"):
   if int(g.get('group','0'))<3 and g.get('mesh'):self.socket.add_object(g.get('name'),trimesh.load(meshes[g.get('mesh')],force='mesh',process=False),transform=self.Tws)
  self.module_meshes=[trimesh.load(p['mesh'],force='mesh',process=False) for p in read('/data/omi_runtime/assets/optical_module_v4/r08/asset_manifest.json')['parts'] if p['component']!='pull_handle']
  self.moving=trimesh.collision.CollisionManager()
  for i,mesh in enumerate(self.module_meshes):self.moving.add_object('module_'+str(i),mesh)
  for i,mesh in enumerate(self.r.visual_gate.meshes):self.moving.add_object('tool_'+str(i),mesh)
  self.r.visual_gate=CachedGraspGate()
  self.module_vertices=np.concatenate([m.vertices for m in self.module_meshes]);self.r.m.opt.disableflags|=int(mujoco.mjtDisableBit.mjDSBL_CONTACT)
  self.pad_ids=[self.m.geom('pad_contact_'+s).id for s in ['left','right']]
 def reset(self,T,relative,jaws=None):
  mujoco.mj_resetData(self.m,self.d);set_free(self.d,'tool_free',T);set_free(self.d,'module_free',T@relative);self.d.mocap_pos[self.mocap]=T[:3,3];self.d.mocap_quat[self.mocap]=np.roll(Rotation.from_matrix(T[:3,:3]).as_quat(),1)
  for s in ['left','right']:self.d.joint('jaw_'+s).qpos[0]=.002 if jaws is None else jaws[s]
  self.d.ctrl[:]=.002 if jaws is None else -.0015;mujoco.mj_forward(self.m,self.d)
 def tick(self,n=25):
  mujoco.mj_step(self.m,self.d,nstep=n);mujoco.mj_forward(self.m,self.d);s=grasp_status(self.m,self.d);s['penetration_mm']=max([0.]+[-float(c.dist)*1000 for c in self.d.contact]);return s
 def target_gate(self,T,wanted):
  q=measurements(T,ANCHOR);ok=all(abs(q[k]-wanted[k])<=v for k,v in [('fore_aft_mm',.1),('height_mm',.1),('pitch_deg',.5)]) and abs(q['lateral_center_mm'])<=.1 and q['non_pitch_rotation_deg']<=.5
  return bool(ok),q
 def grasp(self,g):
  desired=pose(ANCHOR,**{'forward_mm':g['requested_module']['fore_aft_mm'],'height_mm':g['requested_module']['height_mm'],'pitch_deg':g['requested_module']['pitch_deg']});self.m.opt.gravity[:]=0;self.reset(self.nominal,desired);trace=[];baseline=None
  for k in range(240):
   if k==120:self.m.opt.gravity[:]=[0,0,-9.81]
   self.d.ctrl[:]=.002+(-.0015-.002)*min(self.d.time/.25,1);st=self.tick()
   if k>=160:
    T=np.array(st['T_TCP_from_module']);baseline=T.copy() if baseline is None else baseline
    trace.append([self.d.time,*st['pad_normal_force_n'].values(),np.linalg.norm(T[:3,3]-baseline[:3,3])*1000,np.degrees(Rotation.from_matrix(T[:3,:3]@baseline[:3,:3].T).magnitude()),st['penetration_mm']])
  T=np.array(st['T_TCP_from_module']);jaws={s:float(self.d.joint('jaw_'+s).qpos[0]) for s in ['left','right']};visible=self.r.visual_gate.check(T,jaws);matched,actual=self.target_gate(T,g['requested_module']);tr=np.array(trace)
  accepted=bool(np.min(tr[:,1:3])>=.1 and np.max(tr[:,3])<=.1 and np.max(tr[:,4])<=.5 and np.max(tr[:,5])<=.05 and visible['accepted'] and matched)
  result={**g,'accepted':accepted,'actual_module':actual,'T_tool_module':T.tolist(),'jaws_m':jaws,'visible_gate':visible,'min_force_N':float(np.min(tr[:,1:3])),'max_slip_mm':float(np.max(tr[:,3])),'max_rotation_drift_deg':float(np.max(tr[:,4])),'trace_samples':len(trace),'monitor_interval_ms':5}
  np.savez_compressed(self.out/'grasps'/f"{g['grasp_id']}.npz",qpos=self.d.qpos,qvel=self.d.qvel,mocap_pos=self.d.mocap_pos,mocap_quat=self.d.mocap_quat,ctrl=self.d.ctrl,trace=tr)
  return result
 def socket_collision(self,Twm,Twt,jaws):
  for i,mesh in enumerate(self.module_meshes):self.moving.set_transform('module_'+str(i),Twm)
  for i,part in enumerate(self.r.visual_gate.tool):
   local=np.eye(4);side=part['component'].removeprefix('jaw_')
   if side in jaws:local[1,3]=jaws[side]*(-1 if side=='left' else 1)
   self.moving.set_transform('tool_'+str(i),Twt@local)
  hits,pairs=self.moving.in_collision_other(self.socket,return_names=True)
  if hits:return 'module_socket_mesh_intersection' if any(pair[0].startswith('module_') for pair in pairs) else 'gripper_socket_mesh_intersection'
  return None
 def frame(self,c,g):
  Rwanted=wanted_relation(c['requested_socket_relation']);rel=np.array(g['T_tool_module']);Ttool=self.Tws@Rwanted@np.linalg.inv(rel)
  reason=self.socket_collision(Ttool@rel,Ttool,g['jaws_m'])
  if reason:return {'accepted':False,'reason':reason}
  if (self.module_vertices@Rwanted[1,:3]+Rwanted[1,3]).min()<MOUTH[1]:return {'accepted':False,'reason':'surface_crosses_mouth_plane_in_preinsert_dataset'}
  _,robot_q,ep,er=self.r.ik(Ttool[:3,3],Ttool[:3,:3])
  if ep>.1 or er>.05:return {'accepted':False,'reason':'IK_out_of_tolerance','ik_position_mm':ep,'ik_angle_deg':er}
  self.m.opt.gravity[:]=[0,0,-9.81];self.reset(Ttool,rel,g['jaws_m']);trace=[]
  for k in range(20):
   st=self.tick()
   if k>=10:trace.append([self.d.time,*st['pad_normal_force_n'].values(),st['penetration_mm']])
  Ttm=np.array(st['T_TCP_from_module']);matched,actual=self.target_gate(Ttm,c['requested_module']);jaws={s:float(self.d.joint('jaw_'+s).qpos[0]) for s in ['left','right']};visual=self.r.visual_gate.check(Ttm,jaws);trace=np.array(trace)
  if not matched or not visual['accepted'] or np.min(trace[:,1:3])<.1 or np.max(trace[:,3])>.05:return {'accepted':False,'reason':'transferred_contact_or_prior_failed','actual_module':actual}
  Twm=transform(self.d,self.module);Twt=transform(self.d,self.tool);Tsm=np.linalg.inv(self.Tws)@Twm;actual_socket=relation(Tsm)
  reason=self.socket_collision(Twm,Twt,jaws)
  if reason:return {'accepted':False,'reason':reason}
  clearance=float(((self.module_vertices@Tsm[1,:3]+Tsm[1,3]).min()-MOUTH[1])*1000)
  if clearance<0:return {'accepted':False,'reason':'actual_surface_crosses_mouth_plane'}
  rng=np.random.default_rng(np.random.SeedSequence([20261123,c['sample_id']]));self.r.reset(Ttool,Ttm,rng);self.r.robot_pose(robot_q);self.r.d.qpos[:]=self.d.qpos;self.r.d.qvel[:]=self.d.qvel;self.r.d.mocap_pos[:]=self.d.mocap_pos;self.r.d.mocap_quat[:]=self.d.mocap_quat;self.r.d.ctrl[:]=self.d.ctrl;mujoco.mj_forward(self.r.m,self.r.d)
  labels=self.r.labels();rgb,seg=self.r.render(segmentation=True);mask=np.zeros(seg.shape,np.uint8);mask[np.isin(seg,self.r.module_geoms)]=1;mask[np.isin(seg,self.r.socket_geoms)]=2;qa={}
  for name,i in [('module',1),('socket',2)]:
   yy,xx=np.where(mask==i);qa[name]={'visible_pixels':len(xx),'bbox_xyxy':[int(xx.min()),int(yy.min()),int(xx.max()),int(yy.max())] if len(xx) else None}
  if qa['module']['visible_pixels']<60 or qa['socket']['visible_pixels']<100:return {'accepted':False,'reason':'visibility_too_low','qa':qa}
  folder=self.out/'images'/c['grasp_id'];folder.mkdir(exist_ok=True);stem=f"{c['sample_id']:06d}";image=folder/(stem+'.jpg');Image.fromarray(rgb).save(image,quality=95,subsampling=0);maskpath=folder/(stem+'_mask.png');Image.fromarray(mask).save(maskpath)
  state=self.out/'states'/(stem+'.npz');np.savez_compressed(state,qpos=self.d.qpos,qvel=self.d.qvel,mocap_pos=self.d.mocap_pos,mocap_quat=self.d.mocap_quat,ctrl=self.d.ctrl,robot_qpos=robot_q,trace=trace)
  return {'accepted':True,'image':str(image.relative_to(self.out)),'image_sha256':sha(image),'instance_mask':str(maskpath.relative_to(self.out)),'mask_sha256':sha(maskpath),'state':str(state.relative_to(self.out)),**labels,'actual_module':actual,'actual_socket_relation':actual_socket,'qa':qa,'physical_contact':st,'visible_grasp_gate':visual,'socket_mesh_collision':False,'minimum_surface_mouth_plane_gap_mm':clearance,'ik_position_error_mm':ep,'ik_angle_error_deg':er,'handle_angle_deg':self.r.handle_angle_deg,'label_source':'actual settled physical module/tool state; fixed socket and FK arm visual context','training_label_valid':True,'real_world_ground_truth':False}

def main():
 p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--shards',type=int,default=1);p.add_argument('--shard-id',type=int,default=0);p.add_argument('--pilot',action='store_true');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
 for name in ['grasps','images','states']:(a.output/name).mkdir()
 gs=read(a.plan/'grasps.json');cs=list(map(json.loads,(a.plan/'candidates.jsonl').read_text().splitlines()));by={g['grasp_id']:[] for g in gs}
 for c in cs:by[c['grasp_id']].append(c)
 if a.pilot:
  corner=[g for g in gs if all(abs(g['requested_module'][k])==v for k,v in [('fore_aft_mm',3),('height_mm',1),('pitch_deg',4)])];zero=next(g for g in gs if all(v==0 for v in g['requested_module'].values()));gs=[zero,*corner]
  for g in gs:
   candidates=by[g['grasp_id']]
   if g==zero:
    select=[c for c in candidates if (c['requested_socket_relation']['lateral_mm'],c['requested_socket_relation']['vertical_mm']) in [(0,0),(-3,-3),(3,3)] and c['requested_socket_relation']['tip_gap_mm'] in [.5,2,10,40] and tuple(c['requested_socket_relation']['rotation_socket_xyz_deg']) in [(0,0,0),(-6,-6,-6),(6,6,6)]];by[g['grasp_id']]=select
   else:by[g['grasp_id']]=candidates
 capture=Capture(a.output);started=time.time();n=0;accepted=0;grasp_records=[];reasons={};metadata={'plan':str(a.plan),'plan_sha256':sha(a.plan/'plan.json'),'source_scene':str(SOURCE/'scene.xml'),'source_scene_sha256':sha(SOURCE/'scene.xml'),'physics_scene_sha256':sha(a.output/'physics_scene.xml'),'joint_and_inertia_equivalence_verified':True,'grasp_monitor_interval_ms':5,'grasp_close_total_seconds':1.2,'view_settle_seconds':.1,'view_monitor_last_seconds':.05,'view_monitor_interval_ms':5,'robot_motion':'independent static IK configurations, not continuous dynamics','socket_contacts_enabled':False,'socket_module_and_tool_mesh_intersection_checked':True,'pointcloud_templates':read(a.plan/'plan.json')['template_contract'],'mask_values':{'0':'background incl gripper','1':'visible rigid module','2':'visible socket assembly'},'render_only_model_contact_disabled':True,'physical_model_contacts_enabled':True,'shards':a.shards,'shard_id':a.shard_id,'pilot':a.pilot}
 (a.output/'config.json').write_text(json.dumps(metadata,indent=2));f=open(a.output/'records.jsonl','w');reject=open(a.output/'rejected.jsonl','w')
 for gi,g in enumerate(gs):
  if not all(v==0 for v in g['requested_module'].values()) and int(g['grasp_id'][1:])%a.shards!=a.shard_id:continue
  if all(v==0 for v in g['requested_module'].values()):by[g['grasp_id']]=[c for c in by[g['grasp_id']] if c['sample_id']%a.shards==a.shard_id]
  gr=capture.grasp(g);grasp_records.append(gr);(a.output/'grasp_records.json').write_text(json.dumps(grasp_records,indent=2))
  for c in by[g['grasp_id']]:
   result=capture.frame(c,gr) if gr['accepted'] else {'accepted':False,'reason':'grasp_configuration_failed'};row={**c,**result};n+=1
   if result['accepted']:f.write(json.dumps(row)+'\n');accepted+=1
   else:reject.write(json.dumps(row)+'\n');reasons[result['reason']]=reasons.get(result['reason'],0)+1
  f.flush();reject.flush();print(json.dumps({'grasp':g['grasp_id'],'grasp_ok':gr['accepted'],'groups':len(grasp_records),'attempted':n,'accepted':accepted,'reasons':reasons,'elapsed_s':round(time.time()-started,1)}),flush=True)
 f.close();reject.close();capture.r.close();report={'grasp_groups':len(grasp_records),'grasp_groups_passed':sum(g['accepted'] for g in grasp_records),'candidate_views':n,'accepted_images':accepted,'rejected_images':n-accepted,'rejection_reasons':reasons,'elapsed_s':time.time()-started,'complete':True};(a.output/'complete.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
if __name__=='__main__':main()
