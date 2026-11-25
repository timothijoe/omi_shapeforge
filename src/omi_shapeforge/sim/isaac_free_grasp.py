"""Opt-in GC-r01 PhysX grasp: module has its own dynamic body and no fixed joint."""
import json
import numpy as np
from scipy.spatial.transform import Rotation

from .isaac_contact_runtime import RobotExperiment,matrix
from .isaac_contact_kinematics import transform,free_module_servo_target,bounded_contact_spin_torque


class FreeGraspExperiment(RobotExperiment):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.grasp_config=self.manifest['grasp_contract']
        self.free_module=self.world.tensor.create_rigid_body_view(self.audit['body_paths']['sim_module'])
        if self.free_module.count!=1:raise RuntimeError('one independent dynamic module required')
        nominal=self.manifest['tool_to_module']
        self.nominal_tcp_module=transform(np.asarray(nominal['position_m']),np.asarray(nominal['rotation']))
        self.reference_tcp_module=None
        self.grasp_settled=False
        self.spin_enabled=False;self.spin_anchor=None;self.spin_torque=0.;self.spin_limit=0.
        self.spin_debug=[]
        self.grasp_command_closed=False
        self.filtered_grasp_force={'left':0.,'right':0.}
        self.patch_anchor_tcp=None;self.patch_point_module=None;self.tangent_force=np.zeros(3)
        self.previous_live_tcp=None
        tcp_id=next(b['id'] for b in self.packet['bodies'] if b['name']=='TCP_Link_L')
        owner=self.audit['owners'][tcp_id];body=self.packet['bodies'][owner]
        q={j['name']:self.packet['initial_qpos'][j['qpos_index']] for j in self.packet['joints']}
        frames=self.kin.frames(q)
        self.actor_from_tcp=np.linalg.inv(frames[owner])@frames[tcp_id]
        self.tcp_actor=self.world.tensor.create_rigid_body_view(self.audit['body_paths'][body['name']])
        self.finger_actors=[self.world.tensor.create_rigid_body_view(self.audit['body_paths'][name])
                            for name in ['Arm_L10_Link','Arm_L11_Link']]
        module_body=next(b for b in self.packet['bodies'] if b['name']=='sim_module')
        self.module_mass=module_body['mass']
        self.module_com=self.free_module.get_coms()[0,:3].copy()
        self.actor_com=self.tcp_actor.get_coms()[0,:3].copy()
        inertia_R=Rotation.from_quat(np.roll(module_body['inertia_quaternion'],-1)).as_matrix()
        self.module_inertia=inertia_R@np.diag(module_body['inertia'])@inertia_R.T
        self.world.before_step=self.apply_contact_spin
        self.task_id='isaac-wva01-gc01-free-grasp-insertion-v1'

    def set_grasp(self,closed):
        self.grasp_command_closed=closed
        for name,drive in self.grasp_config['finger_drives'].items():
            self._held_joint_targets[0,self.names.index(name)]=drive['closed_target' if closed else 'open_target']
        self.robot.set_joint_position_targets(self._held_joint_targets)

    def reset(self,seed,socket_pose=None):
        self.grasp_settled=False
        self.spin_enabled=False;self.spin_anchor=None
        self.spin_debug=[]
        self.filtered_grasp_force={'left':0.,'right':0.}
        self.reference_tcp_module=None
        self.patch_anchor_tcp=None;self.patch_point_module=None
        self.previous_live_tcp=None
        self.monitor.active_grasp_pairs={'left':set(),'right':set()}
        self.monitor.grasp_contact_points={}
        result=super().reset(seed,socket_pose)
        pose=self.tcp()@self.nominal_tcp_module
        native=np.r_[pose[:3,3],Rotation.from_matrix(pose[:3,:3]).as_quat()].astype(np.float32)[None]
        self.free_module.set_transforms(native,np.array([0],np.uint32))
        self.free_module.set_velocities(np.zeros((1,6),np.float32),np.array([0],np.uint32))
        self.set_grasp(True)
        self.spin_enabled=bool(self.grasp_config.get('spin_contact_model'))
        material_diagnostic={}
        for name,view in [('module',self.free_module),('robot',self.robot.view)]:
            if hasattr(view,'get_material_properties'):
                material_diagnostic[name]=view.get_material_properties().tolist()
        (self.output/'grasp_native_materials.json').write_text(json.dumps(material_diagnostic,indent=2))
        self.monitor.clear()
        diagnostic=[]
        for _ in range(round(self.grasp_config['settle_seconds']/self.dt)):
            self.monitor.start_substep();self.world.step()
            if _%50==0:
                self.world.sync()
                diagnostic.append(dict(step=_,q=self.robot.get_joint_positions()[0].tolist(),
                    module=self.free_module.get_transforms().tolist(),pairs=sorted(self.monitor.pairs),
                    grasp_impulse=self.monitor.grasp_impulse.copy()))
        self.world.sync()
        self.reference_tcp_module=np.linalg.inv(self.tcp())@matrix(self.stage,self.audit['frame_paths']['sim_module'])
        self.grasp_settled=True
        state=self.measurements()
        (self.output/'grasp_reset.json').write_text(json.dumps(state,indent=2))
        (self.output/'grasp_reset_diagnostic.json').write_text(json.dumps(diagnostic,indent=2))
        (self.output/'grasp_spin_diagnostic.json').write_text(json.dumps(self.spin_debug,indent=2))
        if not state['grasp_held']:raise RuntimeError(f'free grasp failed to settle: {state}')
        return dict(result,free_grasp=state)

    def apply_contact_spin(self):
        self.spin_torque=0.;self.spin_limit=0.
        self.tangent_force=np.zeros(3)
        def clear_wrench():
            zero=np.zeros((1,3),np.float32);indices=np.array([0],np.uint32)
            for view in [self.free_module,*self.finger_actors]:
                view.apply_forces_and_torques_at_position(zero,zero,None,indices,True)
        if not self.spin_enabled or not self.grasp_command_closed:
            self.spin_anchor=None;self.patch_anchor_tcp=None;self.previous_live_tcp=None
            clear_wrench();return
        alpha=min(1.,self.dt/self.grasp_config.get('spin_normal_filter_s',.005))
        for side in self.filtered_grasp_force:
            self.filtered_grasp_force[side]+=(self.monitor.previous_grasp_force_N[side]-self.filtered_grasp_force[side])*alpha
        forces=self.filtered_grasp_force
        if min(forces.values())<.1:
            self.spin_anchor=None
            self.patch_anchor_tcp=None
            self.previous_live_tcp=None
            clear_wrench();return
        if not all(self.monitor.previous_grasp_contact.values()):
            # Keep finite rubber-patch deformation across substep contact churn,
            # but apply NO wrench in the gap. Open jaws / decayed normal load
            # discard the anchors above; this is not a long-range attachment.
            self.previous_live_tcp=None
            clear_wrench();return
        module_pose=self.free_module.get_transforms()[0]
        module_R=Rotation.from_quat(module_pose[3:]).as_matrix()
        # Use independently checked joint-state FK for the contact target.
        live_tcp=self.kin.tcp(self.qdict())
        tcp_R=live_tcp[:3,:3];tcp_position=live_tcp[:3,3]
        tcp_omega=np.zeros(3)
        if self.previous_live_tcp is not None:
            tcp_omega=Rotation.from_matrix(tcp_R@self.previous_live_tcp[:3,:3].T).as_rotvec()/self.dt
        if self.spin_anchor is None:self.spin_anchor=tcp_R.T@module_R
        axis=tcp_R[:,1]
        angle=float(Rotation.from_matrix(module_R@(tcp_R@self.spin_anchor).T).as_rotvec()@axis)
        speed=float((self.free_module.get_velocities()[0,3:]-tcp_omega)@axis)
        inertia=float(axis@(module_R@self.module_inertia@module_R.T)@axis)
        torque,limit=bounded_contact_spin_torque(angle,speed,inertia,forces['left'],forces['right'],
                    self.grasp_config['torsional_patch_radius_m'],self.grasp_config['spin_time_constant_s'])
        tangent_force=np.zeros(3)
        point=module_pose[:3].copy()
        if self.grasp_config.get('sliding_friction_coefficient'):
            if self.patch_anchor_tcp is None:
                if not all(side in self.monitor.grasp_contact_points for side in ('left','right')):return
                center=(self.monitor.grasp_contact_points['left']+self.monitor.grasp_contact_points['right'])*.5
                self.patch_anchor_tcp=tcp_R.T@(center-tcp_position)
                self.patch_point_module=module_R.T@(center-module_pose[:3])
            point=module_pose[:3]+module_R@self.patch_point_module
            target=tcp_position+tcp_R@self.patch_anchor_tcp
            error=point-target;error-=axis*float(error@axis)
            vm=self.free_module.get_velocities()[0]
            module_com_world=module_pose[:3]+module_R@self.module_com
            target_velocity=np.zeros(3)
            if self.previous_live_tcp is not None:
                previous_target=self.previous_live_tcp[:3,3]+self.previous_live_tcp[:3,:3]@self.patch_anchor_tcp
                target_velocity=(target-previous_target)/self.dt
            relative=vm[:3]+np.cross(vm[3:],point-module_com_world)-target_velocity
            relative-=axis*float(relative@axis)
            mass=self.module_mass
            tc=self.grasp_config['tangential_time_constant_s']
            tangent_force=-mass/(tc*tc)*error-2*mass/tc*relative
            force_limit=self.grasp_config['sliding_friction_coefficient']*(forces['left']+forces['right'])
            demand=float(np.linalg.norm(tangent_force))/max(force_limit,1e-12)
            if demand>1:
                tangent_force/=demand
                # Finite plastic slip at the cone; no hard position constraint.
                wanted_error=(-tangent_force-2*mass/tc*relative)/(mass/(tc*tc))
                self.patch_anchor_tcp+=tcp_R.T@(error-wanted_error)
            ellipsoid=np.sqrt((np.linalg.norm(tangent_force)/max(force_limit,1e-12))**2+(torque/max(limit,1e-12))**2)
            if ellipsoid>1:tangent_force/=ellipsoid;torque/=ellipsoid
        value=(axis*torque).astype(np.float32)[None]
        force=tangent_force.astype(np.float32)[None]
        at=point.astype(np.float32)[None]
        indices=np.array([0],np.uint32)
        self.free_module.apply_forces_and_torques_at_position(force,value,at,indices,True)
        for side,finger in zip(('left','right'),self.finger_actors):
            weight=forces[side]/(forces['left']+forces['right'])
            finger.apply_forces_and_torques_at_position(-force*weight,-value*weight,at,indices,True)
        self.tangent_force=tangent_force
        self.previous_live_tcp=live_tcp.copy()
        self.spin_torque=torque;self.spin_limit=limit
        if len(self.spin_debug)<350:
            self.spin_debug.append(dict(angle=angle,speed=speed,torque=torque,limit=limit,inertia=inertia,
                                        force_left=forces['left'],force_right=forces['right']))

    def goal_error(self,goal_pos=None,goal_rot=None):
        tcp=self.tcp()
        module=matrix(self.stage,self.audit['frame_paths']['sim_module'])
        desired_tcp=transform(np.asarray(self.goal_pos if goal_pos is None else goal_pos),
                              np.asarray(self.goal_rot if goal_rot is None else goal_rot))
        corrected=free_module_servo_target(tcp,module,desired_tcp,self.nominal_tcp_module)
        return np.r_[corrected[:3,3]-tcp[:3,3],self.rotation_error(tcp[:3,:3],corrected[:3,:3])]

    def _error(self):
        return self.goal_error()

    def measurements(self):
        state=super().measurements()
        module=matrix(self.stage,self.audit['frame_paths']['sim_module'])
        socket=matrix(self.stage,self.audit['frame_paths']['sim_socket'])
        actual=np.linalg.inv(self.tcp())@module
        rigid=self.tcp_actor.get_transforms()[0]
        rigid_tcp=transform(rigid[:3],Rotation.from_quat(rigid[3:]).as_matrix())@self.actor_from_tcp
        fk_frames=self.kin.frames(self.qdict())
        finger_errors={}
        for name,view in zip(('Arm_L10_Link','Arm_L11_Link'),self.finger_actors):
            bid=next(b['id'] for b in self.packet['bodies'] if b['name']==name)
            native=view.get_transforms()[0]
            finger_errors[name]=float(np.linalg.norm(native[:3]-fk_frames[bid][:3,3])*1000)
        reference=self.reference_tcp_module
        slip=float(np.linalg.norm(actual[:3,3]-reference[:3,3])*1000) if reference is not None else 0.
        angle=float(np.rad2deg(Rotation.from_matrix(actual[:3,:3]@reference[:3,:3].T).magnitude())) if reference is not None else 0.
        duration=max(1,self.monitor.sample_count)*self.dt
        forces={side:value/duration for side,value in self.monitor.grasp_impulse.items()}
        held=all(value>=self.grasp_config['minimum_side_force_N'] for value in forces.values())
        held&=slip<=self.grasp_config['maximum_slip_mm'] and angle<=self.grasp_config['maximum_rotation_deg']
        state.update(world_from_module=module.tolist(),world_from_socket=socket.tolist(),
                     tcp_from_module=actual.tolist(),grasp_force_proxy_N=forces,grasp_held=bool(held),
                     grasp_relative_slip_mm=slip,grasp_relative_angle_deg=angle,
                     grasp_spin_torque_Nm=self.spin_torque,grasp_spin_limit_Nm=self.spin_limit,
                     grasp_spin_model=self.grasp_config.get('spin_contact_model','native'),
                     grasp_tangent_force_N=self.tangent_force.tolist(),
                     grasp_rigid_view_tcp_delta_mm=float(np.linalg.norm(rigid_tcp[:3,3]-self.tcp()[:3,3])*1000),
                     grasp_finger_fk_error_mm=finger_errors,
                     grasp_force_kind='per-side contact impulse norm / control interval; excluded from insertion force')
        return state

    def step(self,action):
        state=super().step(action)
        if self.grasp_settled and not state['grasp_held']:
            state.update(failed=True,is_success=False,failure_reason='physical_grasp_lost')
            self._finished=True
        return state
