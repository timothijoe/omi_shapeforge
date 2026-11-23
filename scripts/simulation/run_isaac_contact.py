"""Bounded Isaac/PhysX counterpart of the SIM-r06 insertion experiment."""
import argparse
import json
import hashlib
import shutil
import os
import subprocess
from pathlib import Path
import sys
import traceback


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--transfer',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--isaac-root',type=Path,default=Path('/data/isaac-sim-5.1.0'))
    p.add_argument('--support',type=Path,default=Path('/data/omi_runtime/envs/isaac_contact_support'))
    p.add_argument('--dt',type=float,default=.0002);p.add_argument('--seed',type=int,default=7)
    p.add_argument('--steps',type=int,default=350);p.add_argument('--render',action='store_true')
    p.add_argument('--locked',action='store_true');p.add_argument('--lateral-mm',type=float,default=0.)
    p.add_argument('--yaw-deg',type=float,default=0.);p.add_argument('--contact-offset',type=float,default=1e-7)
    p.add_argument('--audit-all-colliders',action='store_true')
    p.add_argument('--solver',choices=('TGS','PGS'),default='PGS')
    p.add_argument('--contact-recipe',choices=('baseline','gentle'),default='baseline')
    p.add_argument('--force-limit',type=float,help='Stop and fail when control-sampled force exceeds this many N')
    p.add_argument('--image-recipe',choices=('baseline','refined'),default='baseline')
    p.add_argument('--sensor-resolution',type=int,default=128)
    a=p.parse_args()
    a.force_limit_explicit=a.force_limit is not None
    if a.contact_recipe=='gentle' and a.force_limit is None:a.force_limit=10.
    if a.sensor_resolution<128 or a.sensor_resolution>1024:p.error('sensor resolution must be 128..1024')
    if a.steps<1 or a.contact_offset<0:p.error('positive step count and nonnegative contact offset required')
    if a.dt<=0 or a.dt>.001 or abs(round(.1/a.dt)*a.dt-.1)>1e-9:p.error('dt must evenly divide 0.1 s and be <= 0.001')
    a.output.mkdir(parents=True,exist_ok=False)
    # Tiny 6x6 IK solves must not spawn a large BLAS pool alongside PhysX.
    for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):
        os.environ[name]='1'
    snapshot=a.output/'code_snapshot';snapshot.mkdir()
    source_root=Path(__file__).resolve().parents[2]
    files=[Path(__file__),*[source_root/'src/omi_shapeforge/sim'/name for name in (
        'isaac_contact_scene.py','isaac_contact_runtime.py','isaac_contact_kinematics.py','contact_teacher.py','isaac_contact_approach.py','isaac_appearance.py','box_overlap.py')]]
    common_root=source_root.parent/'omi_proj/src';files.append(common_root/'omi_hil_rl/hil/insertion_task.py')
    source_hashes={}
    for file in files:
        shutil.copy2(file,snapshot/file.name);source_hashes[str(file)]=hashlib.sha256(file.read_bytes()).hexdigest()
    (a.output/'execution.json').write_text(json.dumps(dict(arguments={k:str(v) if isinstance(v,Path) else v for k,v in vars(a).items()},
        sources_sha256=source_hashes,scope='exploratory PhysX insertion counterpart'),indent=2)+'\n')
    sys.path.insert(0,str(a.support));sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
    sys.path.insert(0,str(common_root))
    import omi_hil_rl.hil
    omi_hil_rl.hil.__path__=[str(snapshot.resolve())]
    import omi_shapeforge.sim
    omi_shapeforge.sim.__path__=[str(snapshot.resolve())]
    sys.argv=[sys.argv[0]]
    from isaacsim import SimulationApp
    extra=['--/app/extensions/registryEnabled=false']
    for directory in ['exts','extscache','kit/exts','kit/extscore']:extra+=['--ext-folder',str(a.isaac_root/directory)]
    if not a.render:
        for extension in ['omni.physx','omni.usd','omni.kit.loop','omni.kit.usd.layers','omni.kit.usd.mdl','omni.physx.tensors']:
            extra+=['--enable',extension]
    app=SimulationApp({'headless':True,'width':640,'height':480,'limit_cpu_threads':4,'multi_gpu':False,
        'extra_args':extra},experience=str(a.isaac_root/'apps/isaacsim.exp.base.python.kit') if a.render else None)
    failed=False
    try:
        import numpy as np
        import omni.usd
        if a.render:import omni.replicator.core as rep
        from pxr import UsdPhysics, PhysxSchema, Gf
        from omi_shapeforge.sim.isaac_contact_scene import build
        from omi_shapeforge.sim.isaac_contact_runtime import RobotExperiment, ContactMonitor, DirectWorld, matrix
        from omi_shapeforge.sim.contact_teacher import ContactInsertionTeacher
        from omi_shapeforge.sim.isaac_contact_approach import limit_approach
        context=omni.usd.get_context();context.new_stage()
        world=DirectWorld(context.get_stage(),app,a.dt)
        physics=UsdPhysics.Scene.Define(world.stage,'/World/PhysicsScene')
        physics.CreateGravityDirectionAttr(Gf.Vec3f(0,0,-1));physics.CreateGravityMagnitudeAttr(9.81)
        settings=PhysxSchema.PhysxSceneAPI.Apply(physics.GetPrim())
        settings.CreateEnableGPUDynamicsAttr(False);settings.CreateBroadphaseTypeAttr('MBP')
        settings.CreateSolverTypeAttr(a.solver);settings.CreateTimeStepsPerSecondAttr(round(1/a.dt))
        settings.CreateEnableStabilizationAttr(False)
        packet,audit=build(world.stage,a.transfer,a.output,contact_offset=a.contact_offset,
            locked=a.locked,lateral_mm=a.lateral_mm,yaw_deg=a.yaw_deg)
        if a.image_recipe=='refined':
            from omi_shapeforge.sim.isaac_appearance import apply_recipe,geometry_digest
            before=geometry_digest(world.stage)
            appearance=apply_recipe(world.stage,packet,audit,a.transfer,'refined')
            assert geometry_digest(world.stage)==before
            (a.output/'appearance.json').write_text(json.dumps(appearance,indent=2)+'\n')
            world.stage.GetRootLayer().Export(str(a.output/'scene_refined.usda'))
        print('USD_AUTHORED',flush=True)
        world.reset()
        print('PHYSICS_RESET',flush=True)
        # Compare actual PhysX cooked hulls to transferred source vertices.
        import omni.physx
        from pxr import PhysicsSchemaTools
        cooking=[]
        audited_names=[g['name'] for g in packet['geoms'] if g['contact'] and g['kind']==7] if a.audit_all_colliders else ['sim_module_013_collision_022','sim_socket_008_collision_000']
        for name in audited_names:
            path=audit['geom_paths'].get(name)
            if not path:continue
            def cooked(result,convexes,name=name,path=path):
                from scipy.spatial import ConvexHull
                source=np.asarray(world.stage.GetPrimAtPath(path).GetAttribute('points').Get())
                reference=ConvexHull(source)
                outside=[];missing=[]
                for c in convexes:
                    verts=np.asarray(c.vertices);h=ConvexHull(verts)
                    outside.append(max(0.,float(np.max(verts@reference.equations[:,:3].T+reference.equations[:,3]))))
                    missing.append(max(0.,float(np.max(source@h.equations[:,:3].T+h.equations[:,3]))))
                item=dict(name=name,result=str(result),source_vertices=len(source),cooked_vertices=[len(c.vertices) for c in convexes],
                    max_outward_mm=max(outside) if outside else None,max_missing_mm=max(missing) if missing else None)
                if not a.audit_all_colliders:
                    item.update(source_points=source.tolist(),hulls=[dict(vertices=np.asarray(c.vertices).tolist(),indices=list(c.indices),
                        polygons=[dict(index_base=p.index_base,num_vertices=p.num_vertices,plane=list(p.plane)) for p in c.polygons]) for c in convexes])
                cooking.append(item)
            omni.physx.get_physx_cooking_interface().request_convex_collision_representation(
                world.stage_id,PhysicsSchemaTools.sdfPathToInt(path),False,cooked)
        (a.output/'cooking_audit.json').write_text(json.dumps(cooking,indent=2)+'\n')
        cameras={}
        if a.render:
            if a.image_recipe=='refined':rep.settings.set_render_rtx_realtime(antialiasing='DLAA')
            class Camera:
                def __init__(self,path,resolution):
                    self.product=rep.create.render_product(path,resolution)
                    self.annotator=rep.AnnotatorRegistry.get_annotator('rgb');self.annotator.attach([self.product])
                def initialize(self):pass
                def get_rgba(self):return self.annotator.get_data()
            for name,path in audit['cameras'].items():
                if name not in ('head_rgb','wrist_rgb','overview'):continue
                overview_resolution=(1280,960) if a.sensor_resolution>128 else (640,480)
                camera=Camera(path,resolution=overview_resolution if name=='overview' else (a.sensor_resolution,a.sensor_resolution))
                camera.initialize();cameras[name]=camera
                print('CAMERA_INITIALIZED',name,flush=True)
            for _ in range(5):world.render()
        print('SCENE_READY',json.dumps(dict(robot=audit['robot'],colliders=audit['collider_count'])),flush=True)
        rows=[];frames=[];camera_checks=[]
        if audit['robot']:
            env=RobotExperiment(world,packet,audit,a.output,a.dt,cameras);kin=env.reset(a.seed)
            if env.contact_assessment and not a.force_limit_explicit:a.force_limit=None
            if a.contact_recipe=='gentle':
                axis=-np.asarray(env.manifest['socket_to_world']['rotation'])[:,1]
                env.goal_pos=np.asarray(env.manifest['seated_tcp_position'])+axis*.00003
            world.stage.GetRootLayer().Export(str(a.output/'initial_pose.usda'))
            teacher=ContactInsertionTeacher();phases={}
            for phase in ['insert','withdraw']:
                if phase=='withdraw':
                    if not rows[-1]['is_success']:break
                    env.begin_withdrawal();teacher.reset()
                for step in range(a.steps):
                    action,control=teacher.act(env);approach=dict(active=False)
                    if a.contact_recipe=='gentle':
                        action,approach=limit_approach(action,env.scale,axis,
                            env.manifest['shoulder_depth_mm']-env.measurements()['insertion_depth_mm'],env.phase)
                    row=env.step(action);row['action']=action.tolist();row['approach']=approach
                    if a.force_limit is not None and row['contact_force_N']>a.force_limit:
                        row.update(is_success=False,failed=True,failure='control_force_limit')
                        env._finished=True
                    row['joint_positions']=env.robot.get_joint_positions()[0].tolist()
                    rows.append(row)
                    with (a.output/'trajectory.jsonl').open('a') as stream:stream.write(json.dumps(row)+'\n')
                    if a.render:
                        obs=env.capture()
                        camera_checks.append(dict(step=len(rows),rgb_shape=list(obs['rgb'].shape),native_resolution=a.sensor_resolution,history=int(obs['history_mask'].sum())))
                        from PIL import Image, ImageDraw
                        overview=cameras['overview'].get_rgba()[:,:,:3].astype(np.uint8)
                        high=a.sensor_resolution>128
                        side=512 if high else 256;main_width=1280 if high else 640
                        panel_height=1024 if high else 544
                        panel=Image.new('RGB',(main_width+side,panel_height),'#14202b');panel.paste(Image.fromarray(overview),(0,32))
                        for name,y in [('head_rgb',0 if high else 32),('wrist_rgb',side if high else 288)]:
                            panel.paste(Image.fromarray(cameras[name].get_rgba()[:,:,:3].astype(np.uint8)).resize((side,side)),(main_width,y))
                        draw=ImageDraw.Draw(panel)
                        draw.text((12,10),'Isaac Sim / PhysX CPU | SIM-r06 | HEAD (top right) / WRIST (bottom right)',fill='white')
                        draw.text((12,panel_height-24),f"{phase} step {step+1} | depth {row['insertion_depth_mm']:.2f} mm | force {row['contact_force_N']:.2f} N | fixed attachment",fill='white')
                        frame=np.asarray(panel);frames.append(frame)
                        if step==0:
                            Image.fromarray(overview).save(a.output/f'{phase}_overview.png')
                            for n in ('head_rgb','wrist_rgb'):
                                Image.fromarray(cameras[n].get_rgba()[:,:,:3].astype(np.uint8)).save(a.output/f'{phase}_{n}.png')
                    if step%20==0 or env._finished:print('STEP',json.dumps(row),flush=True)
                    if env._finished:break
                phases[phase]=dict(success=rows[-1]['is_success'],steps=step+1,final_depth_mm=rows[-1]['insertion_depth_mm'])
            passed=all(phases.get(k,{}).get('success',False) for k in ['insert','withdraw'])
            report=dict(phases=phases,kinematics=kin,accepted=passed)
        else:
            manifest=packet['manifest'];monitor=ContactMonitor(a.dt,manifest.get('contact_shoulder_pair'))
            drive=UsdPhysics.DriveAPI(world.stage.GetPrimAtPath(audit['joint_paths']['insertion']),'linear')
            module_path=audit['frame_paths']['sim_module'];socket_path=audit['frame_paths']['sim_socket']
            def depth():
                local=np.linalg.inv(matrix(world.stage,socket_path))@matrix(world.stage,module_path)
                tip=local[:3,3]+local[:3,:3]@np.array([0,manifest['leading_tip_y_mm']/1000,0])
                return float(manifest['mouth_y_mm']-tip[1]*1000)
            initial=depth();end=manifest['shoulder_depth_mm'];phases={};stable=0
            for phase in ['insert','withdraw']:
                if phase=='withdraw' and not phases['insert']['success']:break
                for step in range(a.steps):
                    target_mm=min(end+.15,initial+(step+1)*.5) if phase=='insert' else max(initial,end-(step+1)*.5)
                    drive.GetTargetPositionAttr().Set((target_mm-initial)/1000)
                    monitor.clear()
                    for _ in range(round(.1/a.dt)):
                        monitor.start_substep();world.step(render=False)
                    world.sync()
                    value=depth();settled=abs(value-(end if phase=='insert' else initial))<.15
                    if phase=='insert':settled=settled and monitor.last['shoulder']
                    stable=stable+1 if settled else 0
                    row=dict(phase=phase,step=step+1,insertion_depth_mm=value,target_depth_mm=target_mm,
                        peak_penetration_mm=monitor.peak,contact_force_N=monitor.last.get('force_N',0.),
                        step_peak_contact_force_N=monitor.peak_force,shoulder_contact=monitor.last['shoulder'],
                        step_any_shoulder_contact=monitor.shoulder,
                        is_success=stable>=3 and monitor.peak<.05)
                    row['pad_travel_mm']=[]
                    for j in packet['joints']:
                        if not j['name'].startswith('pad_'):continue
                        b=packet['bodies'][j['body']];t=matrix(world.stage,audit['body_paths'][b['name']])
                        axis=np.asarray(b['world_rotation'])@j['axis']
                        row['pad_travel_mm'].append(float((t[:3,3]-b['world_position'])@axis*1000))
                    row['contact_pairs']=sorted(monitor.pairs)
                    rows.append(row)
                    with (a.output/'trajectory.jsonl').open('a') as stream:stream.write(json.dumps(row)+'\n')
                    if a.render and step%5==0:
                        for _ in range(2):world.render()
                        frames.append(cameras['overview'].get_rgba()[:,:,:3].astype(np.uint8))
                    if step%20==0:print('LOCAL',json.dumps(row),flush=True)
                    if row['is_success'] or monitor.peak>.05 or row['contact_force_N']>10:break
                    # Negative cases stop after ample attempted advance beyond blockage.
                    if (a.locked or a.lateral_mm or a.yaw_deg) and step>50 and value<15:break
                    if step>40 and max(r['insertion_depth_mm'] for r in rows[-20:])-min(r['insertion_depth_mm'] for r in rows[-20:])<.001:
                        row['stop_reason']='stalled_for_2_simulated_seconds';break
                phases[phase]=dict(success=rows[-1]['is_success'],final_depth_mm=value,steps=step+1)
                stable=0
            negative=bool(a.locked or a.lateral_mm or a.yaw_deg)
            safe=all(r['peak_penetration_mm']<.05 for r in rows)
            accepted=(not phases['insert']['success'] and phases['insert']['final_depth_mm']<15 and safe) if negative else (all(phases.get(k,{}).get('success',False) for k in ['insert','withdraw']) and safe)
            report=dict(phases=phases,negative_case=negative,accepted=accepted,last_contact_pairs=sorted(monitor.pairs))
        (a.output/'trajectory.json').write_text(json.dumps(rows,indent=2)+'\n')
        if frames:
            from PIL import Image
            Image.fromarray(frames[len(frames)//2]).save(a.output/'preview.png')
            height,width=frames[0].shape[:2]
            encoder=subprocess.Popen(['ffmpeg','-v','error','-n','-f','rawvideo','-pixel_format','rgb24',
                '-video_size',f'{width}x{height}','-framerate','10' if audit['robot'] else '2',
                '-i','-','-an','-c:v','libx264','-pix_fmt','yuv420p','-movflags','+faststart',str(a.output/'cycle.mp4')],stdin=subprocess.PIPE)
            for frame in frames:encoder.stdin.write(frame.tobytes())
            encoder.stdin.close()
            if encoder.wait():raise RuntimeError('video encoding failed')
        report.update(engine='Isaac Sim / PhysX CPU',isaac_version=(a.isaac_root/'VERSION').read_text().strip(),
            dt=a.dt,control_dt=.1,solver=a.solver,seed=a.seed,asset_id=packet['manifest'].get('asset_id'),
            renderer_executed=a.render,camera_checks=camera_checks,physics_accuracy_validated=False,
            training_executed=False,contact_recipe=a.contact_recipe,control_force_limit_N=a.force_limit,
            image_recipe=a.image_recipe,native_sensor_resolution=a.sensor_resolution,policy_resolution=128,
            insertion_assessment=packet['manifest'].get('insertion_assessment'),
            sources_sha256=source_hashes,limitations=audit['limitations'])
        (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
        print('RESULT',json.dumps(report),flush=True)
        failed=not report['accepted']
    except BaseException as exc:
        failed=True;traceback.print_exc()
        (a.output/'failure.json').write_text(json.dumps(dict(error=repr(exc),traceback=traceback.format_exc()),indent=2)+'\n')
    finally:
        # Kit fast shutdown may terminate the interpreter inside close().
        # Set its native return code before releasing the framework.
        app._app.post_quit(1 if failed else 0)
        app.close()
    if failed:raise SystemExit(1)


if __name__=='__main__':main()
