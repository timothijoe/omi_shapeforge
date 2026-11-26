"""Render recorded autonomous policy joint states; never integrate new physics."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import traceback


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run', type=Path, required=True)
    p.add_argument('--stride', type=int, default=3)
    p.add_argument('--preview', action='store_true')
    p.add_argument('--wrist', action='store_true', help='Render the original wrist camera extrinsics and full fisheye projection')
    p.add_argument('--wrist-face-size', type=int, default=1024)
    p.add_argument('--wrist-context-face-size', type=int, help='Optional smaller peripheral cube faces; focus faces retain full resolution')
    p.add_argument('--wrist-context-scale', type=float, choices=[.5,1.], default=1., help='Scale the full-field context image; focus rays remain at full resolution')
    a = p.parse_args()
    root = Path(__file__).resolve().parents[2]
    sys.path[:0] = [str(root/'src'), '/data/shapeforge/runtime/envs/isaac_contact_support']
    selection = json.loads((a.run/'selection.json').read_text())
    out = a.run/('preview' if a.preview else 'capture')
    out.mkdir(exist_ok=False)
    for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
        os.environ[key] = '1'
    sys.argv = [sys.argv[0]]
    from isaacsim import SimulationApp
    isaac = Path('/data/isaac-sim-5.1.0')
    extra = ['--/app/extensions/registryEnabled=false']
    for directory in ('exts', 'extscache', 'kit/exts', 'kit/extscore'):
        extra += ['--ext-folder', str(isaac/directory)]
    app = SimulationApp(dict(headless=True, limit_cpu_threads=4, multi_gpu=False, extra_args=extra),
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
        from omi_shapeforge.sim.socket_pose import relocate_socket_manifest

        context = omni.usd.get_context(); context.new_stage(); stage = context.get_stage()
        packet, audit = build(stage, Path(selection['transfer']), out)
        apply_recipe(stage, packet, audit, Path(selection['transfer']), 'refined')
        for prim in stage.Traverse():
            if prim.HasAPI(UsdPhysics.RigidBodyAPI):
                UsdPhysics.RigidBodyAPI(prim).CreateRigidBodyEnabledAttr(False)
        kin = Kinematics(packet)
        ids = {b['name']: b['id'] for b in packet['bodies']}
        socket_ids = {ids['sim_socket']}
        for b in packet['bodies']:
            if b['parent'] in socket_ids: socket_ids.add(b['id'])
        annotators = {}; products = []
        cameras = [
            ('detail', [.88, .47, 1.015], [.625, .203, .807], (900, 540), 46),
            ('overview', [1.06, .95, 1.30], [.28, .18, .90], (440, 330), 30),
        ]
        for name, eye, target, size, focal in cameras:
            cam = UsdGeom.Camera.Define(stage, '/World/PolicyFilm_'+name)
            cam.AddTransformOp().Set(Gf.Matrix4d().SetLookAt(Gf.Vec3d(*eye), Gf.Vec3d(*target), Gf.Vec3d(0, 0, 1)).GetInverse())
            cam.CreateHorizontalApertureAttr(36.)
            cam.CreateVerticalApertureAttr(36*size[1]/size[0])
            cam.CreateFocalLengthAttr(focal)
            cam.CreateClippingRangeAttr(Gf.Vec2f(.001, 30))
            product = rep.create.render_product(str(cam.GetPath()), size); products.append(product)
            ann = rep.AnnotatorRegistry.get_annotator('rgb'); ann.attach(product); annotators[name] = ann
        wrist_cameras=[]; wrist_annotators=[]; projection=None
        if a.wrist:
            from omi_shapeforge.sim.wrist_fisheye import FACES, CV_TO_GL, maps, reproject
            wrist=next(c for c in packet['cameras'] if c['name']=='wrist_rgb')
            projection=packet['manifest']['observation_projection']
            scale=a.wrist_context_scale
            context_projection=dict(projection,K=(np.array([[scale,0.,(scale-1)/2],[0.,scale,(scale-1)/2],[0.,0.,1.]])@np.asarray(projection['K'])).tolist(),
                image_size=[round(n*scale) for n in projection['image_size']])
            sampling=maps(context_projection,a.wrist_face_size)
            focus_sampling=None
            if selection.get('wrist_crop'):
                x0,y0,x1,y1=selection['wrist_crop'];sx=900/(x1-x0);sy=540/(y1-y0)
                focus_projection=dict(projection,K=(np.array([[sx,0.,-sx*x0],[0.,sy,-sy*y0],[0.,0.,1.]])@np.asarray(projection['K'])).tolist(),image_size=[900,540])
                focus_sampling=maps(focus_projection,a.wrist_face_size)
            face_sizes=[a.wrist_face_size]*6
            if a.wrist_context_face_size and focus_sampling is not None:
                low_sampling=maps(context_projection,a.wrist_context_face_size)
                for i in range(6):
                    if not np.any(focus_sampling[i][0]):
                        face_sizes[i]=a.wrist_context_face_size;sampling[i]=low_sampling[i]
            for i in range(6):
                cam=UsdGeom.Camera.Define(stage,f'/World/PolicyFilmWrist{i}')
                cam.CreateHorizontalApertureAttr(20.);cam.CreateVerticalApertureAttr(20.)
                cam.CreateFocalLengthAttr(10.);cam.CreateClippingRangeAttr(Gf.Vec2f(.001,30))
                product=rep.create.render_product(str(cam.GetPath()),(face_sizes[i],face_sizes[i]));products.append(product)
                ann=rep.AnnotatorRegistry.get_annotator('rgb');ann.attach(product)
                wrist_cameras.append(cam);wrist_annotators.append(ann)
        rep.settings.set_render_rtx_realtime(antialiasing='DLAA')
        report = dict(scope='recorded PhysX state visual replay; no new physics, interpolation or inference',
                      stride=a.stride, source_control_fps=10, cameras=cameras, modes={})
        if a.wrist:
            report['wrist']=dict(projection=projection,context_projection=context_projection,face_size=a.wrist_face_size,face_sizes=face_sizes,camera=wrist,
                focus_crop=selection.get('wrist_crop'),focus_projection=focus_projection if focus_sampling is not None else None,
                geometry='original wrist-camera attachment; no camera relocation or target tracking',
                scope='higher-resolution re-render for inspection; not original policy input pixels')
        count = 0
        for mode, source in selection['modes'].items():
            path = Path(source['states'])
            assert hashlib.sha256(path.read_bytes()).hexdigest() == source['states_sha256']
            rows = json.loads(path.read_text())
            names = json.loads((Path(source['worker'])/'kinematics_check.json').read_text())['joint_names']
            indices = sorted(set([0, len(rows)-1] if a.preview else [*range(0, len(rows), a.stride), len(rows)-1]))
            errors = []; rotations = []; captured = []
            for index in indices:
                row = rows[index]
                assert row['teacher_requests'] == 0
                q = {j['name']: packet['initial_qpos'][j['qpos_index']] for j in packet['joints']}
                q.update(zip(names, row['joint_positions']))
                for j in packet['joints']:
                    if j['name'].startswith('pad_'):
                        q[j['name']] = row['pad_travel_mm'][int(j['name'].split('_')[-1])]/1000
                transforms = kin.frames(q)
                _, delta = relocate_socket_manifest(packet['manifest'], row['socket_pose'])
                for index_body in socket_ids: transforms[index_body] = delta@transforms[index_body]
                for name, body_path in audit['body_paths'].items():
                    if name != 'world': set_pose(stage.GetPrimAtPath(body_path), transforms[ids[name]])
                tcp = kin.tcp(q)
                error = float(np.linalg.norm(tcp[:3, 3]-row['tcp_position']))
                rotation = float(np.max(np.abs(tcp[:3, :3]-row['tcp_rotation'])))
                assert error < 1e-5 and rotation < 1e-5, (error, rotation)
                errors.append(error); rotations.append(rotation)
                if a.wrist:
                    world_from_gl=transforms[wrist['body']]@local_pose(wrist)
                    for cam,face in zip(wrist_cameras,FACES):
                        t=world_from_gl.copy();t[:3,:3]=world_from_gl[:3,:3]@CV_TO_GL@face@CV_TO_GL
                        set_pose(cam.GetPrim(),t)
                for _ in range(4 if count == 0 else 1):
                    rep.orchestrator.step(delta_time=0., pause_timeline=True, rt_subframes=3)
                if count == 0:
                    from omni.kit.viewport.utility import get_active_viewport
                    viewport = get_active_viewport()
                    if viewport: viewport.updates_enabled = False
                frame = out/mode/f'{row["step"]:04d}'; frame.mkdir(parents=True)
                for name, ann in annotators.items():
                    rgb = ann.get_data()[:, :, :3].copy(); assert rgb.std() > 1
                    Image.fromarray(rgb).save(frame/f'{name}.jpg', quality=95, subsampling=0)
                if a.wrist:
                    cube=[ann.get_data()[:,:,:3].copy() for ann in wrist_annotators]
                    rgb=reproject(cube,sampling)
                    assert rgb.std()>1
                    Image.fromarray(rgb).save(frame/'wrist.jpg',quality=97,subsampling=0)
                    if focus_sampling is not None:
                        Image.fromarray(reproject(cube,focus_sampling)).save(frame/'wrist_focus.jpg',quality=97,subsampling=0)
                    world_from_cv=world_from_gl.copy();world_from_cv[:3,:3]=world_from_gl[:3,:3]@CV_TO_GL
                    (frame/'wrist_pose.json').write_text(json.dumps(dict(source_step=row['step'],
                        world_from_wrist_cv=world_from_cv.tolist(),tcp_from_wrist_cv=(np.linalg.inv(tcp)@world_from_cv).tolist())))
                captured.append(row['step']); count += 1
                if count % 20 == 0 or index == indices[-1]:
                    print('CAPTURE', mode, row['step'], '/', len(rows), flush=True)
            report['modes'][mode] = dict(steps=captured, source_steps=rows[-1]['step'], source_frames=len(rows),
                max_tcp_error_m=max(errors), max_rotation_matrix_error=max(rotations),
                source_sha256=source['states_sha256'], result=source['evaluation'])
        (out/'capture_report.json').write_text(json.dumps(report, indent=2))
    except BaseException as exc:
        failed = True; traceback.print_exc()
        (out/'failure.json').write_text(json.dumps(dict(error=repr(exc), traceback=traceback.format_exc())))
    finally:
        app._app.post_quit(1 if failed else 0); app.close()
    if failed: raise SystemExit(1)


if __name__ == '__main__': main()
