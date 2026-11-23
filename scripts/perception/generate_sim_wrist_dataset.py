"""Generate grouped, privileged-label wrist videos from the mounted robot scene.

MuJoCo FK + rendering only: these are known simulated poses, not a validated
contact-grasp simulation. Grasp configurations are independent across splits;
within a clip the grasp stays rigid while the real URDF arm follows a path.
"""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
os.environ.setdefault('MUJOCO_GL','egl')
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
import mujoco
import numpy as np
from PIL import Image
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation
from omi_shapeforge.sim.wrist_fisheye import FACES,CV_TO_GL,maps,reproject

SCENE=Path('/data/omi_runtime/runs/wg_r10_om_r08_isaac_20261122/integration/robot_scene')
BUNDLE=ROOT/'manifests/wrist_visual_asset_handoff_20261122.json'
TEMPLATES=Path('/data/omi_runtime/runs/interaction_surface_representation_20261122/network_templates')


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def transform(d,b):
    T=np.eye(4);T[:3,:3]=d.xmat[b].reshape(3,3);T[:3,3]=d.xpos[b];return T
def camera_transform(d,c):
    T=np.eye(4);T[:3,:3]=d.cam_xmat[c].reshape(3,3)@CV_TO_GL;T[:3,3]=d.cam_xpos[c];return T
def apply(points,T):return points@T[:3,:3].T+T[:3,3]


def verify_assets():
    bundle=read(BUNDLE);verified={}
    for item in bundle['assets'].values():
        for key in ['manifest','delivery_manifest']:
            if sha(item[key])!=item[key+'_sha256']:raise ValueError('Pinned asset manifest changed')
        for rel,h in read(item['delivery_manifest'])['files'].items():
            p=Path(item['directory'])/rel
            if sha(p)!=h:raise ValueError('Pinned asset changed: '+str(p))
            verified[str(p)]=h
    return verified


def create_scene(output,face_size):
    root=ET.parse(SCENE/'scene.xml').getroot()
    root.set('model','Privileged wrist image to complete surface dataset')
    visual=root.find('visual');global_=visual.find('global')
    global_.set('offwidth',str(max(face_size,640)));global_.set('offheight',str(max(face_size,360)))
    headlight=visual.find('headlight')
    if headlight is None:headlight=ET.SubElement(visual,'headlight')
    headlight.set('ambient','.4 .4 .4');headlight.set('diffuse','.55 .55 .55');headlight.set('specular','.2 .2 .2')
    if not any(x.get('type')=='skybox' for x in root.findall('asset/texture')):
        ET.SubElement(root.find('asset'),'texture',name='dataset_sky',type='skybox',builtin='gradient',rgb1='.18 .22 .26',rgb2='.07 .10 .13',width='512',height='3072')
    for item in root.find('asset'):
        if item.get('file'):item.set('file',str((SCENE/item.get('file')).resolve()))
    world=root.find('worldbody')
    for i in range(6):ET.SubElement(world,'camera',name=f'dataset_cube_{i}',pos='0 0 0',quat='1 0 0 0',fovy='90',ipd='0')
    ET.indent(root);ET.ElementTree(root).write(output,encoding='unicode')


