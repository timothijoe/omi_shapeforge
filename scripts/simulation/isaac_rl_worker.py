"""Isaac process for rule-feedback RL; real PhysX and real RGB observations."""
import argparse,hashlib,json,os,shutil,socket,sys,traceback
from pathlib import Path

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--transfer',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--socket',type=Path,required=True);p.add_argument('--max-steps',type=int,default=350);p.add_argument('--no-render',action='store_true')
    p.add_argument('--physics-dt',type=float,default=.0002)
    p.add_argument('--teacher-min-step-mm',type=float,default=.01)
    p.add_argument('--target-overtravel-mm',type=float,default=.03)
    a=p.parse_args()
    if not 0<a.physics_dt<=.001 or abs(round(.1/a.physics_dt)*a.physics_dt-.1)>1e-9:p.error('physics dt must divide 0.1 s')
    if not 0<a.teacher_min_step_mm<=.1 or not 0<=a.target_overtravel_mm<=.2:p.error('invalid approach settings')
    a.output.mkdir(parents=True,exist_ok=False)
    for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
    repo=Path(__file__).resolve().parents[2];sys.path[:0]=['/data/omi_runtime/envs/isaac_contact_support',str(repo/'src')]
    snapshot=a.output/'code_snapshot';snapshot.mkdir()
    common_root=repo.parent/'omi_proj/src';sys.path.insert(0,str(common_root))
    for f in [Path(__file__),common_root/'omi_hil_rl/hil/insertion_task.py',*[repo/'src/omi_shapeforge/sim'/n for n in ['isaac_contact_scene.py','isaac_contact_runtime.py','isaac_contact_kinematics.py','isaac_appearance.py','isaac_contact_approach.py','contact_teacher.py','wrist_fisheye.py','isaac_ipc.py','box_overlap.py']]]:shutil.copy2(f,snapshot/f.name)
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
        from omi_shapeforge.sim.isaac_appearance import apply_recipe
        from omi_shapeforge.sim.isaac_contact_approach import limit_approach
        from omi_shapeforge.sim.contact_teacher import ContactInsertionTeacher
        from omi_shapeforge.sim.wrist_fisheye import inverse_theta
        from omi_shapeforge.sim.isaac_ipc import send,receive
        context=omni.usd.get_context();context.new_stage();world=DirectWorld(context.get_stage(),app,a.physics_dt)
        physics=UsdPhysics.Scene.Define(world.stage,'/World/PhysicsScene');physics.CreateGravityDirectionAttr(Gf.Vec3f(0,0,-1));physics.CreateGravityMagnitudeAttr(9.81)
        settings=PhysxSchema.PhysxSceneAPI.Apply(physics.GetPrim());settings.CreateEnableGPUDynamicsAttr(False);settings.CreateBroadphaseTypeAttr('MBP');settings.CreateSolverTypeAttr('PGS');settings.CreateTimeStepsPerSecondAttr(round(1/a.physics_dt));settings.CreateEnableStabilizationAttr(False)
        packet,audit=build(world.stage,a.transfer,a.output,contact_offset=1e-7)
        if packet['manifest'].get('wrist_tool_asset')!='WG-DAIMON-OBS-r10' or (packet['manifest'].get('module_visual_asset') or {}).get('asset_id')!='OM-001/V4 r08':
            raise ValueError('this study requires the pinned WG-r10 / OM-r08 scene')
        apply_recipe(world.stage,packet,audit,a.transfer,'refined');world.reset()
        env=RobotExperiment(world,packet,audit,a.output,a.physics_dt);env.max_steps=a.max_steps
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
        cameras={};products=[]
        if not a.no_render:
            import omni.replicator.core as rep
            rep.settings.set_render_rtx_realtime(antialiasing='DLAA')
            for name,size in [('head_rgb',256),('wrist_rgb',N)]:
                product=rep.create.render_product(audit['cameras'][name],(size,size));products.append(product)
                ann=rep.AnnotatorRegistry.get_annotator('rgb');ann.attach(product);cameras[name]=ann
            for _ in range(3):world.render()
        history=deque(maxlen=10);teacher=ContactInsertionTeacher();episode=0;step=0;finished=True;teacher_requests=0
        def capture():
            if a.no_render:return {}
            before=env.robot.get_joint_positions().copy();velocity=env.robot.view.get_dof_velocities().copy()
            world.render()
            np.testing.assert_allclose(env.robot.get_joint_positions(),before,atol=1e-9,rtol=0)
            np.testing.assert_allclose(env.robot.view.get_dof_velocities(),velocity,atol=1e-9,rtol=0)
            head=cameras['head_rgb'].get_data()[:,:,:3];front=cameras['wrist_rgb'].get_data()[:,:,:3].astype(float)
            wrist=np.rint(front[iy,ix]*(1-wx)*(1-wy)+front[iy,ix+1]*wx*(1-wy)+front[iy+1,ix]*(1-wx)*wy+front[iy+1,ix+1]*wx*wy).clip(0,255).astype(np.uint8)
            head=np.asarray(Image.fromarray(head).resize((128,128),Image.Resampling.LANCZOS))
            assert head.std()>1 and wrist.std()>1
            history.append(dict(rgb=head.transpose(2,0,1),wrist_rgb=wrist.transpose(2,0,1)))
            missing=10-len(history);result={k:np.stack([np.zeros_like(z)]*missing+[h[k] for h in history]) for k,z in history[-1].items()}
            result.update(state=np.zeros((10,14),np.float32),tactile=np.zeros((10,10,16,24),np.float32),
                camera_mask=np.array([[0.,0.]]*missing+[[1.,1.]]*len(history),np.float32),history_mask=np.array([0]*missing+[1]*len(history),np.uint8))
            return result
        def potential():return -10*float(np.linalg.norm(env._error()[:3]))-.5*env.measurements()['alignment_angle_rad']
        def info():
            return dict(env.measurements(),simulation_time_ns=1+step*100_000_000,episode=episode,step=step,
                is_success=False,terminated=False,truncated=False,task=env.task_id)
        meta=dict(transfer=str(a.transfer.resolve()),transfer_sha256=hashlib.sha256((a.transfer/'transfer.json').read_bytes()).hexdigest(),
            rendered=not a.no_render,physics_dt=a.physics_dt,control_dt=.1,projection=projection,wrist_roi=[766,566,1155,955],
            wrist_sampling='rint(linspace(0,388,128)); fisheye rays sampled from 512px 90deg front cube',
            current_assets=['WG-DAIMON-OBS-r10','OM-001/V4 r08'],policy_inputs='two RGB histories and validity masks; state/tactile zero padding',
            execution_config=dict(max_steps=a.max_steps,physics_dt=a.physics_dt,control_dt=.1,
                teacher_min_step_mm=a.teacher_min_step_mm,target_overtravel_mm=a.target_overtravel_mm,
                joint_target_interpolation=env.manifest.get('joint_target_interpolation','none'),
                global_contact_offset_m=1e-7,per_collider_contact_offsets_m=audit.get('per_collider_contact_offsets_m',{}),
                force_stop_N=None if env.contact_assessment else 10.,
                penetration_stop_mm=None if env.contact_assessment else .05,solver='PGS',
                insertion_assessment=env.manifest.get('insertion_assessment')))
        if not env.contact_assessment:meta['execution_config'].pop('insertion_assessment')
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
                            episode+=1;step=0;teacher_requests=0;history.clear();teacher.reset();env.reset(int(request['seed']))
                            env.goal_pos=np.asarray(env.manifest['seated_tcp_position'])+axis*(a.target_overtravel_mm/1000)
                            finished=False;obs=capture();state=info()
                            send(connection,dict(ok=True,info=state),obs);continue
                        if finished:raise RuntimeError('reset required before stepping')
                        if command=='teacher':
                            teacher_requests+=1
                            action,detail=teacher.act(env);action,limit=limit_approach(action,env.scale,axis,env.manifest['shoulder_depth_mm']-env.measurements()['insertion_depth_mm'],env.phase,minimum_mm=a.teacher_min_step_mm)
                            send(connection,dict(ok=True,action=action.tolist(),audit=dict(detail,approach=limit)));continue
                        if command!='step':raise ValueError('unknown command')
                        before=potential();action=np.asarray(request['action'],np.float32);m=env.step(action);step+=1
                        force_abort=not env.contact_assessment and m['contact_force_N']>10.;terminated=bool(m['failed'] or force_abort or m['is_success']);success=bool(m['is_success'] and not m['failed'] and not force_abort)
                        truncated=bool(step>=a.max_steps and not terminated);finished=terminated or truncated;env._finished=finished
                        after=potential();reward=(1. if success else -1. if terminated else 0.)+.995*(0. if terminated else after)-before-.001
                        m.update(simulation_time_ns=1+step*100_000_000,is_success=success,terminated=terminated,truncated=truncated,
                            reward_terms=dict(potential_before=before,potential_after=after,gamma=.995),
                            failure='control_force_limit' if force_abort else (m.get('failure_reason') or 'physics_guard') if m['failed'] else None,
                            executed_action=action.tolist(),episode=episode,step=step,teacher_requests=teacher_requests)
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
