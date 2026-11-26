"""Isaac process for rule-feedback RL; real PhysX and real RGB observations."""
import argparse,hashlib,json,os,shutil,socket,sys,traceback
from pathlib import Path

def resolve_physics_dt(dt=None,substeps=None):
    if dt is not None and substeps is not None:raise ValueError('choose physics dt or substeps, not both')
    if substeps is not None:
        if type(substeps) is not int or substeps not in (5,20,100,500):raise ValueError('supported substeps: 5, 20, 100, 500')
        dt=.1/substeps
    dt=.0002 if dt is None else float(dt)
    if not 0<dt<=.02 or abs(round(.1/dt)*dt-.1)>1e-9:raise ValueError('physics dt must divide 0.1 s and be at most 20 ms')
    return dt

def validate_physics_backend(device,gpu_enabled,broadphase,statistics):
    """Check scene-local native solver evidence, not GPU usage from rendering."""
    if device not in ('cpu','gpu'):raise ValueError('unknown physics device')
    if gpu_enabled != (device=='gpu') or broadphase != ('GPU' if device=='gpu' else 'MBP'):
        raise RuntimeError('physics scene does not match requested backend')
    solver=statistics.get('gpu_mem_heap_solver',0)
    articulation=statistics.get('gpu_mem_heap_simulation_articulation',0)
    if device=='gpu' and (solver<=0 or articulation<=0):
        raise RuntimeError('GPU requested but native GPU solver/articulation statistics are absent')
    if device=='cpu' and (solver>0 or articulation>0):
        raise RuntimeError('CPU requested but native GPU solver/articulation is active')

