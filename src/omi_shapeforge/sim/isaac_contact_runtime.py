"""PhysX stepping, task measurements and independent CPU kinematics.

No MuJoCo import or simulation is used here. USD/PhysX supply actual state.
"""
from collections import deque
from copy import deepcopy
import json
import time
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from pxr import Usd, UsdGeom, UsdPhysics, PhysicsSchemaTools
import omni.physx

from .isaac_contact_kinematics import Kinematics, local_pose, transform


class DirectWorld:
    """Explicit attach/simulate/fetch path, independent of Kit timeline warm-up."""
    def __init__(self,stage,app,dt,*,render_subframes=2):
        self.stage,self.app,self.dt=stage,app,dt;self.time=0.
        if type(render_subframes) is not int or render_subframes not in (1,2):raise ValueError('render subframes must be 1 or 2')
        self.render_subframes=render_subframes
        self.sim=omni.physx.get_physx_simulation_interface()
        self.physx=omni.physx.get_physx_interface()
    def reset(self):
        from pxr import UsdUtils
        import carb.settings
        import omni.physics.tensors
        carb.settings.get_settings().set('/physics/updateToUsd',False)
        self.stage_id=UsdUtils.StageCache.Get().Insert(self.stage).ToLongInt()
        if not self.sim.attach_stage(self.stage_id):raise RuntimeError('PhysX stage attach failed')
        self.step();self.sync()
        self.tensor=omni.physics.tensors.create_simulation_view('numpy')
        self.tensor.set_subspace_roots('/')
    def step(self,render=False):
        if hasattr(self,'before_step'):
            self.tensor.clear_forces()
            self.sync()
            self.before_step()
        self.sim.simulate(self.dt,self.time);self.sim.fetch_results()
        self.time+=self.dt
        if render:self.render()
    def sync(self):self.physx.update_transformations(False,True,True,False)
    def render(self):
        self.sync()
        import omni.replicator.core as rep
        rep.orchestrator.step(delta_time=0.,rt_subframes=self.render_subframes,pause_timeline=True)


class TensorArticulation:
    def __init__(self,world):
        self.view=world.tensor.create_articulation_view('/World/Robot/ZJ_Robot_link')
        if self.view.count!=1:raise RuntimeError(f'Expected one robot articulation, got {self.view.count}')
        self.dof_names=list(self.view.shared_metatype.dof_names)
        self.indices=np.array([0],np.uint32)
    def get_joint_positions(self):return self.view.get_dof_positions().copy()
    def set_joint_positions(self,q):self.view.set_dof_positions(np.asarray(q,np.float32),self.indices)
    def set_joint_velocities(self,q):self.view.set_dof_velocities(np.asarray(q,np.float32),self.indices)
    def set_joint_position_targets(self,q):self.view.set_dof_position_targets(np.asarray(q,np.float32),self.indices)




