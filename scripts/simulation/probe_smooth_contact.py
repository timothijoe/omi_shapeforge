"""Actual robot withdrawal/re-alignment probe for a frozen contact transfer.

The scripted diagnostic is not a learned-policy evaluation. All movements after
reset use normal IK and PhysX drives, including withdrawal and correction.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import traceback


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--transfer', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--offset-mm', type=float, default=1.)
    parser.add_argument('--dt', type=float, default=.0002)
    parser.add_argument('--contact-offset', type=float, default=1e-7)
    parser.add_argument('--seed', type=int, default=7)
    parser.add_argument('--skip-final-withdrawal', action='store_true')
    parser.add_argument('--interior-rub-mm',type=float,default=0.,help='After qualified entry, test controlled light side contact, then recenter')
    parser.add_argument('--render',action='store_true')
    parser.add_argument('--preview-only',action='store_true')
    args = parser.parse_args()
    if args.preview_only and not args.render:parser.error('--preview-only requires --render')
    if args.dt <= 0 or args.dt > .001 or abs(round(.1/args.dt)*args.dt-.1) > 1e-9:
        parser.error('dt must divide 0.1 s and be <= 0.001')
    if args.contact_offset <= 0:
        parser.error('contact offset must be positive')
    args.output.mkdir(parents=True, exist_ok=False)
    for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
        os.environ[name] = '1'
    root = Path(__file__).resolve().parents[2]
    snapshot = args.output/'code_snapshot'
    snapshot.mkdir()
    sources = [Path(__file__)] + [root/'src/omi_shapeforge/sim'/name for name in (
        'isaac_contact_scene.py', 'isaac_contact_runtime.py', 'isaac_contact_kinematics.py',
        'contact_teacher.py', 'isaac_contact_approach.py', 'isaac_contact_diagnostics.py', 'box_overlap.py',
        'isaac_demo_recorder.py','isaac_appearance.py','wrist_fisheye.py')]
    common_root=root.parent/'omi_proj/src'
    sources.append(common_root/'omi_hil_rl/hil/insertion_task.py')
    hashes = {}
    for path in sources:
        shutil.copy2(path, snapshot/path.name)
        hashes[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
    (args.output/'execution.json').write_text(json.dumps(dict(arguments={k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()}, sources_sha256=hashes), indent=2)+'\n')
    sys.path.insert(0, '/data/omi_runtime/envs/isaac_contact_support')
    sys.path.insert(0, str(root/'src'))
    sys.path.insert(0, str(common_root))
    import omi_hil_rl.hil
    omi_hil_rl.hil.__path__ = [str(snapshot)]
    import omi_shapeforge.sim
    omi_shapeforge.sim.__path__ = [str(snapshot)]
    sys.argv = [sys.argv[0]]
    from isaacsim import SimulationApp
    extra = ['--/app/extensions/registryEnabled=false']
    for directory in ('exts', 'extscache', 'kit/exts', 'kit/extscore'):
        extra += ['--ext-folder', '/data/isaac-sim-5.1.0/'+directory]
    for extension in ('omni.physx', 'omni.usd', 'omni.kit.loop', 'omni.kit.usd.layers', 'omni.kit.usd.mdl', 'omni.physx.tensors'):
        extra += ['--enable', extension]
    app = SimulationApp(dict(headless=True, limit_cpu_threads=4, multi_gpu=False, extra_args=extra),
        experience='/data/isaac-sim-5.1.0/apps/isaacsim.exp.base.python.kit' if args.render else None)
    accepted = False
    recorder=None
    try:
        import numpy as np
        import omni.usd
        from pxr import UsdPhysics, PhysxSchema, Gf
        from omi_shapeforge.sim.isaac_contact_scene import build
        from omi_shapeforge.sim.isaac_contact_runtime import DirectWorld, RobotExperiment
        from omi_shapeforge.sim.isaac_contact_diagnostics import DiagnosticContactMonitor
        from omi_shapeforge.sim.contact_teacher import ContactInsertionTeacher
        from omi_shapeforge.sim.isaac_contact_approach import limit_approach
        context = omni.usd.get_context()
        context.new_stage()
        world = DirectWorld(context.get_stage(), app, args.dt)
        scene = UsdPhysics.Scene.Define(world.stage, '/World/PhysicsScene')
        scene.CreateGravityDirectionAttr(Gf.Vec3f(0, 0, -1))
        scene.CreateGravityMagnitudeAttr(9.81)
        settings = PhysxSchema.PhysxSceneAPI.Apply(scene.GetPrim())
        settings.CreateEnableGPUDynamicsAttr(False)
        settings.CreateBroadphaseTypeAttr('MBP')
        settings.CreateSolverTypeAttr('PGS')
        settings.CreateTimeStepsPerSecondAttr(round(1/args.dt))
        settings.CreateEnableStabilizationAttr(False)
        packet, audit = build(world.stage, args.transfer, args.output, contact_offset=args.contact_offset)
        if args.render:
            from omi_shapeforge.sim.isaac_appearance import apply_recipe,geometry_digest
            before=geometry_digest(world.stage)
            appearance=apply_recipe(world.stage,packet,audit,args.transfer,'refined')
            assert geometry_digest(world.stage)==before
            (args.output/'appearance.json').write_text(json.dumps(appearance,indent=2)+'\n')
        world.reset()
        env = RobotExperiment(world, packet, audit, args.output, args.dt)
        env.reset(args.seed)
        env.max_steps = 2000
        rotation = np.asarray(env.manifest['socket_to_world']['rotation'])
        axis = -rotation[:, 1]
        offset = rotation[:, 0]*args.offset_mm/1000
        env.monitor.sub = None
        env.monitor = DiagnosticContactMonitor(args.dt, axis, env.manifest.get('contact_shoulder_pair'))
        if args.render:
            from omi_shapeforge.sim.isaac_demo_recorder import RuleDemoRecorder
            recorder=RuleDemoRecorder(world,env,packet,audit,args.output)
            initial=env.measurements();initial['step']=0
            recorder.capture(initial,'preview' if args.preview_only else 'initial')
            if args.preview_only:
                (args.output/'preview_only.json').write_text(json.dumps(dict(preview_only=True,counts_as_trial=False))+'\n')
                accepted=True
                return
        outside = np.asarray(env.manifest['preinsert_tcp_position'])
        seated = np.asarray(env.manifest['seated_tcp_position']) + axis*.0001
        records = []
        phases = []

        def move(name, goal, mode, cap=.85, max_steps=450):
            # Advance the scripted task phase after a successful withdrawal.
            # Clear only terminal bookkeeping; do not change physical state.
            if env._finished:
                if not records or not records[-1]['is_success']:
                    raise RuntimeError('Cannot continue a failed physical state')
                env._finished = False
            env._stable = 0
            # Recovery remains inside the insertion task. Reaching the outside
            # waypoint is not an insertion success or an episode reset.
            env.phase = 'insert' if env.contact_assessment and name!='withdraw_aligned' else mode
            env.goal_pos = goal.copy()
            teacher = ContactInsertionTeacher()
            phase_rows = []
            reason = 'timeout'
            for _ in range(max_steps):
                action, _ = teacher.act(env)
                action = np.clip(action, -cap, cap)
                if name == 'insert_aligned':
                    remaining = env.manifest['shoulder_depth_mm']-env.measurements()['insertion_depth_mm']
                    # At sub-mm depth, 10um commands can stall under small-dt
                    # articulation arithmetic. Use a bounded 50um minimum
                    # target increment and 100um preload; physical stop and
                    # unchanged force/penetration guards still constrain motion.
                    delta = action[:3]*env.scale[:3]
                    axial = float(delta@axis)
                    if remaining < 2.:
                        limit = float(np.clip(max(remaining,0.)*.2,.05,.1))/1000
                        action[:3] = (delta+axis*(min(axial,limit)-axial))/env.scale[:3]
                row = env.step(action)
                row.update(env.monitor.summary())
                row.update(probe_phase=name, action=action.tolist(), tcp_position=env.tcp()[:3, 3].tolist())
                row['joint_positions']=env.robot.get_joint_positions()[0].tolist()
                records.append(row)
                phase_rows.append(row)
                with (args.output/'trajectory.jsonl').open('a') as stream:
                    stream.write(json.dumps(row)+'\n')
                if recorder:recorder.capture(row,name)
                if row['failed']:
                    reason = 'physics_guard'
                    break
                if not env.contact_assessment and row['contact_force_N'] > 10:
                    reason = 'force_guard'
                    break
                if name == 'push_misaligned':
                    recent = phase_rows[-6:]
                    stalled = len(recent) == 6 and np.ptp([r['insertion_depth_mm'] for r in recent]) < .005
                    # A rigid entrance can stop a small increment with little
                    # force. Detect contact plus lack of progress, not only a
                    # high force threshold that would require harder pushing.
                    blocked = row.get('recovery_required',False) if env.contact_assessment else (
                        row['scalar_contact_sum_mean_N'] > .3 or (
                            stalled and row['scalar_contact_sum_mean_N'] > .05
                            and np.linalg.norm(env._error()[:3]) > .0005))
                    if blocked:
                        reason = 'entrance_blocked'
                        break
                if name == 'insert_aligned' and row['is_success']:
                    reason = 'seated'
                    break
                if name != 'insert_aligned' and np.linalg.norm(env._error()[:3]) < .00008:
                    reason = 'target_reached'
                    break
                if mode == 'withdraw' and row['is_success']:
                    reason = 'target_reached'
                    break
                if env._finished:
                    reason = 'episode_finished'
                    break
            result = dict(phase=name, reason=reason, steps=len(phase_rows),
                depth_mm=phase_rows[-1]['insertion_depth_mm'],
                max_depth_mm=max(r['insertion_depth_mm'] for r in phase_rows),
                scalar_sample_max_N=max(r['contact_force_N'] for r in phase_rows),
                scalar_mean_max_N=max(r['scalar_contact_sum_mean_N'] for r in phase_rows),
                axial_mean_max_N=max(r['axial_absolute_sum_mean_N'] for r in phase_rows),
                penetration_max_mm=max(r['step_peak_penetration_mm'] for r in phase_rows))
            phases.append(result)
            print('PHASE', json.dumps(result), flush=True)
            if reason in ('physics_guard', 'force_guard', 'timeout', 'episode_finished'):
                raise RuntimeError('Probe phase failed: '+json.dumps(result))
            return result

        if args.offset_mm:
            move('offset_outside', outside+offset, 'withdraw')
            move('approach_offset_outside', outside+axis*.004+offset, 'withdraw')
            # The target is 3 mm past the entrance; a valid entrance obstruction
            # must be observed before that target, not merely a small movement.
            mouth_goal = seated-axis*((env.manifest['shoulder_depth_mm']-3.+.1)/1000)+offset
            blocked = move('push_misaligned', mouth_goal, 'insert', cap=.05, max_steps=600)
            if blocked['reason'] != 'entrance_blocked' or blocked['max_depth_mm'] > 2.:
                raise RuntimeError('Misaligned shaft was not blocked at the entrance')
            move('retreat_same_offset', outside+offset, 'withdraw')
        move('align_outside', outside, 'withdraw')
        if args.interior_rub_mm:
            move('enter_guide',seated-axis*((env.manifest['shoulder_depth_mm']-10.+.1)/1000),'insert')
            if not env.contact_assessment or not env.contact_assessment.inside:
                raise RuntimeError('light-contact test requires qualified entry')
            move('slide_with_contact',seated-axis*((env.manifest['shoulder_depth_mm']-30.+.1)/1000)+rotation[:,2]*args.interior_rub_mm/1000,'insert')
        move('insert_aligned', seated, 'insert')
        if not args.skip_final_withdrawal:
            env.begin_withdrawal()
            move('withdraw_aligned', outside, 'withdraw')
        interior = [r for r in records if r['probe_phase'] in ('enter_guide','slide_with_contact','insert_aligned')
                    and 5 < r['insertion_depth_mm'] < env.manifest['shoulder_depth_mm']-1.]
        if not interior:
            raise RuntimeError('No interior samples')
        interior_report = dict(samples=len(interior),
            scalar_sample_max_N=max(r['contact_force_N'] for r in interior),
            scalar_mean_max_N=max(r['scalar_contact_sum_mean_N'] for r in interior),
            axial_mean_max_N=max(r['axial_absolute_sum_mean_N'] for r in interior),
            substep_peak_max_N=max(r['step_peak_contact_force_N'] for r in interior),
            minimum_depth_increment_mm=min(b['insertion_depth_mm']-a['insertion_depth_mm'] for a,b in zip(interior, interior[1:])))
        # A predeclared behavioural criterion for this uncalibrated candidate,
        # independent of the unchanged historical 10 N termination threshold.
        accepted = (any(p['phase']=='insert_aligned' and p['reason']=='seated' for p in phases)
                    and all(not r['failed'] for r in records)) if env.contact_assessment else (
                        interior_report['axial_mean_max_N'] < 1. and interior_report['minimum_depth_increment_mm'] > 0)
        if args.interior_rub_mm:
            rubbing=[r for r in records if r['probe_phase']=='slide_with_contact']
            if not any(r['step_any_module_contact'] for r in rubbing):
                raise RuntimeError('rub test produced no physical contact')
        report = dict(accepted=accepted, phases=phases, interior=interior_report,
            candidate=packet['manifest'].get('contact_candidate'), offset_mm=args.offset_mm,
            dt=args.dt, seed=args.seed, reset_count=1, teleport_after_reset=False,
            contact_offset_m=args.contact_offset,
            final_withdrawal_executed=not args.skip_final_withdrawal,
            insertion_assessment=env.manifest.get('insertion_assessment'),
            interior_rub_mm=args.interior_rub_mm,
            seated_target_overtravel_mm=.1, minimum_final_axial_target_increment_mm=.05,
            rendered=args.render, learned_policy=False, physical_calibration=False,
            source_transfer_sha256=hashlib.sha256((args.transfer/'transfer.json').read_bytes()).hexdigest())
        (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
        print('RESULT', json.dumps({k:v for k,v in report.items() if k != 'candidate'}), flush=True)
    except BaseException as exc:
        traceback.print_exc()
        (args.output/'failure.json').write_text(json.dumps(dict(error=repr(exc), traceback=traceback.format_exc()), indent=2)+'\n')
    finally:
        if recorder:
            try:recorder.close(accepted and not args.preview_only)
            except Exception as exc:
                accepted=False
                (args.output/'video_failure.json').write_text(json.dumps(dict(error=repr(exc)))+'\n')
        app._app.post_quit(0 if accepted else 1)
        app.close()


if __name__ == '__main__':
    main()
