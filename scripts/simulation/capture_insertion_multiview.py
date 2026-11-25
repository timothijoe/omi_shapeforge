"""Render a saved successful PhysX trajectory with synchronized RTX cameras.

This is a visual replay of measured joint states, not a new physics trial.
Rigid template poses, calibrated wrist projection and source state IDs are saved.
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
    parser.add_argument('--case', type=Path, required=True)
    parser.add_argument('--worker', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--indices', type=int, nargs='+')
    parser.add_argument('--subframes', type=int, default=3)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
        os.environ[key] = '1'
    root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, '/data/omi_runtime/envs/isaac_contact_support')
    sys.path.insert(0, str(root/'src'))
    snapshot = args.output/'source_snapshot'
    snapshot.mkdir()
    sources = [Path(__file__), *[root/'src/omi_shapeforge/sim'/n for n in
               ('isaac_contact_scene.py', 'isaac_contact_kinematics.py', 'isaac_appearance.py', 'wrist_fisheye.py')]]
    for p in sources:
        shutil.copy2(p, snapshot/p.name)
    protected = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in
                 [args.transfer/'transfer.json', args.transfer/'meshes.npz',
                  args.case/'trajectory.jsonl', args.case/'report.json', args.worker/'kinematics_check.json']}
    sys.argv = [sys.argv[0]]
    from isaacsim import SimulationApp
    isaac = Path('/data/isaac-sim-5.1.0')
    extra = ['--/app/extensions/registryEnabled=false']
    for d in ('exts', 'extscache', 'kit/exts', 'kit/extscore'):
        extra += ['--ext-folder', str(isaac/d)]
    app = SimulationApp(dict(headless=True, width=1000, height=820, limit_cpu_threads=4,
                             multi_gpu=False, extra_args=extra),
                        experience=str(isaac/'apps/isaacsim.exp.base.python.kit'))
    failed = False
    try:
        import numpy as np
        import omni.usd
        import omni.replicator.core as rep
        from PIL import Image
        from pxr import Gf, UsdGeom, UsdPhysics
        from omi_shapeforge.sim.isaac_contact_scene import build, set_pose
        from omi_shapeforge.sim.isaac_contact_kinematics import Kinematics, local_pose
        from omi_shapeforge.sim.isaac_appearance import apply_recipe
        from omi_shapeforge.sim.wrist_fisheye import FACES, CV_TO_GL, maps, reproject

        trajectory = [json.loads(s) for s in (args.case/'trajectory.jsonl').read_text().splitlines()]
        case_report = json.loads((args.case/'report.json').read_text())
        assert case_report['success'] and trajectory[-1]['is_success']
        assert trajectory[0]['insertion_depth_mm'] < 0 and trajectory[-1]['insertion_depth_mm'] > 50
        names = json.loads((args.worker/'kinematics_check.json').read_text())['joint_names']
        context = omni.usd.get_context()
        context.new_stage()
        stage = context.get_stage()
        packet, audit = build(stage, args.transfer, args.output)
        appearance = apply_recipe(stage, packet, audit, args.transfer, 'refined')
        (args.output/'appearance.json').write_text(json.dumps(appearance, indent=2))
        for prim in stage.Traverse():
            if prim.HasAPI(UsdPhysics.RigidBodyAPI):
                UsdPhysics.RigidBodyAPI(prim).CreateRigidBodyEnabledAttr(False)
        kin = Kinematics(packet)
        ids = {b['name']: b['id'] for b in packet['bodies']}
        wrist = next(c for c in packet['cameras'] if c['name'] == 'wrist_rgb')
        projection = dict(packet['manifest']['observation_projection'])
        projection['K'] = (np.array([[.5, 0, -.25], [0, .5, -.25], [0, 0, 1]])@np.array(projection['K'])).tolist()
        projection['image_size'] = [960, 540]
        sampling = maps(projection, 640)
        products, annotators = [], {}

        def camera(path, eye, target, size, focal):
            cam = UsdGeom.Camera.Define(stage, path)
            cam.AddTransformOp().Set(Gf.Matrix4d().SetLookAt(Gf.Vec3d(*eye), Gf.Vec3d(*target), Gf.Vec3d(0, 0, 1)).GetInverse())
            cam.CreateHorizontalApertureAttr(36.)
            cam.CreateVerticalApertureAttr(36*size[1]/size[0])
            cam.CreateFocalLengthAttr(focal)
            cam.CreateClippingRangeAttr(Gf.Vec2f(.001, 30))
            return cam

        camera('/World/FilmOverview', [1.06, .95, 1.30], [.28, .18, .90], (1000, 820), 32)
        camera('/World/FilmDetail', [.80, .41, .99], [.625, .205, .81], (640, 420), 47)
        for name, path, size in [('overview', '/World/FilmOverview', (1000, 820)),
                                 ('detail', '/World/FilmDetail', (640, 420))]:
            product = rep.create.render_product(path, size)
            products.append(product)
            ann = rep.AnnotatorRegistry.get_annotator('rgb')
            ann.attach(product)
            annotators[name] = ann
        face_cameras = []
        for i in range(6):
            cam = UsdGeom.Camera.Define(stage, f'/World/FilmWrist{i}')
            cam.CreateHorizontalApertureAttr(20.)
            cam.CreateVerticalApertureAttr(20.)
            cam.CreateFocalLengthAttr(10.)
            cam.CreateClippingRangeAttr(Gf.Vec2f(.001, 30))
            face_cameras.append(cam)
            product = rep.create.render_product(str(cam.GetPath()), (640, 640))
            products.append(product)
            for kind, annotator in [('rgb', 'rgb'), ('depth', 'distance_to_camera')]:
                ann = rep.AnnotatorRegistry.get_annotator(annotator)
                ann.attach(product)
                annotators[f'{kind}{i}'] = ann
        rep.settings.set_render_rtx_realtime(antialiasing='DLAA')
        # No timeline playback or physics integration occurs in this renderer.
        all_rows = []
        indices = args.indices if args.indices is not None else list(range(len(trajectory)))
        for count, index in enumerate(indices):
            row = trajectory[index]
            q = {j['name']: packet['initial_qpos'][j['qpos_index']] for j in packet['joints']}
            q.update(zip(names, row['joint_positions']))
            for j in packet['joints']:
                if j['name'].startswith('pad_'):
                    q[j['name']] = row['pad_travel_mm'][int(j['name'].split('_')[-1])]/1000
            transforms = kin.frames(q)
            if row.get('world_from_module') is not None:
                # A free module follows recorded PhysX state, not robot FK.
                transforms[ids['sim_module']]=np.asarray(row['world_from_module'])
                descendants={ids['sim_module']}
                for b in packet['bodies'][1:]:
                    if b['parent'] in descendants:
                        transforms[b['id']]=transforms[b['parent']]@local_pose(b)
                        descendants.add(b['id'])
            for name, path in audit['body_paths'].items():
                if name == 'world':
                    continue
                set_pose(stage.GetPrimAtPath(path), transforms[ids[name]])
            tcp = kin.tcp(q)
            tcp_error = float(np.linalg.norm(tcp[:3, 3]-row['tcp_position']))
            assert tcp_error < 1e-5, tcp_error
            world_from_gl = transforms[wrist['body']]@local_pose(wrist)
            for cam, face in zip(face_cameras, FACES):
                T = world_from_gl.copy()
                T[:3, :3] = world_from_gl[:3, :3]@CV_TO_GL@face@CV_TO_GL
                set_pose(cam.GetPrim(), T)
            # First render warms shader histories; subsequent samples are synchronized.
            for _ in range(4 if count == 0 else 1):
                rep.orchestrator.step(delta_time=0., pause_timeline=True, rt_subframes=args.subframes)
            if count == 0:
                from omni.kit.viewport.utility import get_active_viewport
                viewport = get_active_viewport()
                if viewport:
                    viewport.updates_enabled = False
            frames = args.output/'frames'/f'{index:04d}'
            frames.mkdir(parents=True)
            for name in ['overview', 'detail']:
                rgb = annotators[name].get_data()[:, :, :3].copy()
                assert rgb.std() > 1
                Image.fromarray(rgb).save(frames/f'{name}.jpg', quality=96, subsampling=0)
            cube = [annotators[f'rgb{i}'].get_data()[:, :, :3].copy() for i in range(6)]
            rgb = reproject(cube, sampling)
            Image.fromarray(rgb).save(frames/'wrist.jpg', quality=97, subsampling=0)
            depth = np.full((540, 960), np.inf, np.float32)
            for i, (mask, u, v) in enumerate(sampling):
                raw = annotators[f'depth{i}'].get_data()
                if isinstance(raw, dict):
                    raw = raw['data']
                raw = np.asarray(raw).squeeze()
                depth[mask] = raw[np.rint(v).astype(int), np.rint(u).astype(int)]
            np.savez_compressed(frames/'depth.npz', radial_m=depth)
            world_from_cv = world_from_gl.copy()
            world_from_cv[:3, :3] = world_from_gl[:3, :3]@CV_TO_GL
            state = dict(source_index=index, source_step=row['step'], time_s=row['simulation_time_ns']/1e9,
                         depth_mm=row['insertion_depth_mm'], entry_qualified=row['entry_qualified'],
                         is_success=row['is_success'], lateral_error_mm=row['lateral_error_mm'],
                         alignment_angle_rad=row.get('alignment_angle_rad', 0.),
                         showcase_phase=row.get('showcase_phase'),
                         world_from_module=transforms[ids['sim_module']].tolist(),
                         world_from_socket=transforms[ids['sim_socket']].tolist(),
                         world_from_wrist_cv=world_from_cv.tolist(),
                         tcp_replay_error_m=tcp_error, joint_positions=row['joint_positions'])
            for key in ('grasp_held','grasp_force_proxy_N','grasp_relative_slip_mm','grasp_relative_angle_deg'):
                if key in row:state[key]=row[key]
            (frames/'state.json').write_text(json.dumps(state, indent=2))
            all_rows.append(state)
            if count%10 == 0 or count == len(indices)-1:
                print('CAPTURE', count+1, '/', len(indices), 'depth_mm', round(state['depth_mm'], 3), flush=True)
        stage.GetRootLayer().Export(str(args.output/'final_scene.usdc'))
        assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest() == sha for p, sha in protected.items())
        report = dict(scope='RTX visual replay of one successful recorded PhysX insertion; no new physics or model inference',
                      source_case=str(args.case), source_worker=str(args.worker), transfer=str(args.transfer),
                      captured_indices=indices, frames=len(all_rows), source_total_frames=len(trajectory),
                      source_control_fps=10, projection=projection,
                      source_success=True, initial_depth_mm=trajectory[0]['insertion_depth_mm'],
                      final_depth_mm=trajectory[-1]['insertion_depth_mm'],
                      max_tcp_replay_error_m=max(r['tcp_replay_error_m'] for r in all_rows),
                      gt_geometry=True, network_inference=False, source_sha256=protected,
                      all_protected_sources_unchanged=True, rows=all_rows)
        report['asset_identity']=dict(tool=packet['manifest'].get('wrist_tool_asset'),
            module=(packet['manifest'].get('module_visual_asset') or {}).get('asset_id'),
            contract=packet['manifest'].get('asset_contract','legacy-r10'),
            integration_release=packet['manifest'].get('integration_release'),
            grasp=packet['manifest'].get('grasp'))
        worker_meta=args.worker/'worker_metadata.json'
        if worker_meta.exists():report['physics_execution']=json.loads(worker_meta.read_text())['execution_config']
        (args.output/'capture_report.json').write_text(json.dumps(report, indent=2))
        print('CAPTURE_COMPLETE', str(args.output), flush=True)
    except BaseException as exc:
        failed = True
        traceback.print_exc()
        (args.output/'failure.json').write_text(json.dumps(dict(error=repr(exc), traceback=traceback.format_exc()), indent=2))
    finally:
        app._app.post_quit(1 if failed else 0)
        app.close()


if __name__ == '__main__':
    main()