class ContactMonitor:
    def __init__(self,dt,shoulder_pair=None):
        self.shoulder_pair=shoulder_pair or ('sim_module_006_collision','sim_socket_008_collision')
        self.dt=dt;self.clear()
        self.sub=omni.physx.get_physx_simulation_interface().subscribe_contact_report_events(self.callback)
    def clear(self):
        self.peak=0.;self.peak_force=0.;self.shoulder=False;self.pairs=set();self.last=dict(force_N=0.,shoulder=False)
        self.module_impulse=0.;self.sample_count=0;self.module_contact=False
        self.grasp_impulse={'left':0.,'right':0.}
        self.last_grasp_force_N={'left':0.,'right':0.}
        self.previous_grasp_force_N={'left':0.,'right':0.}
        if not hasattr(self,'active_grasp_pairs'):self.active_grasp_pairs={'left':set(),'right':set()}
        self.last_grasp_contact={side:bool(pairs) for side,pairs in self.active_grasp_pairs.items()}
        self.previous_grasp_contact=self.last_grasp_contact.copy()
        if not hasattr(self,'grasp_contact_points'):self.grasp_contact_points={}
    def start_substep(self):
        self.previous_grasp_force_N=self.last_grasp_force_N.copy()
        self.last_grasp_force_N={'left':0.,'right':0.}
        self.previous_grasp_contact=self.last_grasp_contact.copy()
        self.last_grasp_contact={side:bool(pairs) for side,pairs in self.active_grasp_pairs.items()}
        self.last=dict(force_N=0.,shoulder=False);self.sample_count+=1
    def callback(self,headers,data):
        force=0.;shoulder=False
        for h in headers:
            names=[str(PhysicsSchemaTools.intToSdfPath(h.collider0)),str(PhysicsSchemaTools.intToSdfPath(h.collider1))]
            grasp_side=next((side for side in ('left','right') if any(f'grasp_pad_{side}_collision' in n for n in names)),None)
            if grasp_side is not None and any('sim_module' in n for n in names):
                from omni.physx.bindings._physx import ContactEventType
                pair=tuple(sorted(names))
                if h.type==ContactEventType.CONTACT_LOST:self.active_grasp_pairs[grasp_side].discard(pair)
                elif h.type in (ContactEventType.CONTACT_FOUND,ContactEventType.CONTACT_PERSIST):
                    self.active_grasp_pairs[grasp_side].add(pair)
                self.last_grasp_contact[grasp_side]=bool(self.active_grasp_pairs[grasp_side])
            if not h.num_contact_data:continue
            self.pairs.add(tuple(names))
            for c in data[h.contact_data_offset:h.contact_data_offset+h.num_contact_data]:
                self.peak=max(self.peak,-float(c.separation)*1000)
                if any('sim_module' in n for n in names):
                    impulse=float(np.linalg.norm(c.impulse))
                    side=next((side for side in ('left','right') if any(f'grasp_pad_{side}_collision' in n for n in names)),None)
                    if side is not None:
                        self.grasp_impulse[side]+=impulse
                        self.last_grasp_force_N[side]+=impulse/self.dt
                        if hasattr(c,'position'):self.grasp_contact_points[side]=np.asarray(c.position,dtype=float).copy()
                        continue  # grip normal load is not insertion resistance
                    force+=impulse/self.dt
                    self.module_impulse+=impulse;self.module_contact=True
            shoulder |= all(any(part in n for n in names) for part in self.shoulder_pair)
        self.shoulder|=shoulder
        self.last['force_N']+=force;self.last['shoulder']|=shoulder
        self.peak_force=max(self.peak_force,self.last['force_N'])


def matrix(stage,path):
    return np.asarray(UsdGeom.Xformable(stage.GetPrimAtPath(path)).ComputeLocalToWorldTransform(Usd.TimeCode.Default())).T