class Renderer:
    def __init__(self,scene,calibration,face_size):
        self.m=mujoco.MjModel.from_xml_path(str(scene));self.d=mujoco.MjData(self.m)
        self.meta=read(SCENE/'robot_manifest.json');self.d.qpos[:]=self.meta['initial_qpos']
        self.m.opt.disableflags|=int(mujoco.mjtDisableBit.mjDSBL_CONTACT)
        self.opt=mujoco.MjvOption();self.opt.geomgroup[3:]=0;self.opt.sitegroup[:]=0
        self.opt.flags[mujoco.mjtVisFlag.mjVIS_JOINT]=False
        self.opt.flags[mujoco.mjtVisFlag.mjVIS_ACTUATOR]=False
        self.renderer=mujoco.Renderer(self.m,face_size,face_size)
        self.sampling=maps({'K':calibration['K'],'D':calibration['D'],'image_size':[calibration['image_width'],calibration['image_height']]},face_size)
        self.faces=[i for i,s in enumerate(self.sampling) if s[0].any()];self.face_size=face_size
        self.cam=self.m.camera('wrist_rgb').id;self.cubes=[self.m.camera(f'dataset_cube_{i}').id for i in range(6)]
        self.module=self.m.body('sim_module').id;self.socket=self.m.body('sim_socket').id;self.tcp=self.m.body('TCP_Link_L').id
        self.joints=np.array([self.m.joint(f'Arm_L{i}_Joint').id for i in range(1,8)]);self.qids=self.m.jnt_qposadr[self.joints];self.dids=self.m.jnt_dofadr[self.joints]
        self.base_pos=self.m.body_pos[self.module].copy();self.base_rot=Rotation.from_quat(np.roll(self.m.body_quat[self.module],-1)).as_matrix()
        self.base_q=np.array(self.meta['initial_qpos']);self.nominal_tcp=np.array(self.meta['preinsert_tcp_position']);self.nominal_R=np.array(self.meta['goal_tcp_rotation'])
        self.Rs=np.array(self.meta['socket_to_world']['rotation'])
        self.base_light_pos=self.m.light_pos.copy();self.base_light_diffuse=self.m.light_diffuse.copy();self.base_light_ambient=self.m.light_ambient.copy()
        self.table=self.m.geom('work_table').id;self.floor=self.m.geom('floor').id;self.base_rgba=self.m.geom_rgba.copy()
        self.handle=self.m.body('module_u_handle').id
        self.handle_pivot=np.asarray(read(read(BUNDLE)['assets']['module']['manifest'])['handle']['hinge_pivot_m'])
        self.module_geoms=[g for g in range(self.m.ngeom) if (self.m.geom(g).name or '').startswith('sim_module_') and (self.m.geom(g).name or '').endswith('_visual') and 'handle' not in self.m.geom(g).name]
        self.socket_geoms=[g for g in range(self.m.ngeom) if (self.m.geom(g).name or '').startswith('sim_socket_') and (self.m.geom(g).name or '').endswith('_visual')]
        self.overview=mujoco.Renderer(self.m,360,640)
        self.overview_camera=mujoco.MjvCamera();self.overview_camera.lookat[:]=[.42,.13,.78];self.overview_camera.distance=1.55;self.overview_camera.azimuth=125;self.overview_camera.elevation=-20
        mujoco.mj_forward(self.m,self.d)

    def set_grasp(self,translation_mm,angles_deg):
        R=Rotation.from_euler('xyz',angles_deg,degrees=True).as_matrix();pivot=np.array([0.,.025,0.])
        delta=np.array(translation_mm)/1000+pivot-R@pivot
        self.m.body_pos[self.module]=self.base_pos+self.base_rot@delta
        quat=Rotation.from_matrix(self.base_rot@R).as_quat();self.m.body_quat[self.module]=np.roll(quat,1)

    def randomize(self,rng):
        self.m.light_pos[:]=self.base_light_pos;self.m.light_pos[0,:2]+=rng.uniform(-.45,.45,2)
        self.m.light_diffuse[:]=self.base_light_diffuse*rng.uniform(.75,1.2)
        self.m.light_ambient[:]=self.base_light_ambient*rng.uniform(.8,1.2)
        self.m.geom_rgba[:]=self.base_rgba
        self.m.geom_rgba[self.table,:3]=np.array([.75,.76,.73])*rng.uniform(.8,1.1,3)
        self.m.geom_rgba[self.floor,:3]=np.array([.35,.38,.40])*rng.uniform(.75,1.2,3)
        angle=rng.uniform(-35,0);R=Rotation.from_euler('x',angle,degrees=True).as_matrix()
        self.m.body_pos[self.handle]=self.handle_pivot-R@self.handle_pivot;self.m.body_quat[self.handle]=np.roll(Rotation.from_matrix(R).as_quat(),1)
        self.handle_angle_deg=float(angle)

    def solve(self,pos,R):
        jp=np.zeros((3,self.m.nv));jr=np.zeros_like(jp)
        for _ in range(65):
            mujoco.mj_forward(self.m,self.d);current=transform(self.d,self.tcp)
            er=Rotation.from_matrix(R@current[:3,:3].T).as_rotvec();ep=pos-current[:3,3]
            if np.linalg.norm(ep)<1e-6 and np.linalg.norm(er)<1e-5:break
            mujoco.mj_jacBody(self.m,self.d,jp,jr,self.tcp);J=np.vstack([jp[:,self.dids],jr[:,self.dids]*.1]);e=np.r_[ep,er*.1]
            dq=J.T@np.linalg.solve(J@J.T+np.eye(6)*1e-6,e)
            self.d.qpos[self.qids]=np.clip(self.d.qpos[self.qids]+np.clip(dq,-.08,.08),self.m.jnt_range[self.joints,0]+1e-6,self.m.jnt_range[self.joints,1]-1e-6)
        mujoco.mj_forward(self.m,self.d);T=transform(self.d,self.tcp)
        return float(np.linalg.norm(pos-T[:3,3])*1000),float(np.linalg.norm(Rotation.from_matrix(R@T[:3,:3].T).as_rotvec())*180/np.pi)

    def labels(self):
        Twc=camera_transform(self.d,self.cam);Tcm=np.linalg.inv(Twc)@transform(self.d,self.module);Tcs=np.linalg.inv(Twc)@transform(self.d,self.socket)
        return {'T_camera_from_module':Tcm.tolist(),'T_camera_from_socket':Tcs.tolist(),'T_world_from_camera':Twc.tolist(),
                'T_world_from_tcp':transform(self.d,self.tcp).tolist(),'left_arm_qpos':self.d.qpos[self.qids].tolist(),
                'T_tcp_from_module':(np.linalg.inv(transform(self.d,self.tcp))@transform(self.d,self.module)).tolist()}

    def render(self,segmentation=False):
        Twc=camera_transform(self.d,self.cam);faces=[np.zeros((self.face_size,self.face_size,3),np.uint8) for _ in range(6)];segments={}
        for i in self.faces:
            c=self.cubes[i];self.m.cam_pos[c]=Twc[:3,3];q=np.empty(4);mujoco.mju_mat2Quat(q,(Twc[:3,:3]@FACES[i]@CV_TO_GL).ravel());self.m.cam_quat[c]=q
        mujoco.mj_forward(self.m,self.d)
        for i in self.faces:
            self.renderer.update_scene(self.d,camera=self.cubes[i],scene_option=self.opt);faces[i]=self.renderer.render().copy()
            if segmentation:
                self.renderer.enable_segmentation_rendering();self.renderer.update_scene(self.d,camera=self.cubes[i],scene_option=self.opt);segments[i]=self.renderer.render()[:,:,0].copy();self.renderer.disable_segmentation_rendering()
        rgb=reproject(faces,self.sampling)
        if segmentation:
            seg=np.full(rgb.shape[:2],-1,np.int32)
            for i in self.faces:
                mask,u,v=self.sampling[i];seg[mask]=segments[i][np.rint(v).astype(int),np.rint(u).astype(int)]
            return rgb,seg
        return rgb,None

    def render_overview(self):
        self.overview.update_scene(self.d,camera=self.overview_camera,scene_option=self.opt);return self.overview.render().copy()

    def close(self):self.renderer.close();self.overview.close()