def validate_asset_contract(packet,requested):
    manifest=packet['manifest']
    tool=manifest.get('wrist_tool_asset')
    module=(manifest.get('module_visual_asset') or {}).get('asset_id')
    if requested=='legacy-r10':
        if tool!='WG-DAIMON-OBS-r10' or module!='OM-001/V4 r08' or packet.get('free_bodies'):
            raise ValueError('legacy contract requires pinned r10/r08 and its fixed module topology')
    elif requested=='wva01-gc01-free-grasp-v1':
        if (manifest.get('asset_contract')!=requested or tool!='WG-DAIMON-LOGO-r15' or
            module!='OM-001/V4 r08' or packet.get('free_bodies')!=['sim_module'] or
            manifest.get('grasp_contract',{}).get('version')!='isaac-gc01-free-module-v1'):
            raise ValueError('updated contract requires r15/r08, GC-r01 pads and free module topology')
    elif requested=='wva01-closed-reference-fixture-v1':
        if (tool!='WG-DAIMON-LOGO-r15' or module!='OM-001/V4 r08' or packet.get('free_bodies') or
            manifest.get('asset_contract')!=requested or manifest.get('grasp_reference',{}).get('scope')!='closed pose reference only'):
            raise ValueError('visual fixture requires r15/r08, closed reference and explicit fixed topology')
    else:raise ValueError('unknown asset execution contract')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--transfer',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--socket',type=Path,required=True);p.add_argument('--max-steps',type=int,default=350);p.add_argument('--no-render',action='store_true')
    p.add_argument('--physics-dt',type=float)
    p.add_argument('--physics-substeps',type=int,choices=[5,20,100,500])
    p.add_argument('--physics-device',choices=['cpu','gpu'],default='cpu',help='PhysX dynamics device; current control interface retains CPU readback')
    p.add_argument('--solver',choices=['PGS','TGS'],default='PGS')
    p.add_argument('--ik-backend',choices=['dls','tianji'],default='dls')
    p.add_argument('--tianji-sdk',type=Path,help='Offline Arm_control directory containing fx_kine.py and libKine.so')
    p.add_argument('--tianji-config',type=Path,help='Defaults to SDK ccs_m6_40.MvKDCfg')
    p.add_argument('--keep-preview-viewport',action='store_true',help='Preserve legacy headless preview rendering and execution contract')
    p.add_argument('--render-subframes',type=int,choices=[1,2],default=2,help='RTX subframes per observation; 1 changes image convergence and execution contract')
    p.add_argument('--socket-pose-range-mm',type=float,default=0.,help='Per-axis XY socket reset range; enables movable kinematic socket assembly')
    p.add_argument('--socket-yaw-range-deg',type=float,default=0.,help='Socket reset yaw range about world Z')
    p.add_argument('--initial-pose-reset',action='store_true',help='Opt-in explicit fixed-grasp evaluation start poses; task and policy schema unchanged')
    p.add_argument('--teacher-min-step-mm',type=float,default=.01)
    p.add_argument('--target-overtravel-mm',type=float,default=.03)
    p.add_argument('--entry-guidance',action='store_true',help='Hold strict entry and recover missed qualification; new execution contract')
    p.add_argument('--wrist-wrench',action='store_true',help='Opt-in ideal compensated module-contact wrench observation; legacy default off')
    p.add_argument('--wrist-offset-m',type=float,nargs=3,default=[0.,0.,0.],help='Virtual sensor origin in TCP frame; axes follow TCP')
    p.add_argument('--asset-contract',choices=['legacy-r10','wva01-gc01-free-grasp-v1','wva01-closed-reference-fixture-v1'],default='legacy-r10')
    a=p.parse_args()
    if a.ik_backend=='tianji' and a.tianji_sdk is None:p.error('--tianji-sdk required for native IK')
    if a.initial_pose_reset and (a.ik_backend!='tianji' or a.asset_contract!='legacy-r10'):
        p.error('initial pose reset currently requires native IK and legacy fixed-grasp assets')
    if a.ik_backend=='dls' and (a.tianji_sdk is not None or a.tianji_config is not None):p.error('SDK options require --ik-backend tianji')
    if a.asset_contract=='wva01-gc01-free-grasp-v1' and a.solver!='TGS':p.error('free-grasp torsional friction requires explicit --solver TGS')
    try:a.physics_dt=resolve_physics_dt(a.physics_dt,a.physics_substeps)
    except ValueError as exc:p.error(str(exc))
    if not 0<a.teacher_min_step_mm<=.1 or not 0<=a.target_overtravel_mm<=.2:p.error('invalid approach settings')
    a.output.mkdir(parents=True,exist_ok=False)
    for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
    repo=Path(__file__).resolve().parents[2];sys.path[:0]=['/data/omi_runtime/envs/isaac_contact_support',str(repo/'src')]
    snapshot=a.output/'code_snapshot';snapshot.mkdir()
    common_root=repo.parent/'omi_proj/src';sys.path.insert(0,str(common_root))
    for f in [Path(__file__),common_root/'omi_hil_rl/hil/insertion_task.py',*[repo/'src/omi_shapeforge/sim'/n for n in ['isaac_contact_scene.py','isaac_contact_runtime.py','isaac_free_grasp.py','isaac_contact_kinematics.py','tianji_ik.py','socket_pose.py','isaac_appearance.py','isaac_contact_approach.py','contact_teacher.py','isaac_recovery.py','wrist_fisheye.py','isaac_ipc.py','box_overlap.py']]]:shutil.copy2(f,snapshot/f.name)
    if a.wrist_wrench:
        shutil.copy2(repo/'src/omi_shapeforge/sim/wrist_wrench.py',snapshot/'wrist_wrench.py')
    if a.initial_pose_reset:
        shutil.copy2(repo/'src/omi_shapeforge/sim/initial_pose.py',snapshot/'initial_pose.py')
    (a.output/'execution.json').write_text(json.dumps(dict(arguments={k:str(v) if isinstance(v,Path) else v for k,v in vars(a).items()},
        sources_sha256={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in snapshot.iterdir()}),indent=2)+'\n')
    import omi_hil_rl.hil
    omi_hil_rl.hil.__path__=[str(snapshot)]
    import omi_shapeforge.sim
    omi_shapeforge.sim.__path__=[str(snapshot)]
    root=Path('/data/isaac-sim-5.1.0');sys.argv=[sys.argv[0]]
    from isaacsim import SimulationApp
    extra=['--/app/extensions/registryEnabled=false']
    for f in ('exts','extscache','kit/exts','kit/extscore'):extra+=['--ext-folder',str(root/f)]
    if a.no_render:
        for ext in ('omni.physx','omni.usd','omni.kit.loop','omni.kit.usd.layers','omni.kit.usd.mdl','omni.physx.tensors'):extra+=['--enable',ext]
    app=SimulationApp(dict(headless=True,limit_cpu_threads=4,multi_gpu=False,extra_args=extra),experience=None if a.no_render else str(root/'apps/isaacsim.exp.base.python.kit'))
    failed=False;server=None;bound_socket=False
    try:
        from collections import deque
        import numpy as np
        from PIL import Image
        import omni.usd
        from pxr import Gf,UsdPhysics,PhysxSchema
        from omi_shapeforge.sim.isaac_contact_scene import build
        from omi_shapeforge.sim.isaac_contact_runtime import DirectWorld,RobotExperiment
        from omi_shapeforge.sim.socket_pose import SocketPoseRange
        from omi_shapeforge.sim.isaac_appearance import apply_recipe
        from omi_shapeforge.sim.isaac_contact_approach import limit_approach
        from omi_shapeforge.sim.contact_teacher import ContactInsertionTeacher
        from omi_shapeforge.sim.isaac_recovery import StagedRecoveryTeacher,RecoveryConfig
        from dataclasses import asdict
        from omi_shapeforge.sim.wrist_fisheye import inverse_theta
        from omi_shapeforge.sim.isaac_ipc import send,receive
        context=omni.usd.get_context();context.new_stage();world=DirectWorld(context.get_stage(),app,a.physics_dt,render_subframes=a.render_subframes)
        physics=UsdPhysics.Scene.Define(world.stage,'/World/PhysicsScene');physics.CreateGravityDirectionAttr(Gf.Vec3f(0,0,-1));physics.CreateGravityMagnitudeAttr(9.81)
        settings=PhysxSchema.PhysxSceneAPI.Apply(physics.GetPrim());settings.CreateEnableGPUDynamicsAttr(a.physics_device=='gpu');settings.CreateBroadphaseTypeAttr('GPU' if a.physics_device=='gpu' else 'MBP');settings.CreateSolverTypeAttr(a.solver);settings.CreateTimeStepsPerSecondAttr(round(1/a.physics_dt));settings.CreateEnableStabilizationAttr(False)
        pose_range=SocketPoseRange(a.socket_pose_range_mm,a.socket_yaw_range_deg)
        pose_range=pose_range if a.socket_pose_range_mm or a.socket_yaw_range_deg else None
        packet,audit=build(world.stage,a.transfer,a.output,contact_offset=1e-7,movable_socket=pose_range is not None)
        validate_asset_contract(packet,a.asset_contract)
        apply_recipe(world.stage,packet,audit,a.transfer,'refined');world.reset()
        from omni.physx import get_physx_statistics_interface
        from omni.physx.bindings._physx import PhysicsSceneStats
        from pxr import PhysicsSchemaTools
        native_stats=PhysicsSceneStats()
        if not get_physx_statistics_interface().get_physx_scene_statistics(world.stage_id,PhysicsSchemaTools.sdfPathToInt('/World/PhysicsScene'),native_stats):
            raise RuntimeError('native physics statistics unavailable')
        statistics={n:getattr(native_stats,n) for n in ('gpu_mem_heap_solver','gpu_mem_heap_simulation_articulation',
            'gpu_mem_heap_broadphase','gpu_mem_heap_narrowphase','nb_articulations','nb_dynamic_rigids','nb_box_shapes','nb_cylinder_shapes')}
        validate_physics_backend(a.physics_device,settings.GetEnableGPUDynamicsAttr().Get(),settings.GetBroadphaseTypeAttr().Get(),statistics)
        physics_backend=dict(requested_device=a.physics_device,gpu_dynamics=settings.GetEnableGPUDynamicsAttr().Get(),
            broadphase=settings.GetBroadphaseTypeAttr().Get(),tensor_frontend='numpy',tensor_device=str(world.tensor.device),
            tensor_device_ordinal=world.tensor.device_ordinal,statistics=statistics,
            data_path='host readback; per-substep CPU control and contact reports; not an end-to-end GPU tensor pipeline')
        (a.output/'physics_backend.json').write_text(json.dumps(physics_backend,indent=2)+'\n')
        Experiment=RobotExperiment
        if a.asset_contract=='wva01-gc01-free-grasp-v1':
            from omi_shapeforge.sim.isaac_free_grasp import FreeGraspExperiment
            Experiment=FreeGraspExperiment
        env=Experiment(world,packet,audit,a.output,a.physics_dt,ik_backend=a.ik_backend,
            tianji_sdk=a.tianji_sdk,tianji_config=a.tianji_config,socket_pose_range=pose_range);env.max_steps=a.max_steps
        if a.initial_pose_reset:
            from omi_shapeforge.sim.initial_pose import gripper_center_from_mesh
            with np.load(a.transfer/'meshes.npz',allow_pickle=False) as meshes:
                env.tcp_from_gripper=gripper_center_from_mesh(packet,meshes)
        wrench_contract=None
        if a.wrist_wrench:
            from omi_shapeforge.sim.wrist_wrench import attach_wrist_wrench
            wrench_contract=attach_wrist_wrench(env,a.wrist_offset_m)
        axis=-np.asarray(env.manifest['socket_to_world']['rotation'])[:,1]
        projection=packet['manifest']['observation_projection'];K=np.asarray(projection['K']);D=np.asarray(projection['D'])
        # Exact legacy real-data ROI coordinates; each output sample stays in the
        # original 1920x1080 fisheye pixel domain. This ROI fits wholly in cube 0.
        select=np.rint(np.linspace(0,388,128));x,y=np.meshgrid(766+select,566+select)
        xn=(x-K[0,2])/K[0,0];yn=(y-K[1,2])/K[1,1];rd=np.hypot(xn,yn);theta=inverse_theta(rd,D)
        factor=np.sin(theta)/np.maximum(rd,1e-12);directions=np.stack([xn*factor,yn*factor,np.cos(theta)],-1)
        assert np.all(directions[:,:,2]>np.max(np.abs(directions[:,:,:2]),axis=2)),'ROI needs multiple cube faces'
        N=512;u=(N-1)/2+N/2*directions[:,:,0]/directions[:,:,2];v=(N-1)/2+N/2*directions[:,:,1]/directions[:,:,2]
        ix=np.floor(u).astype(int);iy=np.floor(v).astype(int);wx=(u-ix)[...,None];wy=(v-iy)[...,None]
        assert ix.min()>=0 and iy.min()>=0 and ix.max()<N-1 and iy.max()<N-1
        cameras={};products=[];viewport_audit=None
        if not a.no_render:
            import omni.replicator.core as rep
            rep.settings.set_render_rtx_realtime(antialiasing='DLAA')
            for name,size in [('head_rgb',256),('wrist_rgb',N)]:
                product=rep.create.render_product(audit['cameras'][name],(size,size));products.append(product)
                ann=rep.AnnotatorRegistry.get_annotator('rgb');ann.attach(product);cameras[name]=ann
            for _ in range(3):world.render()
            # Headless Kit still owns a default 1280x720 preview. Only the two
            # explicit render products above feed observations. Disable that
            # unused view AFTER stage/camera initialization: disabling it in
            # SimulationApp's startup config can stall scene initialization.
            from omni.kit.viewport.utility import get_active_viewport
            viewport=get_active_viewport()
            if viewport:
                if not a.keep_preview_viewport:
                    viewport.updates_enabled=False
                    if viewport.updates_enabled:raise RuntimeError('unused preview viewport still updating')
                viewport_audit=dict(resolution=list(viewport.resolution),updates_enabled=bool(viewport.updates_enabled))
        history=deque(maxlen=10);teacher=ContactInsertionTeacher();episode=0;step=0;finished=True;teacher_requests=0
        if a.entry_guidance and not env.contact_assessment:raise ValueError('entry guidance requires staged assessment')
        recovery=StagedRecoveryTeacher(RecoveryConfig(strict_entry=True)) if a.entry_guidance else StagedRecoveryTeacher() if env.contact_assessment else None
        last_measurement={}
        def capture():
            if a.no_render:return {}
            before=env.robot.get_joint_positions().copy();velocity=env.robot.view.get_dof_velocities().copy()
            world.render()
            np.testing.assert_allclose(env.robot.get_joint_positions(),before,atol=1e-9,rtol=0)
            np.testing.assert_allclose(env.robot.view.get_dof_velocities(),velocity,atol=1e-9,rtol=0)
            head=cameras['head_rgb'].get_data()[:,:,:3];front=cameras['wrist_rgb'].get_data()[:,:,:3]
            wrist=np.rint(front[iy,ix]*(1-wx)*(1-wy)+front[iy,ix+1]*wx*(1-wy)+front[iy+1,ix]*(1-wx)*wy+front[iy+1,ix+1]*wx*wy).clip(0,255).astype(np.uint8)
            head=np.asarray(Image.fromarray(head).resize((128,128),Image.Resampling.LANCZOS))
            assert head.std()>1 and wrist.std()>1
            history.append(dict(rgb=head.transpose(2,0,1),wrist_rgb=wrist.transpose(2,0,1)))
            missing=10-len(history);result={k:np.stack([np.zeros_like(z)]*missing+[h[k] for h in history]) for k,z in history[-1].items()}
            result.update(state=np.zeros((10,14),np.float32),tactile=np.zeros((10,10,16,24),np.float32),
                camera_mask=np.array([[0.,0.]]*missing+[[1.,1.]]*len(history),np.float32),history_mask=np.array([0]*missing+[1]*len(history),np.uint8))
            return result
        def potential(measurement):
            # Both inputs are already measured at this exact physics state.
            # Rendering is checked above not to move q/dq. Re-running the full
            # contact SAT audit here twice per control step changes no evidence.
            return -10*float(np.linalg.norm(env.goal_pos-np.asarray(measurement['tcp_position'])))-.5*measurement['alignment_angle_rad']
        def info():
            return dict(env.measurements(),simulation_time_ns=1+step*100_000_000,episode=episode,step=step,
                is_success=False,terminated=False,truncated=False,task=env.task_id)
        meta=dict(transfer=str(a.transfer.resolve()),transfer_sha256=hashlib.sha256((a.transfer/'transfer.json').read_bytes()).hexdigest(),
            rendered=not a.no_render,physics_dt=a.physics_dt,control_dt=.1,projection=projection,wrist_roi=[766,566,1155,955],
            render_runtime=dict(rt_subframes=a.render_subframes,unused_preview_viewport=viewport_audit),
            physics_backend=physics_backend,
            wrist_sampling='rint(linspace(0,388,128)); fisheye rays sampled from 512px 90deg front cube',
            current_assets=[packet['manifest']['wrist_tool_asset'],'OM-001/V4 r08'],policy_inputs='two RGB histories and validity masks; state/tactile zero padding',
            execution_config=dict(max_steps=a.max_steps,physics_dt=a.physics_dt,control_dt=.1,
                teacher_min_step_mm=a.teacher_min_step_mm,target_overtravel_mm=a.target_overtravel_mm,
                joint_target_interpolation=env.manifest.get('joint_target_interpolation','none'),
                global_contact_offset_m=1e-7,per_collider_contact_offsets_m=audit.get('per_collider_contact_offsets_m',{}),
                force_stop_N=None if env.contact_assessment else 10.,
                penetration_stop_mm=None if env.contact_assessment else .05,solver=a.solver,
                insertion_assessment=env.manifest.get('insertion_assessment')))
        if wrench_contract:
            meta['execution_config']['wrist_wrench']=wrench_contract
        if env.native_ik:
            meta['action_contract']='isaac-world-tcp-normalized-delta-tianji-servo-v1'
            meta['execution_config']['ik_backend']=env.native_ik.metadata
        if a.asset_contract!='legacy-r10':
            meta['execution_config']['asset_contract']=a.asset_contract
        if a.asset_contract=='wva01-gc01-free-grasp-v1':
            meta['execution_config']['grasp_contract']=env.grasp_config
            meta['current_assets'].append('GC-r01 PhysX free-grasp port')
        elif a.asset_contract=='wva01-closed-reference-fixture-v1':
            meta['execution_config']['grasp_reference']=packet['manifest']['grasp_reference']
        if pose_range:meta['execution_config']['socket_pose_randomization']=pose_range.contract()
        if a.physics_device=='gpu':
            meta['execution_config']['physics_backend']=dict(version='physx-gpu-host-readback-v1',dynamics='gpu',broadphase='GPU',tensor_frontend='numpy')
        if not a.no_render and not a.keep_preview_viewport:
            # Removing an unused view still changes renderer scheduling/history.
            # Give new recordings an explicit recipe; do not relabel old RGB.
            meta['execution_config']['render_runtime']=dict(version='headless-sensors-only-v1',rt_subframes=a.render_subframes)
        elif not a.no_render and a.render_subframes!=2:
            meta['execution_config']['render_runtime']=dict(version='legacy-preview-subframes-v1',rt_subframes=a.render_subframes)
        if not env.contact_assessment:meta['execution_config'].pop('insertion_assessment')
        else:
            recovery_config=asdict(recovery.config)
            if not a.entry_guidance:recovery_config.pop('strict_entry')
            meta['execution_config']['recovery_controller']=recovery_config
        if a.entry_guidance:
            meta['execution_config']['entry_guidance']=dict(version='qualified-entry-hold-v1',
                lateral_takeover_mm=.10,angle_takeover_rad=.0015,handback_requires_entry=True)
        if a.initial_pose_reset:
            meta['reset_capabilities']={'initial_pose':'gripper-centered-gap-offset-yaw-pitch-v1',
                'scope':'explicit reset-distribution shift; runtime task, reward, observations and actions unchanged'}
        (a.output/'worker_metadata.json').write_text(json.dumps(meta,indent=2)+'\n')
        if a.socket.exists():raise FileExistsError(a.socket)
        server=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);server.bind(str(a.socket));bound_socket=True;os.chmod(a.socket,0o600);server.listen(1)
        print('WORKER_READY',str(a.socket),flush=True)
        shutdown=False
        while not shutdown:
            connection,_=server.accept();connection.settimeout(1800)
            with connection:
                while True:
                    try:request,arrays=receive(connection)
                    except EOFError:break
                    command=request.get('command')
                    try:
                        if command=='hello':send(connection,dict(ok=True,metadata=meta));continue
                        if command=='shutdown':send(connection,dict(ok=True));shutdown=True;break
                        if command=='reset':
                            requested_initial=request.get('initial_pose')
                            if requested_initial is not None and not a.initial_pose_reset:
                                raise ValueError('initial pose reset not enabled')
                            episode+=1;step=0;teacher_requests=0;history.clear();teacher.reset()
                            reset_audit=env.reset(int(request['seed']),request.get('socket_pose'),initial_pose=requested_initial) if requested_initial is not None else env.reset(int(request['seed']),request.get('socket_pose'))
                            if recovery:recovery.reset()
                            axis=-np.asarray(env.manifest['socket_to_world']['rotation'])[:,1]
                            env.goal_pos=np.asarray(env.manifest['seated_tcp_position'])+axis*(a.target_overtravel_mm/1000)
                            finished=False;obs=capture();state=info()
                            if recovery:state.update(recovery.status())
                            state['task_goal_position']=env.goal_pos.tolist()
                            state['tcp_position']=env.tcp()[:3,3].tolist()
                            state['tcp_rotation']=env.tcp()[:3,:3].tolist()
                            if pose_range:
                                state['socket_pose']=env.manifest['episode_socket_pose']
                                state['socket_to_world']=env.manifest['socket_to_world']
                                state['preinsert_tcp_position']=env.manifest['preinsert_tcp_position']
                            state['initial_pose']=reset_audit.get('initial_pose')
                            state['joint_positions']=env.robot.get_joint_positions()[0].tolist()
                            with (a.output/'reset_audit.jsonl').open('a') as stream:
                                stream.write(json.dumps(dict(seed=int(request['seed']),**state))+'\n')
                            last_measurement=state
                            send(connection,dict(ok=True,info=state),obs);continue
                        if command=='grasp':
                            if a.asset_contract!='wva01-gc01-free-grasp-v1':raise ValueError('grasp control requires explicit free-grasp asset contract')
                            env.set_grasp(bool(request['closed']))
                            send(connection,dict(ok=True));continue
                        if finished:raise RuntimeError('reset required before stepping')
                        if command=='teacher':
                            teacher_requests+=1
                            if recovery:
                                action,detail=recovery.act(env,last_measurement,minimum_mm=a.teacher_min_step_mm)
                            else:
                                action,detail=teacher.act(env);action,limit=limit_approach(action,env.scale,axis,env.manifest['shoulder_depth_mm']-env.measurements()['insertion_depth_mm'],env.phase,minimum_mm=a.teacher_min_step_mm)
                                detail['approach']=limit
                            send(connection,dict(ok=True,action=action.tolist(),audit=detail));continue
                        if command!='step':raise ValueError('unknown command')
                        before=potential(last_measurement);action=np.asarray(request['action'],np.float32);m=env.step(action);step+=1
                        if recovery:
                            recovery.observe(env,m,executed_action=action)
                            m.update(recovery.status())
                            if recovery.failure and not m['failed']:
                                m.update(failed=True,is_success=False,failure_reason=recovery.failure)
                        force_abort=not env.contact_assessment and m['contact_force_N']>10.;terminated=bool(m['failed'] or force_abort or m['is_success']);success=bool(m['is_success'] and not m['failed'] and not force_abort)
                        truncated=bool(step>=a.max_steps and not terminated);finished=terminated or truncated;env._finished=finished
                        tcp=env.tcp()
                        m['tcp_position']=tcp[:3,3].tolist();m['tcp_rotation']=tcp[:3,:3].tolist()
                        after=potential(m);reward=(1. if success else -1. if terminated else 0.)+.995*(0. if terminated else after)-before-.001
                        m.update(simulation_time_ns=1+step*100_000_000,is_success=success,terminated=terminated,truncated=truncated,
                            reward_terms=dict(potential_before=before,potential_after=after,gamma=.995),
                            failure='control_force_limit' if force_abort else (m.get('failure_reason') or 'physics_guard') if m['failed'] else None,
                            executed_action=action.tolist(),episode=episode,step=step,teacher_requests=teacher_requests)
                        m['task_goal_position']=env.goal_pos.tolist()
                        if pose_range:m['socket_pose']=env.manifest['episode_socket_pose']
                        m['joint_positions']=env.robot.get_joint_positions()[0].tolist()
                        last_measurement=m
                        teacher.previous=action.copy()
                        obs=capture()
                        with (a.output/'step_audit.jsonl').open('a') as stream:stream.write(json.dumps(m)+'\n')
                        send(connection,dict(ok=True,reward=float(reward),info=m),obs)
                    except Exception as exc:
                        traceback.print_exc();send(connection,dict(ok=False,error=f'{type(exc).__name__}: {exc}'))
        (a.output/'shutdown.json').write_text(json.dumps(dict(clean=True,episodes=episode))+'\n')
    except BaseException as exc:
        failed=True;traceback.print_exc();(a.output/'failure.json').write_text(json.dumps(dict(error=repr(exc),traceback=traceback.format_exc()),indent=2))
    finally:
        if server:server.close()
        if bound_socket and a.socket.exists():a.socket.unlink()
        app._app.post_quit(1 if failed else 0);app.close()

if __name__=='__main__':main()