class RobotExperiment:
    task_id='isaac-contact-insertion-v1'
    def __init__(self,world,packet,audit,output,dt,cameras=None,*,ik_backend='dls',tianji_sdk=None,tianji_config=None,socket_pose_range=None):
        self.world=world;self.stage=world.stage;self.packet=packet;self.audit=audit
        self.output=Path(output);self.dt=dt;self.cameras=cameras or {}
        self.manifest=packet['manifest'];self.kin=Kinematics(packet)
        self.native_ik=None
        if ik_backend=='tianji':
            if tianji_sdk is None:raise ValueError('tianji SDK directory required')
            from .tianji_ik import TianjiIK
            self.native_ik=TianjiIK(packet,tianji_sdk,tianji_config)
        elif ik_backend!='dls':raise ValueError(f'unknown IK backend: {ik_backend}')
        self.robot=TensorArticulation(world)
        self.names=self.robot.dof_names;self.arm=[self.names.index(f'Arm_L{i}_Joint') for i in range(1,8)]
        self.joints={j['name']:j for j in packet['joints']}
        self.scale=np.array([.001/np.sqrt(3)]*3+[np.pi/180/np.sqrt(3)]*3)
        self.monitor=ContactMonitor(dt,self.manifest.get('contact_shoulder_pair'));self.history=deque(maxlen=10)
        self.pads=world.tensor.create_rigid_body_view('/World/compliant_pad_*')
        self.pad_initial=self.pads.get_transforms().copy()
        self.socket_pose_range=socket_pose_range
        self._nominal_manifest=deepcopy(self.manifest)
        self._nominal_pad_initial=self.pad_initial.copy()
        if socket_pose_range:world.tensor.initialize_kinematic_bodies()
        self.socket_body=world.tensor.create_rigid_body_view(audit['body_paths']['sim_socket']) if socket_pose_range else None
        self._socket_initial=self.socket_body.get_transforms().copy() if self.socket_body else None
        self._socket_world_change=np.eye(4)
        self.phase='insert';self._finished=False;self._stable=0;self._steps=0
        self.max_steps=350
        self.goal_pos=np.array(self.manifest['goal_tcp_position']);self.goal_rot=np.array(self.manifest['goal_tcp_rotation'])
        self.contact_assessment=None
        if self.manifest.get('insertion_assessment'):
            from omi_hil_rl.hil.insertion_task import InsertionAssessment,InsertionAssessmentConfig
            self.contact_assessment=InsertionAssessment(self.manifest['shoulder_depth_mm'],InsertionAssessmentConfig(**self.manifest['insertion_assessment']))
            if abs(self.contact_assessment.config.control_dt-.1)>1e-12:
                raise ValueError('assessment period must match the 100ms control interval')
            self.task_id='isaac-entry-strict-interior-tolerant-v2'
            ids={b['name']:b['id'] for b in self.packet['bodies']}
            self.task_boxes={name:[g for g in self.packet['geoms'] if g['contact'] and g['body']==ids[name]
                                  and g.get('collision_role')!='grasp_rear'] for name in ('sim_module','sim_socket')}
            if not all(self.task_boxes.values()) or not all(g['kind']==6 for shapes in self.task_boxes.values() for g in shapes):
                raise ValueError('staged candidate geometry audit requires native boxes')
    def reset(self,seed,socket_pose=None,initial_pose=None):
        if self.socket_pose_range:
            from .socket_pose import relocate_socket_manifest
            pose=self.socket_pose_range.resolve(seed,socket_pose)
            self.manifest,self._socket_world_change=relocate_socket_manifest(self._nominal_manifest,pose)
            delta=self._socket_world_change
            def moved(poses):
                result=poses.copy();result[:,:3]=(delta[:3,:3]@poses[:,:3].T).T+delta[:3,3]
                result[:,3:]=Rotation.from_matrix(delta[:3,:3]@Rotation.from_quat(poses[:,3:]).as_matrix()).as_quat()
                return result
            socket_target=moved(self._socket_initial)
            # PhysX's USD kinematic driver re-applies the authored pose during
            # simulate(). Update that source as well as the tensor buffers.
            from .isaac_contact_scene import set_pose
            desired=self.manifest['socket_to_world']
            set_pose(self.stage.GetPrimAtPath(self.audit['body_paths']['sim_socket']),
                     transform(desired['position_m'],np.asarray(desired['rotation'])))
            self.socket_body.set_transforms(socket_target,np.array([0],np.uint32))
            self.socket_body.set_kinematic_targets(socket_target,np.array([0],np.uint32))
            self.pad_initial=moved(self._nominal_pad_initial)
        elif socket_pose is not None:
            raise ValueError('socket pose override requires a movable-socket execution contract')
        self.phase='insert';self._finished=False;self._stable=0;self._steps=0
        if self.contact_assessment:self.contact_assessment.reset()
        self.goal_pos=np.array(self.manifest['goal_tcp_position']);self.goal_rot=np.array(self.manifest['goal_tcp_rotation'])
        q=np.array([[self.packet['initial_qpos'][self.joints[n]['qpos_index']] for n in self.names]],np.float32)
        q[0,self.arm]+=np.random.default_rng(seed).uniform(-.0005,.0005,7)
        initial_audit=None
        if initial_pose is not None:
            if self.native_ik is None or self.packet.get('free_bodies'):
                raise ValueError('explicit initial pose requires native IK and fixed module attachment')
            from .initial_pose import initial_tcp_target,solve_reset_ik
            target,initial_audit=initial_tcp_target(self.manifest,self.tcp_from_gripper,initial_pose)
            qmap={j['name']:self.packet['initial_qpos'][j['qpos_index']] for j in self.packet['joints']}
            qmap.update(zip(self.names,q[0]))
            solved,ik_audit=solve_reset_ik(self.native_ik,self.kin,qmap,target)
            initial_audit['initialization_solver']=ik_audit
            for index in self.arm:q[0,index]=solved[self.names[index]]
        self.robot.set_joint_positions(q);self.robot.set_joint_velocities(np.zeros_like(q));self.robot.set_joint_position_targets(q)
        self._held_joint_targets=q.copy()
        pad_ids=np.arange(self.pads.count,dtype=np.uint32)
        self.pads.set_transforms(self.pad_initial.copy(),pad_ids)
        self.pads.set_velocities(np.zeros((self.pads.count,6),np.float32),pad_ids)
        for _ in range(3):self.world.step(render=False)
        self.world.sync()
        self.reference_right=q[0,[self.names.index(f'Arm_R{i}_Joint') for i in range(1,8)]].copy()
        self.history.clear();self.monitor.clear()
        measured=self.tcp();fk=self.kin.tcp(self.qdict())
        audit=dict(position_error_m=float(np.linalg.norm(measured[:3,3]-fk[:3,3])),
                   rotation_error_rad=float(Rotation.from_matrix(measured[:3,:3]@fk[:3,:3].T).magnitude()),
                   joint_names=self.names,initial_joint_positions=self.robot.get_joint_positions()[0].tolist())
        audit['physics_stiffnesses']=self.robot.view.get_dof_stiffnesses().tolist()
        audit['physics_dampings']=self.robot.view.get_dof_dampings().tolist()
        audit['physics_max_forces']=self.robot.view.get_dof_max_forces().tolist()
        audit['physics_joint_friction']=self.robot.view.get_dof_friction_coefficients().tolist()
        (self.output/'kinematics_check.json').write_text(json.dumps(audit,indent=2)+'\n')
        if audit['position_error_m']>1e-5 or audit['rotation_error_rad']>1e-4:
            raise RuntimeError(f'Imported kinematics mismatch: {audit}')
        if self.socket_pose_range:
            actual=matrix(self.stage,self.audit['frame_paths']['sim_socket'])
            expected=self.manifest['socket_to_world']
            native=self.socket_body.get_transforms()[0]
            native_position_error=float(np.linalg.norm(native[:3]-expected['position_m']))
            native_rotation_error=float(Rotation.from_matrix(Rotation.from_quat(native[3:]).as_matrix()@np.asarray(expected['rotation']).T).magnitude())
            if np.linalg.norm(actual[:3,3]-expected['position_m'])>1e-5 or Rotation.from_matrix(actual[:3,:3]@np.asarray(expected['rotation']).T).magnitude()>1e-4 or native_position_error>1e-5 or native_rotation_error>1e-4:
                detail=dict(expected=expected,usd=actual.tolist(),native=native.tolist())
                (self.output/'socket_pose_mismatch.json').write_text(json.dumps(detail,indent=2)+'\n')
                raise RuntimeError(f'socket collision frame does not match requested episode pose: {detail}')
            audit['socket_pose']=self.manifest['episode_socket_pose']
            audit['socket_world_position']=actual[:3,3].tolist()
            audit['socket_native_position_error_m']=native_position_error
            audit['socket_native_rotation_error_rad']=native_rotation_error
            audit['pad_position_error_m']=float(np.linalg.norm(self.pads.get_transforms()[:,:3]-self.pad_initial[:,:3],axis=1).max())
            if audit['pad_position_error_m']>1e-5:raise RuntimeError('socket pad world transforms did not follow the assembly')
            audit['pad_travel_mm']=self.measurements()['pad_travel_mm']
            if max(abs(v) for v in audit['pad_travel_mm'])>.01:raise RuntimeError('socket pad anchors did not move consistently')
            (self.output/'kinematics_check.json').write_text(json.dumps(audit,indent=2)+'\n')
        if initial_audit is not None:
            measured=self.tcp();measurement=self.measurements()
            initial_audit.update(actual_tcp=measured.tolist(),actual_gripper=(measured@self.tcp_from_gripper).tolist(),
                position_error_mm=float(np.linalg.norm(measured[:3,3]-target[:3,3])*1000),
                rotation_error_deg=float(np.rad2deg(Rotation.from_matrix(measured[:3,:3]@target[:3,:3].T).magnitude())),
                actual_tip_gap_mm=-measurement['insertion_depth_mm'],
                actual_lateral_error_mm=measurement['lateral_error_mm'],
                actual_alignment_angle_deg=float(np.rad2deg(measurement['alignment_angle_rad'])),
                initial_box_overlap_mm=measurement.get('control_box_overlap_mm',0.))
            if initial_audit['position_error_mm']>.1 or initial_audit['rotation_error_deg']>.05:
                raise RuntimeError('initial pose was not physically realized: '+str(initial_audit))
            if initial_audit['actual_tip_gap_mm']<2 or initial_audit['initial_box_overlap_mm']>1e-6:
                raise RuntimeError('initial pose intersects insertion geometry: '+str(initial_audit))
            audit['initial_pose']=initial_audit
            (self.output/'kinematics_check.json').write_text(json.dumps(audit,indent=2)+'\n')
        return audit

    def pad_rest_frame(self,body,joint):
        change=self._socket_world_change
        origin=change[:3,:3]@np.asarray(body['world_position'])+change[:3,3]
        axis=change[:3,:3]@np.asarray(body['world_rotation'])@joint['axis']
        return origin,axis
    def qdict(self):
        q={j['name']:self.packet['initial_qpos'][j['qpos_index']] for j in self.packet['joints']}
        q.update(zip(self.names,self.robot.get_joint_positions()[0]))
        return q
    def tcp(self):
        s=self.kin.sites['urdf_tcp_L'];name=self.packet['bodies'][s['body']]['name']
        return matrix(self.stage,self.audit['frame_paths'][name])@local_pose(s)
    @staticmethod
    def rotation_error(current,target):
        return .5*sum(np.cross(current[:,i],target[:,i]) for i in range(3))
    def _error(self):
        t=self.tcp();return np.r_[self.goal_pos-t[:3,3],self.rotation_error(t[:3,:3],self.goal_rot)]
    def measurements(self):
        module=matrix(self.stage,self.audit['frame_paths']['sim_module'])
        socket=matrix(self.stage,self.audit['frame_paths']['sim_socket']);local=np.linalg.inv(socket)@module
        tip=local[:3,3]+local[:3,:3]@np.array([0,self.manifest['leading_tip_y_mm']/1000,0])
        lateral=np.linalg.norm(local[[0,2],3]-np.array(self.manifest['nominal_module_center_xz_mm'])/1000)*1000
        travels=[]
        for j in self.packet['joints']:
            if not j['name'].startswith('pad_'):continue
            b=self.packet['bodies'][j['body']];t=matrix(self.stage,self.audit['body_paths'][b['name']])
            origin,axis=self.pad_rest_frame(b,j);travels.append(float((t[:3,3]-origin)@axis*1000))
        extra={}
        if self.contact_assessment:
            from .box_overlap import box_overlap_mm
            bodies={'sim_module':module,'sim_socket':socket}
            poses={name:[(g,bodies[name]@local_pose(g)) for g in self.task_boxes[name]] for name in self.task_boxes}
            overlaps=[(box_overlap_mm(a[:3,3],a[:3,:3],np.asarray(ga['size']),b[:3,3],b[:3,:3],np.asarray(gb['size'])),ga['name'],gb['name']) for ga,a in poses['sim_module'] for gb,b in poses['sim_socket']]
            worst=max(overlaps)
            extra=dict(control_box_overlap_mm=worst[0],control_box_overlap_pair=list(worst[1:]) if worst[0]>0 else [])
        return dict(insertion_depth_mm=float(self.manifest['mouth_y_mm']-tip[1]*1000),lateral_error_mm=float(lateral),
            alignment_angle_rad=float(Rotation.from_matrix(local[:3,:3]).magnitude()),pad_travel_mm=travels,
            shoulder_contact=self.monitor.last['shoulder'],step_any_shoulder_contact=self.monitor.shoulder,
            step_peak_penetration_mm=self.monitor.peak,
            contact_force_N=self.monitor.last.get('force_N',0.),step_peak_contact_force_N=self.monitor.peak_force,
            contact_force_mean_N=self.monitor.module_impulse/(max(1,self.monitor.sample_count)*self.dt),
            step_any_module_contact=self.monitor.module_contact,
            force_signal_kind='simulation_contact_impulse_norm_sum_mean',
            **extra,
            step_min_floor_gap_mm=float(np.min(np.asarray(self.manifest['pad_rest_static_gap_mm'])-travels)))
    def step(self,action):
        a=np.asarray(action,dtype=float)
        if self._finished:raise RuntimeError('episode ended')
        if a.shape!=(6,) or not np.isfinite(a).all() or np.any(abs(a)>1):raise ValueError('normalized finite 6D action required')
        t=self.tcp();target=t[:3,3]+a[:3]*self.scale[:3]
        rot=Rotation.from_rotvec(a[3:]*self.scale[3:]).as_matrix()@t[:3,:3]
        q=self.qdict();ik_started=time.perf_counter()
        if self.native_ik:
            q=self.native_ik.solve(q,transform(target,rot))
        for _ in range(0 if self.native_ik else 12):
            now=self.kin.tcp(q);err=np.r_[target-now[:3,3],self.rotation_error(now[:3,:3],rot)*.1]
            cols=[]
            for name in [f'Arm_L{i}_Joint' for i in range(1,8)]:
                dq=dict(q);dq[name]+=1e-6;other=self.kin.tcp(dq)
                cols.append(np.r_[(other[:3,3]-now[:3,3])/1e-6,self.rotation_error(now[:3,:3],other[:3,:3])*.1/1e-6])
            J=np.asarray(cols).T;update=J.T@np.linalg.solve(J@J.T+np.eye(6)*1e-5,err)
            for name,delta in zip([f'Arm_L{i}_Joint' for i in range(1,8)],update):
                q[name]=float(np.clip(q[name]+np.clip(delta,-.03,.03),*self.joints[name]['limits']))
        ik_elapsed=time.perf_counter()-ik_started
        targets=self._held_joint_targets.copy()
        for index in self.arm:targets[0,index]=q[self.names[index]]
        interpolate=self.manifest.get('joint_target_interpolation')=='linear'
        initial_targets=self.robot.get_joint_positions() if interpolate else None
        if not interpolate:self.robot.set_joint_position_targets(targets)
        self.monitor.clear();min_gap=float('inf')
        pads=[j for j in self.packet['joints'] if j['name'].startswith('pad_')]
        pad_by_path={self.audit['body_paths'][self.packet['bodies'][j['body']]['name']]:j for j in pads}
        ordered=[pad_by_path[path] for path in self.pads.prim_paths]
        rest=[self.pad_rest_frame(self.packet['bodies'][j['body']],j) for j in ordered]
        origins=np.array([x[0] for x in rest]);axes=np.array([x[1] for x in rest])
        gaps=np.array([self.manifest['pad_rest_static_gap_mm'][int(j['name'].rsplit('_',1)[1])] for j in ordered])
        substeps=round(.1/self.dt)
        for substep in range(substeps):
            if interpolate:
                command=targets.copy()
                alpha=(substep+1)/substeps
                command[0,self.arm]=initial_targets[0,self.arm]+alpha*(targets[0,self.arm]-initial_targets[0,self.arm])
                self.robot.set_joint_position_targets(command)
            self.monitor.start_substep()
            self.world.step(render=False)
            travel=np.sum((self.pads.get_transforms()[:,:3]-origins)*axes,axis=1)*1000
            min_gap=min(min_gap,float(np.min(gaps-travel)))
        self.world.sync()
        m=self.measurements();self._steps+=1
        m['step_min_floor_gap_mm']=min_gap
        if self.phase=='insert':
            settled=abs(m['insertion_depth_mm']-self.manifest['shoulder_depth_mm'])<.15 and m['lateral_error_mm']<.35 and m['alignment_angle_rad']<.01 and m['shoulder_contact']
        else:settled=m['insertion_depth_mm']< -4.8 and np.linalg.norm(self._error()[:3])<.0003
        if self.contact_assessment:
            assessment=self.contact_assessment.update(m,withdrawing=self.phase=='withdraw')
            m.update(assessment)
            self._stable=(self._stable+1 if settled else 0) if self.phase=='withdraw' else assessment['stable_samples']
            failed=assessment['failed'] or not np.isfinite(self.robot.get_joint_positions()).all()
            m.update(failed=bool(failed),is_success=bool(self._stable>=3 and not failed))
        else:
            self._stable=self._stable+1 if settled else 0
            failed=m['step_peak_penetration_mm']>.05 or m['step_min_floor_gap_mm']<.025 or not np.isfinite(self.robot.get_joint_positions()).all()
            m.update(is_success=self._stable>=3 and not failed,failed=bool(failed))
        m.update(phase=self.phase,step=self._steps,stable_samples=self._stable,joint_targets=targets[0].tolist())
        m['ik_solve_ms']=ik_elapsed*1000
        m['joint_velocities']=self.robot.view.get_dof_velocities()[0].tolist()
        self._finished=bool(m['is_success'] or failed or self._steps>=self.max_steps)
        return m
    def begin_withdrawal(self):
        if self.phase!='insert' or self._stable<3:raise RuntimeError('stable insertion required')
        self.phase='withdraw';self.goal_pos=np.asarray(self.manifest['preinsert_tcp_position'])
        self._finished=False;self._stable=0;self._steps=0
    def capture(self):
        # Render without advancing simulation time; both cameras share one state.
        before=self.robot.get_joint_positions().copy()
        self.world.render()
        np.testing.assert_allclose(self.robot.get_joint_positions(),before,atol=1e-9,rtol=0.)
        frame={}
        for name in ('head_rgb','wrist_rgb'):
            rgba=self.cameras[name].get_rgba()
            if rgba.ndim!=3 or rgba.shape[2]!=4 or rgba.shape[0]!=rgba.shape[1] or rgba.shape[0]<128 or np.ptp(rgba[:,:,:3])==0:
                np.save(self.output/f'invalid_{name}.npy',rgba)
                raise RuntimeError(f'Invalid camera {name}: shape={rgba.shape}, range={np.ptp(rgba) if rgba.size else None}')
            rgb=rgba[:,:,:3].astype(np.uint8)
            if rgb.shape[:2]!=(128,128):
                from PIL import Image
                rgb=np.asarray(Image.fromarray(rgb).resize((128,128),Image.Resampling.LANCZOS))
            frame['rgb' if name=='head_rgb' else name]=rgb.transpose(2,0,1)
        self.history.append(frame);missing=10-len(self.history)
        obs={k:np.stack([np.zeros_like(v)]*missing+[f[k] for f in self.history]) for k,v in frame.items()}
        obs.update(state=np.zeros((10,14),np.float32),tactile=np.zeros((10,10,16,24),np.float32),
            history_mask=np.array([0]*missing+[1]*len(self.history),np.uint8),
            camera_mask=np.array([[0.,0.]]*missing+[[1.,1.]]*len(self.history),np.float32))
        return obs
