"""Three-variable grasp preview: fore/aft, height, pitch; width centered.

Exact target geometry and unconstrained contact settling are saved separately.
Neither target poses nor physical out-of-prior states are training labels.
"""
import argparse,json,itertools,os,sys,shutil,time
from pathlib import Path
os.environ.setdefault('MUJOCO_GL','egl')
import numpy as np,mujoco
from scipy.spatial.transform import Rotation
from PIL import Image,ImageDraw,ImageFont
from generate_contact_wrist_dataset import ContactRenderer
from generate_sim_wrist_dataset import read,sha,transform

R0=np.array([[0.,0.,1.],[-1.,0.,0.],[0.,-1.,0.]])
PIVOT=np.array([0.,.025,0.])
FONT='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'

def pose(anchor0,forward_mm,height_mm,pitch_deg):
 R=Rotation.from_euler('y',pitch_deg,degrees=True).as_matrix()@R0
 T=np.eye(4);T[:3,:3]=R;T[:3,3]=anchor0+np.array([height_mm,0,forward_mm])/1000-R@PIVOT
 return T

def measurements(T,anchor0):
 D=T[:3,:3]@R0.T;pitch=float(np.degrees(np.arctan2(D[0,2],D[2,2])));anchor=T[:3,:3]@PIVOT+T[:3,3];pitch_R=Rotation.from_euler('y',pitch,degrees=True).as_matrix()@R0
 return {'fore_aft_mm':float((anchor[2]-anchor0[2])*1000),'height_mm':float((anchor[0]-anchor0[0])*1000),'pitch_deg':pitch,'lateral_center_mm':float(T[1,3]*1000),'non_pitch_rotation_deg':float(np.degrees(Rotation.from_matrix(T[:3,:3]@pitch_R.T).magnitude()))}

def tangent_jaws(gate,T):
 for key in gate.modules:gate.manager.set_transform(key,T)
 result={}
 for side in ['left','right']:
  i=next(i for i,p in enumerate(gate.tool) if p['name']=='24 convex black contact pad '+side);mesh=gate.meshes[i]
  def collision(q):
   M=np.eye(4);M[1,3]=q*(-1 if side=='left' else 1);return gate.manager.in_collision_single(mesh,transform=M)
  lo,hi=-.003,.008
  if not collision(lo) or collision(hi):return None
  for _ in range(24):
   mid=(lo+hi)/2
   if collision(mid):lo=mid
   else:hi=mid
  result[side]=hi-1e-6
 return result

def save_image(root,rel,rgb):Image.fromarray(rgb).save(root/rel,quality=96,subsampling=0)

def make_sheets(root,records):
 lookup={tuple(x['requested'][k] for k in ['fore_aft_mm','height_mm','pitch_deg']):x for x in records}
 cases=[[lookup[(v,0,0)] for v in [-3,0,3]],[lookup[(0,v,0)] for v in [-1,0,1]],[lookup[(0,0,v)] for v in [-4,0,4]]]
 font=ImageFont.truetype(FONT,23);small=ImageFont.truetype(FONT,17);big=ImageFont.truetype(FONT,30)
 for mode in ['target','settled']:
  sheet=Image.new('RGB',(1500,1360),'#111e28');d=ImageDraw.Draw(sheet)
  d.text((20,10),'三个变量单独变化：前后 / 上下 / 俯仰',font=big,fill='white')
  d.text((20,57),'目标几何预览：左右居中，偏转与侧倾固定；尚未认定为训练样本' if mode=='target' else '自由接触后的实际结果：红字表示偏离目标或不满足夹持检查',font=small,fill='#b9ceda')
  for row,triplet in enumerate(cases):
   for col,item in enumerate(triplet):
    left=col*500;top=95+row*420;im=Image.open(root/item[mode+'_image']);im=im.crop((400,280,580,430)).resize((420,350));sheet.paste(im,(left+40,top+45));q=item['requested'];lab=[f"前后 {q['fore_aft_mm']:+.0f} mm",f"上下 {q['height_mm']:+.0f} mm",f"俯仰 {q['pitch_deg']:+.0f}°"][row];d.text((left+45,top+6),lab,font=font,fill='white')
    if mode=='settled':
     a=item['actual'];label=f"实际：{a['fore_aft_mm']:+.2f}mm / {a['height_mm']:+.2f}mm / {a['pitch_deg']:+.2f}°";d.text((left+20,top+395),label,font=small,fill='#71df9d' if item['qualified_preview'] else '#ff9484')
  sheet.save(root/f'{mode}_single_variable_grid.png')


