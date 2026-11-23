"""GC-r01 contact-driven module with FK-driven robot visual context.

The dynamic tool follows a mocap TCP target; the module is a free rigid body.
Robot links are visual-only FK replay, not a force-controlled arm. Socket
contacts are disabled: this is a contact-qualified pre-insertion dataset.
"""
import argparse,copy,json,os,sys,time,hashlib
from pathlib import Path
import xml.etree.ElementTree as ET
os.environ.setdefault('MUJOCO_GL','egl')
import mujoco
import numpy as np
from PIL import Image
from scipy.spatial.transform import Rotation,Slerp
from generate_sim_wrist_dataset import (SCENE,Renderer,read,sha,transform,camera_transform,start_video,ROOT)
from omi_shapeforge.sim.wrist_fisheye import maps
GC=Path('/data/omi_runtime/assets/daimon/wrist_grasp_contact_r01')
sys.path.insert(0,str(GC/'scripts'))
from grasp_status import grasp_status
from contact_visual_gate import VisibleGraspGate


def set_pose(e,T):
    e.set('pos',' '.join(map(str,T[:3,3])));e.set('quat',' '.join(map(str,np.roll(Rotation.from_matrix(T[:3,:3]).as_quat(),1))))


def create_scene(out,face):
    old=ET.parse(SCENE/'scene.xml').getroot();root=ET.parse(GC/'initial_closure_scene.xml').getroot()
    base=mujoco.MjModel.from_xml_path(str(SCENE/'scene.xml'));bd=mujoco.MjData(base);bd.qpos[:]=read(SCENE/'robot_manifest.json')['initial_qpos'];mujoco.mj_forward(base,bd)
    gc=mujoco.MjModel.from_xml_path(str(GC/'initial_closure_scene.xml'));gd=mujoco.MjData(gc);mujoco.mj_forward(gc,gd)
    tcp=transform(bd,base.body('TCP_Link_L').id);Ttm=np.linalg.inv(transform(gd,gc.body('audit_tool').id))@transform(gd,gc.body('sim_module').id)
    root.set('model','GC-r01 qualified grasp wrist learning');root.find('visual/global').set('offwidth',str(max(face,640)));root.find('visual/global').set('offheight',str(max(face,360)))
    head=root.find('visual/headlight');head.set('active','0')
    set_pose(root.find(".//body[@name='audit_tool']"),tcp);set_pose(root.find(".//body[@name='grasp_target']"),tcp);set_pose(root.find(".//body[@name='sim_module']"),tcp@Ttm)
    set_pose(root.find(".//body[@name='sim_socket']"),transform(bd,base.body('sim_socket').id))
    root.find(".//camera[@name='asset_pinhole']").set('name','wrist_rgb')
    for i,c in enumerate(root.findall('worldbody/camera')):c.set('name',f'dataset_cube_{i}')
    # Import full robot visual hierarchy, remove previous module/tool assembly,
    # joints and cameras. Actual FK body transforms are installed each frame.
    robot=copy.deepcopy(old.find("worldbody/body[@name='ZJ_Robot_link']"))
    for parent in list(robot.iter()):
        for child in list(parent):
            n=child.get('name','')
            if child.tag in ['joint','freejoint','camera','site'] or n in ['sim_module','module_u_handle'] or n.startswith('wrist_tool'):parent.remove(child)
    for e in robot.iter():
        if 'name' in e.attrib:e.set('name','robot_'+e.get('name'))
        for ref in ['mesh','material']:
            if ref in e.attrib:e.set(ref,'robot_'+e.get(ref))
        if e.tag=='geom':e.set('contype','0');e.set('conaffinity','0')
    root.find('worldbody').append(robot)
    for asset in old.find('asset'):
        if asset.tag=='texture' and asset.get('type')=='skybox':continue
        e=copy.deepcopy(asset)
        if 'name' in e.attrib:e.set('name','robot_'+e.get('name'))
        if 'texture' in e.attrib:e.set('texture','robot_'+e.get('texture'))
        if 'file' in e.attrib:e.set('file',str((SCENE/e.get('file')).resolve()))
        root.find('asset').append(e)
    for g in old.findall('worldbody/geom'):
        e=copy.deepcopy(g);e.set('contype','0');e.set('conaffinity','0')
        if 'material' in e.attrib:e.set('material','robot_'+e.get('material'))
        root.find('worldbody').append(e)
    ET.indent(root);ET.ElementTree(root).write(out,encoding='unicode')
    dependencies={str(GC/'initial_closure_scene.xml'):sha(GC/'initial_closure_scene.xml')}
    for e in root.findall('asset/*'):
        if e.get('file'):dependencies[e.get('file')]=sha(e.get('file'))
    return Ttm,dependencies