def start_video(path,width,height,fps):
    return subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s',f'{width}x{height}','-r',str(fps),'-i','-','-an','-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p',str(path)],stdin=subprocess.PIPE)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--train-clips',type=int,default=160);p.add_argument('--val-clips',type=int,default=24);p.add_argument('--test-clips',type=int,default=32);p.add_argument('--frames',type=int,default=16);p.add_argument('--width',type=int,default=640);p.add_argument('--height',type=int,default=360);p.add_argument('--face-size',type=int,default=448);p.add_argument('--fps',type=int,default=8);a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=False);verified=verify_assets();source_meta=read(SCENE/'robot_manifest.json')
    cal=read('/home/linux/Downloads/img/wrist_intrinsics_1920x1080.json');sx=a.width/cal['image_width'];sy=a.height/cal['image_height'];A=np.array([[sx,0,(sx-1)/2],[0,sy,(sy-1)/2],[0,0,1.]])
    cal.update(K=(A@np.array(cal['K'])).tolist(),image_width=a.width,image_height=a.height,resize_pixel_transform=A.tolist(),image_domain='rendered full-field fisheye image, pixel-center consistent scaled intrinsics')
    (a.output/'calibration.json').write_text(json.dumps(cal,indent=2));create_scene(a.output/'scene.xml',a.face_size);renderer=Renderer(a.output/'scene.xml',cal,a.face_size)
    config={'generator_sha256':sha(__file__),'source_scene':str(SCENE/'scene.xml'),'source_scene_sha256':sha(SCENE/'scene.xml'),'derived_scene':str(a.output/'scene.xml'),'derived_scene_sha256':sha(a.output/'scene.xml'),
            'bundle':str(BUNDLE),'bundle_sha256':sha(BUNDLE),'source_asset_files_verified':len(verified),'engine':'MuJoCo '+mujoco.__version__,
            'kinematic_frames_only':True,'physical_grasp_dynamics_validated':False,'module_render_asset':'OM-001/V4 r08','tool_render_asset':'WG-r10','socket_asset':'SIM-r06',
            'templates':str(TEMPLATES),'template_manifest_sha256':sha(TEMPLATES/'manifest.json'),'fps':a.fps,'frames_per_clip':a.frames,
            'grasp_translation_mm_ranges':[[-.5,.5],[-4,4],[-1,1]],'grasp_euler_deg_ranges':[[-4,4],[-1.5,1.5],[-1.5,1.5]],'rotation_pivot_module_m':[0,.025,0],
            'split_by':'independent entire grasp/arm/light clips, no adjacent frames across splits','visibility_supervision':'first-frame segmentation QA only; no trained visibility head claimed',
            'green_handle_nuisance_range_deg':[-35,0],'green_handle_in_target_template':False,
            'created_utc':datetime.now(timezone.utc).isoformat(),'arguments':vars(a)|{'output':str(a.output)}}
    (a.output/'config.json').write_text(json.dumps(config,indent=2));records=[];episodes=[];start=time.time();serial=0
    for split,nclips,seed in [('train',a.train_clips,37101),('val',a.val_clips,69103),('test',a.test_clips,97109)]:
        for clip in range(nclips):
            rng=np.random.default_rng(np.random.SeedSequence([seed,clip]));eid=f'{split}_{clip:04d}';folder=a.output/'episodes'/eid;folder.mkdir(parents=True)
            grasp_xyz=rng.uniform([-.5,-4,-1],[.5,4,1]);grasp_rpy=rng.uniform([-4,-1.5,-1.5],[4,1.5,1.5])
            renderer.d.qpos[:]=renderer.base_q;renderer.d.qpos[renderer.qids]+=rng.normal(0,.025,7);renderer.set_grasp(grasp_xyz,grasp_rpy);renderer.randomize(rng)
            # Robot moves relative to the static socket. Keep a positive nominal
            # approach gap; this dataset does not claim an executed insertion.
            center=rng.uniform([-.010,.023,-.008],[.010,.055,.008]);amplitude=rng.uniform([.002,.006,.002],[.007,.015,.006]);phase=rng.uniform(-np.pi,np.pi,3)
            angles=rng.uniform(-3,3,3);angle_amp=rng.uniform(.5,2,3)
            video=start_video(folder/'wrist.mp4',a.width,a.height,a.fps)
            overview=start_video(folder/'robot_overview.mp4',640,360,a.fps) if clip<2 else None
            qlog=[];module_labels=[];socket_labels=[];qa=None
            for f in range(a.frames):
                tau=2*np.pi*f/max(1,a.frames-1);offset=center+amplitude*np.sin(tau+phase)
                target_pos=renderer.nominal_tcp+renderer.Rs@offset;dr=Rotation.from_euler('xyz',angles+angle_amp*np.sin(tau+phase),degrees=True).as_matrix();target_R=renderer.nominal_R@dr
                ep,er=renderer.solve(target_pos,target_R)
                if ep>.1 or er>.05:raise RuntimeError(f'IK outside tolerance at {eid}/{f}: {ep} mm {er} deg')
                label=renderer.labels();rgb,seg=renderer.render(segmentation=f==0)
                if f==0:
                    qa={}
                    for kind,gids in [('module',renderer.module_geoms),('socket',renderer.socket_geoms)]:
                        yy,xx=np.where(np.isin(seg,gids));qa[kind]={'visible_pixels':len(xx),'bbox_xyxy':[int(xx.min()),int(yy.min()),int(xx.max()),int(yy.max())] if len(xx) else None}
                    if qa['module']['visible_pixels']<60 or qa['socket']['visible_pixels']<100:raise RuntimeError('Target visibility QA failed: '+eid+' '+str(qa))
                    np.save(folder/'first_segmentation.npy',seg)
                path=folder/f'{f:04d}.jpg';Image.fromarray(rgb).save(path,quality=95,subsampling=0);video.stdin.write(rgb.tobytes())
                if overview:overview.stdin.write(renderer.render_overview().tobytes())
                row={'id':serial,'episode':eid,'frame':f,'split':split,'image':str(path.relative_to(a.output)),'image_sha256':sha(path),'time_s':f/a.fps,
                     **label,'ik_position_error_mm':ep,'ik_angle_error_deg':er,'label_source':'simulator FK privileged transforms','training_label_valid':True,'real_world_ground_truth':False}
                records.append(row);qlog.append(label['left_arm_qpos']);module_labels.append(label['T_camera_from_module']);socket_labels.append(label['T_camera_from_socket']);serial+=1
            video.stdin.close();code=video.wait()
            if code:raise RuntimeError('Video encode failed')
            if overview:
                overview.stdin.close()
                if overview.wait():raise RuntimeError('Overview encode failed')
            module_var=float(np.max(np.abs(np.array(module_labels)-np.array(module_labels)[0])))
            if module_var>1e-9:raise RuntimeError('Rigid grasp must remain constant relative to wrist camera within clip')
            epmeta={'episode':eid,'split':split,'grasp_translation_mm':grasp_xyz.tolist(),'grasp_rpy_deg':grasp_rpy.tolist(),'handle_angle_deg':renderer.handle_angle_deg,'arm_path_center_m':center.tolist(),
                    'arm_path_amplitude_m':amplitude.tolist(),'arm_rotation_center_deg':angles.tolist(),'first_frame_visibility':qa,
                    'qpos_range_rad':np.ptp(np.array(qlog),axis=0).tolist(),'module_camera_matrix_max_variation':module_var,
                    'socket_camera_translation_range_mm':(np.ptp(np.array(socket_labels)[:,:3,3],axis=0)*1000).tolist(),'frames':a.frames}
            episodes.append(epmeta);(folder/'episode.json').write_text(json.dumps(epmeta,indent=2))
            (a.output/'records.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in records));(a.output/'episodes.json').write_text(json.dumps(episodes,indent=2))
            print(json.dumps({'episode':eid,'frames_total':len(records),'elapsed_s':round(time.time()-start,2),'qa':qa}),flush=True)
    renderer.close()
    changed=[p for p,h in verified.items() if sha(p)!=h]
    if changed:raise ValueError('Source assets changed during capture')
    final={'frames':len(records),'clips':len(episodes),'split_frames':{s:sum(r['split']==s for r in records) for s in ['train','val','test']},
           'split_clips':{s:sum(r['split']==s for r in episodes) for s in ['train','val','test']},'elapsed_s':time.time()-start,'source_assets_verified_unchanged':len(verified),
           'geometry_label_validation_pending':True,'not_physical_grasp_validation':True}
    (a.output/'complete.json').write_text(json.dumps(final,indent=2));print(json.dumps(final),flush=True)


if __name__=='__main__':main()