def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--limit',type=int);a=p.parse_args();out=a.output;out.mkdir(parents=True,exist_ok=False);(out/'frames').mkdir()
 source=Path('/data/omi_runtime/runs/contact_wrist_surface_20261123_r01/data');shutil.copy2(source/'scene.xml',out/'scene.xml');cal=read(source/'calibration.json');(out/'calibration.json').write_text(json.dumps(cal,indent=2));r=ContactRenderer(out/'scene.xml',cal,672)
 mujoco.mj_forward(r.m,r.d);initial=np.linalg.inv(transform(r.d,r.tcp))@transform(r.d,r.module);t0=initial[:3,3].copy();t0[1]=0.;anchor0=t0+R0@PIVOT
 Ttool,q,ep,er=r.ik(r.nominal_tcp+r.Rs@np.array([0,.035,0]),r.nominal_R);r.robot_pose(q)
 manifest={'schema':'three-variable-grasp-preview-v1','source_scene':str(source/'scene.xml'),'source_scene_sha256':sha(source/'scene.xml'),'tool_axes':{'X':'height toward camera/marked face','Y':'finger opening axis; lateral center fixed at zero','Z':'fore/aft positive toward fingertips'},'levels':{'fore_aft_mm':[-3,0,3],'height_mm':[-1,0,1],'pitch_deg':[-4,0,4]},'rotation_formula':'R_tool_module = Ry(pitch) @ R0','R0':R0.tolist(),'module_grasp_reference_point_m':PIVOT.tolist(),'nominal_grasp_reference_in_tool_m':anchor0.tolist(),'pitch_positive':'insertion tip moves toward tool +X','kept_fixed':['robot TCP and camera','socket','lighting','green handle angle','requested lateral center','requested non-pitch rotation'],'target_is_geometry_only':True,'training_performed':False,'new_training_labels_approved':False,'preview_tolerances':{'height_and_fore_aft_change_mm':.1,'pitch_change_deg':.5,'lateral_center_mm':.1,'non_pitch_rotation_deg':.5},'records':[]}
 cases=list(itertools.product([-3,0,3],[-1,0,1],[-4,0,4]));cases.sort(key=lambda v:(sum(x!=0 for x in v),v))
 if a.limit:cases=cases[:a.limit]
 for j,(forward,height,pitch) in enumerate(cases):
  requested={'fore_aft_mm':forward,'height_mm':height,'pitch_deg':pitch};desired=pose(anchor0,forward,height,pitch);check=measurements(desired,anchor0)
  assert abs(check['lateral_center_mm'])<1e-10 and check['non_pitch_rotation_deg']<1e-8
  assert max(abs(check[k]-requested[k]) for k in requested)<1e-8
  r.reset(Ttool,desired,np.random.default_rng(20261123));r.robot_pose(q);jaws=tangent_jaws(r.visual_gate,desired)
  if jaws:
   for side,value in jaws.items():r.d.joint('jaw_'+side).qpos[0]=value
  mujoco.mj_forward(r.m,r.d);target_gate=r.visual_gate.check(desired,jaws or {'left':0.,'right':0.});rgb,_=r.render();name=f'{j:02d}';target_image=f'frames/{name}_target.jpg';save_image(out,target_image,rgb)
  # Release target geometry into the unchanged GC-r01 free-body dynamics.
  # No module pose or velocity is overwritten during closing / holding.
  r.reset(Ttool,desired,np.random.default_rng(20261123));r.robot_pose(q)
  for side in ['left','right']:r.d.joint('jaw_'+side).qpos[0]=.002
  mujoco.mj_forward(r.m,r.d);trace=[];baseline=None
  for k in range(1200):
   if k==600:r.m.opt.gravity[:]=[0,0,-9.81]
   r.d.ctrl[:]=.002+(-.0015-.002)*min(r.d.time/.25,1);status=r.tick()
   if k>=800:
    T=np.array(status['T_TCP_from_module'])
    if baseline is None:baseline=T.copy()
    drift=float(np.linalg.norm(T[:3,3]-baseline[:3,3])*1000);angle=float(np.degrees(Rotation.from_matrix(T[:3,:3]@baseline[:3,:3].T).magnitude()))
    trace.append([float(r.d.time),*status['pad_normal_force_n'].values(),drift,angle,status['penetration_mm']])
  actualT=np.array(status['T_TCP_from_module']);actual=measurements(actualT,anchor0);physical_jaws={s:float(r.d.joint('jaw_'+s).qpos[0]) for s in ['left','right']};actual_gate=r.visual_gate.check(actualT,physical_jaws);tr=np.array(trace)
  stable=bool(np.min(tr[:,1:3])>=.1 and np.max(tr[:,3])<=.1 and np.max(tr[:,4])<=.5 and np.max(tr[:,5])<=.05 and actual_gate['accepted'])
  matches=bool(abs(actual['fore_aft_mm']-forward)<=.1 and abs(actual['height_mm']-height)<=.1 and abs(actual['pitch_deg']-pitch)<=.5 and abs(actual['lateral_center_mm'])<=.1 and actual['non_pitch_rotation_deg']<=.5)
  rgb,_=r.render();settled_image=f'frames/{name}_settled.jpg';save_image(out,settled_image,rgb)
  item={'id':name,'requested':requested,'target_T_tool_module':desired.tolist(),'target_image':target_image,'target_jaw_qpos_m':jaws,'target_visible_gate':target_gate,'settled_image':settled_image,'actual':actual,'actual_T_tool_module':actualT.tolist(),'settled_visible_gate':actual_gate,'settled_jaw_qpos_m':physical_jaws,'stable_contact':stable,'matches_three_variable_target':matches,'qualified_preview':bool(stable and matches),'minimum_each_force_N':float(np.min(tr[:,1:3])),'max_hold_slip_mm':float(np.max(tr[:,3])),'max_hold_rotation_deg':float(np.max(tr[:,4]))}
  np.savez_compressed(out/'frames'/f'{name}_settled_state.npz',qpos=r.d.qpos,qvel=r.d.qvel,mocap_pos=r.d.mocap_pos,mocap_quat=r.d.mocap_quat,ctrl=r.d.ctrl,trace=tr)
  manifest['records'].append(item);(out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2));print(json.dumps({k:item[k] for k in ['id','requested','actual','stable_contact','matches_three_variable_target']},ensure_ascii=False),flush=True)
 r.close();manifest['summary']={'cases':len(cases),'all_target_transforms_exactly_three_variable':True,'stable_contact_cases':sum(x['stable_contact'] for x in manifest['records']),'matching_target_cases':sum(x['matches_three_variable_target'] for x in manifest['records']),'qualified_preview_cases':sum(x['qualified_preview'] for x in manifest['records'])};(out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
 if not a.limit:make_sheets(out,manifest['records'])
 print(json.dumps(manifest['summary']),flush=True)

if __name__=='__main__':main()