class ContactRenderer:
    solve=Renderer.solve
    render=Renderer.render
    render_overview=Renderer.render_overview
    close=Renderer.close
    def __init__(self,scene,cal,face):
        # Dedicated inverse-kinematics model; its contact-free status is never
        # used as evidence about grasp. Contact state lives in self.m/self.d.
        self.ikm=mujoco.MjModel.from_xml_path(str(SCENE/'scene.xml'));self.ikd=mujoco.MjData(self.ikm);self.meta=read(SCENE/'robot_manifest.json');self.ikd.qpos[:]=self.meta['initial_qpos']
        self.m=mujoco.MjModel.from_xml_path(str(scene));self.d=mujoco.MjData(self.m)
        self.joints=np.array([self.ikm.joint(f'Arm_L{i}_Joint').id for i in range(1,8)]);self.qids=self.ikm.jnt_qposadr[self.joints];self.dids=self.ikm.jnt_dofadr[self.joints];self.iktcp=self.ikm.body('TCP_Link_L').id
        self.nominal_tcp=np.array(self.meta['preinsert_tcp_position']);self.nominal_R=np.array(self.meta['goal_tcp_rotation']);self.Rs=np.array(self.meta['socket_to_world']['rotation'])
        self.tcp=self.m.body('audit_tool').id;self.module=self.m.body('sim_module').id;self.socket=self.m.body('sim_socket').id;self.mid=int(self.m.body_mocapid[self.m.body('grasp_target').id])
        self.cam=self.m.camera('wrist_rgb').id;self.cubes=[self.m.camera(f'dataset_cube_{i}').id for i in range(6)]
        self.handle=self.m.body('new_u_handle').id;self.pivot=np.array([0,.0055747193118635165,.020880750794140167])
        self.robot_map=[(b,self.ikm.body(self.m.body(b).name[6:]).id) for b in range(self.m.nbody) if (self.m.body(b).name or '').startswith('robot_')]
        self.opt=mujoco.MjvOption();self.opt.geomgroup[3:]=0;self.opt.sitegroup[:]=0
        self.renderer=mujoco.Renderer(self.m,face,face);self.face_size=face;self.sampling=maps({'K':cal['K'],'D':cal['D'],'image_size':[cal['image_width'],cal['image_height']]},face);self.faces=[i for i,s in enumerate(self.sampling) if s[0].any()]
        self.overview=mujoco.Renderer(self.m,360,640);self.overview_camera=mujoco.MjvCamera();self.overview_camera.lookat[:]=[.42,.13,.78];self.overview_camera.distance=1.55;self.overview_camera.azimuth=125;self.overview_camera.elevation=-20
        self.module_geoms=[g for g in range(self.m.ngeom) if self.m.geom_bodyid[g]==self.module and self.m.geom_group[g]<3 and self.m.geom_type[g]==mujoco.mjtGeom.mjGEOM_MESH];self.socket_geoms=[g for g in range(self.m.ngeom) if self.m.geom_bodyid[g]==self.socket and self.m.geom_group[g]<3]
        self.visual_gate=VisibleGraspGate()
        self.light_pos=self.m.light_pos.copy();self.light_diffuse=self.m.light_diffuse.copy();self.rgba=self.m.geom_rgba.copy()

    def ik(self,pos,R):
        m,d,tcp=self.m,self.d,self.tcp
        self.m,self.d,self.tcp=self.ikm,self.ikd,self.iktcp
        try:ep,er=self.solve(pos,R);T=transform(self.d,self.tcp);q=self.d.qpos.copy()
        finally:self.m,self.d,self.tcp=m,d,tcp
        return T,q,ep,er

    def robot_pose(self,q):
        self.ikd.qpos[:]=q;mujoco.mj_forward(self.ikm,self.ikd)
        for b,old in self.robot_map:
            par=self.ikm.body_parentid[old];T=np.linalg.inv(transform(self.ikd,par))@transform(self.ikd,old)
            self.m.body_pos[b]=T[:3,3];self.m.body_quat[b]=np.roll(Rotation.from_matrix(T[:3,:3]).as_quat(),1)

    def reset(self,T,relative,rng):
        mujoco.mj_resetData(self.m,self.d);self.m.opt.gravity[:]=0
        for joint,pose in [('tool_free',T),('module_free',T@relative)]:self.d.joint(joint).qpos[:]=np.r_[pose[:3,3],np.roll(Rotation.from_matrix(pose[:3,:3]).as_quat(),1)]
        self.d.mocap_pos[self.mid]=T[:3,3];self.d.mocap_quat[self.mid]=np.roll(Rotation.from_matrix(T[:3,:3]).as_quat(),1)
        angle=rng.uniform(-35,0);R=Rotation.from_euler('x',angle,degrees=True).as_matrix();self.m.body_pos[self.handle]=self.pivot-R@self.pivot;self.m.body_quat[self.handle]=np.roll(Rotation.from_matrix(R).as_quat(),1);self.handle_angle_deg=float(angle)
        self.m.light_pos[:]=self.light_pos;self.m.light_pos[0,:2]+=rng.uniform(-.25,.25,2);self.m.light_diffuse[:]=self.light_diffuse*rng.uniform(.8,1.2)
        self.m.geom_rgba[:]=self.rgba
        for name in ['work_table','floor']:
            g=self.m.geom(name).id;self.m.geom_rgba[g,:3]=self.rgba[g,:3]*rng.uniform(.8,1.1)
        mujoco.mj_forward(self.m,self.d)

    def tick(self,target=None,closing=False):
        if target is not None:self.d.mocap_pos[self.mid]=target[:3,3];self.d.mocap_quat[self.mid]=np.roll(Rotation.from_matrix(target[:3,:3]).as_quat(),1)
        if closing:self.d.ctrl[:]=-.0015*min(self.d.time/.25,1)
        mujoco.mj_step(self.m,self.d,nstep=5);mujoco.mj_forward(self.m,self.d)
        status=grasp_status(self.m,self.d);status['penetration_mm']=max([0.]+[-float(c.dist)*1000 for c in self.d.contact])
        return status

    def labels(self):
        Twc=camera_transform(self.d,self.cam)
        return {'T_camera_from_module':(np.linalg.inv(Twc)@transform(self.d,self.module)).tolist(),'T_camera_from_socket':(np.linalg.inv(Twc)@transform(self.d,self.socket)).tolist(),'T_world_from_camera':Twc.tolist(),'T_world_from_tcp':transform(self.d,self.tcp).tolist(),'T_tcp_from_module':(np.linalg.inv(transform(self.d,self.tcp))@transform(self.d,self.module)).tolist(),'left_arm_qpos':self.ikd.qpos[self.qids].tolist()}


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);ap.add_argument('--train-clips',type=int,default=192);ap.add_argument('--val-clips',type=int,default=32);ap.add_argument('--test-clips',type=int,default=32);ap.add_argument('--frames',type=int,default=12);ap.add_argument('--face-size',type=int,default=672);ap.add_argument('--fps',type=int,default=6);ap.add_argument('--shards',type=int,default=1);ap.add_argument('--shard-id',type=int,default=0);ap.add_argument('--only-episodes',nargs='*');a=ap.parse_args()
    a.output.mkdir(parents=True,exist_ok=False);Ttm,deps=create_scene(a.output/'scene.xml',a.face_size)
    cal=read('/home/linux/Downloads/img/wrist_intrinsics_1920x1080.json');A=np.array([[.5,0,-.25],[0,.5,-.25],[0,0,1.]])
    cal.update(K=(A@np.array(cal['K'])).tolist(),image_width=960,image_height=540,resize_pixel_transform=A.tolist(),image_domain='GC-r01 dynamic contact, full-field fisheye')
    (a.output/'calibration.json').write_text(json.dumps(cal,indent=2));(a.output/'dependencies.json').write_text(json.dumps(deps,indent=2))
    config={'source_scene':str(GC/'initial_closure_scene.xml'),'source_scene_sha256':sha(GC/'initial_closure_scene.xml'),'derived_scene':str(a.output/'scene.xml'),'derived_scene_sha256':sha(a.output/'scene.xml'),'generator_sha256':sha(__file__),'fps':a.fps,'frames_per_clip':a.frames,'tool_render_asset':'WG-r15','module_render_asset':'OM-r08','socket_asset':'SIM-r06','contact_asset':'GC-r01','kinematic_frames_only':False,'robot_control':'FK visual replay; dynamic free tool follows planned TCP via mocap weld','module_attachment':'freejoint; no weld, no pose overwrite after initial placement','socket_contacts_enabled':False,'contact_sample_period_ms':1,'physics_timestep_ms':.2,'physical_grasp_dynamics_validated':'per accepted trajectory, simulation only','initial_offsets_tool_xyz_mm':[[-.5,.5],[-.4,.4],[-1.5,1.5]],'initial_rotation_tool_xyz_deg':[[-1,1],[-.5,.5],[-.5,.5]],'gate':{'minimum_each_pad_force_N':.1,'max_slip_mm':.1,'max_rotation_drift_deg':.5,'max_collision_penetration_mm':.05},'split_by':'independent closure and trajectory seeds per episode','accepted_visual_scheme':'whole_grid','real_world_ground_truth':False,'shard_id':a.shard_id,'shards':a.shards}
    (a.output/'config.json').write_text(json.dumps(config,indent=2));r=ContactRenderer(a.output/'scene.xml',cal,a.face_size);records=[];episodes=[];attempts=[];started=time.time()
    def save():
        (a.output/'records.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in records));(a.output/'episodes.json').write_text(json.dumps(episodes,indent=2));(a.output/'attempts.json').write_text(json.dumps(attempts,indent=2))
    for split,num,seed in [('train',a.train_clips,137101),('val',a.val_clips,169103),('test',a.test_clips,197109)]:
        for clip in range(num):
            if clip%a.shards!=a.shard_id:continue
            if a.only_episodes and f'{split}_{clip:04d}' not in a.only_episodes:continue
            accepted=False
            for attempt in range(20):
                rng=np.random.default_rng(np.random.SeedSequence([seed,clip,attempt]));eid=f'{split}_{clip:04d}';xyz=rng.uniform([-.5,-.4,-1.5],[.5,.4,1.5]);angles=rng.uniform([-1,-.5,-.5],[1,.5,.5]);rel=Ttm.copy();rel[:3,3]+=xyz/1000;rel[:3,:3]=Rotation.from_euler('xyz',angles,degrees=True).as_matrix()@rel[:3,:3]
                center=rng.uniform([-.010,.028,-.008],[.010,.055,.008]);amp=rng.uniform([.001,.003,.001],[.004,.007,.003]);phase=rng.uniform(-np.pi,np.pi,3);orient=rng.uniform(-3,3,3)
                paths=[];r.ikd.qpos[:]=r.meta['initial_qpos']
                for f in range(a.frames):
                    tau=2*np.pi*f/max(1,a.frames-1);T,q,ep,er=r.ik(r.nominal_tcp+r.Rs@(center+amp*np.sin(tau+phase)),r.nominal_R@Rotation.from_euler('xyz',orient+np.sin(tau+phase),degrees=True).as_matrix());paths.append((T,q,ep,er))
                if any(ep>.1 or er>.05 for _,_,ep,er in paths):raise RuntimeError('IK failed')
                r.reset(paths[0][0],rel,rng);r.robot_pose(paths[0][1]);trace=[];reason=None;baseline=None;frames=[];maxslip=0.;maxrot=0.;minforce=float('inf');maxpen=0.
                def gate(status,stage):
                    nonlocal baseline,reason,maxslip,maxrot,minforce,maxpen
                    T=np.array(status['T_TCP_from_module']);forces=list(status['pad_normal_force_n'].values());minforce=min(minforce,min(forces));maxpen=max(maxpen,status['penetration_mm'])
                    if baseline is None:baseline=T.copy()
                    slip=float(np.linalg.norm(T[:3,3]-baseline[:3,3])*1000);rot=float(np.degrees(Rotation.from_matrix(T[:3,:3]@baseline[:3,:3].T).magnitude()));maxslip=max(maxslip,slip);maxrot=max(maxrot,rot)
                    if not status['held']:reason='bilateral_contact_lost'
                    elif slip>.1 or rot>.5:reason='unstable_grasp'
                    elif status['penetration_mm']>.05:reason='excess_penetration'
                    trace.append([float(r.d.time),*forces,slip,rot,status['penetration_mm']])
                    return reason is None
                for k in range(1100):
                    if k==600:r.m.opt.gravity[:]=[0,0,-9.81]
                    st=r.tick(closing=True)
                    if k>=800 and not gate(st,'hold'):break
                if reason is None:
                    for f,(T,q,ep,er) in enumerate(paths):
                        if f:
                            prev=paths[f-1][0];steps=int(round(1/a.fps/.001));interp=Slerp([0,1],Rotation.from_matrix(np.stack([prev[:3,:3],T[:3,:3]])))
                            for k in range(steps):
                                u=(k+1)/steps;u=u*u*(3-2*u);target=np.eye(4);target[:3,3]=prev[:3,3]*(1-u)+T[:3,3]*u;target[:3,:3]=interp(u).as_matrix();st=r.tick(target)
                                if not gate(st,'move'):break
                            if reason:break
                        r.robot_pose(q);mujoco.mj_forward(r.m,r.d);label=r.labels();visual_check=r.visual_gate.check(np.array(label['T_tcp_from_module']),{side:float(r.d.joint('jaw_'+side).qpos[0]) for side in ['left','right']})
                        if not visual_check['accepted']:reason='visible_surface_intersection_or_gap';break
                        rgb,seg=r.render(segmentation=f==0)
                        qa=None
                        if f==0:
                            qa={}
                            for name,gids in [('module',r.module_geoms),('socket',r.socket_geoms)]:
                                yy,xx=np.where(np.isin(seg,gids));qa[name]={'visible_pixels':len(xx),'bbox_xyxy':[int(xx.min()),int(yy.min()),int(xx.max()),int(yy.max())] if len(xx) else None}
                            if qa['module']['visible_pixels']<60 or qa['socket']['visible_pixels']<100:reason='visibility';break
                        frames.append({'rgb':rgb,'label':label,'qpos':r.d.qpos.copy(),'qvel':r.d.qvel.copy(),'mocap_pos':r.d.mocap_pos.copy(),'mocap_quat':r.d.mocap_quat.copy(),'ctrl':r.d.ctrl.copy(),'time':float(r.d.time),'robot_qpos':q,'qa':qa,'status':grasp_status(r.m,r.d),'visual_check':visual_check,'overview':r.render_overview() if clip<2 else None,'ep':ep,'er':er})
                entry={'episode':eid,'attempt':attempt,'accepted':reason is None,'reason':reason,'initial_offset_tool_mm':xyz.tolist(),'initial_rpy_tool_deg':angles.tolist(),'minimum_pad_force_n':minforce if np.isfinite(minforce) else None,'max_slip_mm':maxslip,'max_rotation_drift_deg':maxrot,'max_penetration_mm':maxpen,'samples_checked':len(trace)};attempts.append(entry)
                if reason:
                    failed=a.output/'rejected';failed.mkdir(exist_ok=True);np.savez_compressed(failed/f'{eid}_attempt{attempt}.npz',trace=np.array(trace),qpos=r.d.qpos,qvel=r.d.qvel);save();print(json.dumps(entry),flush=True);continue
                folder=a.output/'episodes'/eid;folder.mkdir(parents=True);v=start_video(folder/'wrist.mp4',960,540,a.fps);ov=start_video(folder/'robot_overview.mp4',640,360,a.fps) if clip<2 else None
                for f,item in enumerate(frames):
                    path=folder/f'{f:04d}.jpg';Image.fromarray(item['rgb']).save(path,quality=95,subsampling=0);v.stdin.write(item['rgb'].tobytes())
                    if ov:ov.stdin.write(item['overview'].tobytes())
                    records.append({'id':len(records),'episode':eid,'frame':f,'split':split,'image':str(path.relative_to(a.output)),'image_sha256':sha(path),'time_s':item['time'],**item['label'],'contact':item['status'],'visible_surface_gate':item['visual_check'],'ik_position_error_mm':item['ep'],'ik_angle_error_deg':item['er'],'training_label_valid':True,'real_world_ground_truth':False,'label_source':'actual dynamic module/tool state; FK robot visual context'})
                v.stdin.close();assert v.wait()==0
                if ov:ov.stdin.close();assert ov.wait()==0
                np.savez_compressed(folder/'states.npz',**{key:np.array([x[key] for x in frames]) for key in ['qpos','qvel','mocap_pos','mocap_quat','ctrl','time','robot_qpos']},contact_trace=np.array(trace))
                delta=np.linalg.inv(Ttm)@rel;epmeta={'episode':eid,'split':split,'frames':a.frames,'initial_offset_tool_mm':xyz.tolist(),'initial_rpy_tool_deg':angles.tolist(),'grasp_translation_mm':(Ttm[:3,:3].T@xyz).tolist(),'grasp_rpy_deg':Rotation.from_matrix(delta[:3,:3]).as_euler('xyz',degrees=True).tolist(),'handle_angle_deg':r.handle_angle_deg,'qpos_range_rad':np.ptp([x['label']['left_arm_qpos'] for x in frames],axis=0).tolist(),'qa_first_frame':frames[0]['qa'],'contact_validation':entry}
                episodes.append(epmeta);(folder/'episode.json').write_text(json.dumps(epmeta,indent=2));save();print(json.dumps({'episode':eid,'frames_total':len(records),'elapsed_s':round(time.time()-started,1),'contact':entry,'qa':frames[0]['qa']}),flush=True);accepted=True;break
            if not accepted:raise RuntimeError('20 failed closures: '+eid)
    r.close()
    if any(sha(p)!=h for p,h in deps.items()):raise RuntimeError('Source changed')
    final={'frames':len(records),'clips':len(episodes),'split_frames':{s:sum(x['split']==s for x in records) for s in ['train','val','test']},'split_clips':{s:sum(x['split']==s for x in episodes) for s in ['train','val','test']},'attempts':len(attempts),'rejected':sum(not x['accepted'] for x in attempts),'elapsed_s':time.time()-started,'all_accepted_episodes_pass_contact_gate':True,'source_assets_unchanged':True,'insertion_validated':False}
    (a.output/'complete.json').write_text(json.dumps(final,indent=2));print(json.dumps(final),flush=True)

if __name__=='__main__':main()
