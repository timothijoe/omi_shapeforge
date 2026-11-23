"""Actuated insertion/withdrawal and negative controls for the NEW sim asset."""
import argparse
import json
from pathlib import Path

import mujoco
import numpy as np


def validate(asset_dir, output, *, x_offset_mm=0., yaw_deg=0., locked=False, timestep=.0002, render=False):
    asset_dir, output = Path(asset_dir), Path(output)
    output.mkdir(parents=True, exist_ok=False)
    manifest = json.loads((asset_dir / "asset_manifest.json").read_text())
    model = mujoco.MjModel.from_xml_path(str(asset_dir / "scene.xml"))
    model.opt.timestep = timestep
    model.body_pos[model.body("sim_module").id, 0] += x_offset_mm / 1000
    angle = np.deg2rad(yaw_deg) / 2
    model.body_quat[model.body("sim_module").id] = [np.cos(angle), 0, 0, np.sin(angle)]
    pad_joints = [model.joint(f"pad_slide_{i}").id for i in range(7)]
    pad_q = model.jnt_qposadr[pad_joints]
    rest_gaps = np.asarray(manifest.get("pad_rest_static_gap_mm", [.4] * len(pad_q)), dtype=float) / 1000
    if locked:
        # Lock the travel using joint limits; leave every contact enabled.
        # Avoid an enormous explicit spring, which would confound this control
        # with numerical stiffness rather than lack of compliance.
        model.jnt_range[pad_joints] = [0., 1e-9]
    q = model.jnt_qposadr[model.joint("insertion").id]
    data = mujoco.MjData(model)
    start = manifest["start_depth_mm"]
    push = (manifest["shoulder_depth_mm"] + 1. - start) / 1000
    speed = .01
    ramp = push / speed
    duration = ramp * 2 + 1.5
    rows, max_penetration, pad_contacts, static_pad_contacts = [], 0., 0, 0
    minimum_floor_gap = np.inf
    worst_contact = None
    peak_pad = np.zeros(7)
    max_depth, max_hold_depth = -np.inf, -np.inf
    frames = []
    renderer = mujoco.Renderer(model, height=600, width=900) if render else None
    try:
        for step in range(round(duration / timestep)):
            t = data.time
            target = min(push, speed * t) if t < ramp + .75 else max(0., push - speed * (t - ramp - .75))
            data.ctrl[0] = target
            mujoco.mj_step(model, data)
            if not np.isfinite(data.qpos).all():
                raise RuntimeError("nonfinite contact simulation")
            depth = float(data.qpos[q] * 1000 + start)
            max_depth = max(max_depth, depth)
            if ramp < t < ramp + .75:
                max_hold_depth = max(max_hold_depth, depth)
            peak_pad = np.maximum(peak_pad, data.qpos[pad_q])
            minimum_floor_gap = min(minimum_floor_gap, float(np.min(rest_gaps - data.qpos[pad_q])))
            for c in data.contact:
                names = [model.geom(int(i)).name for i in c.geom]
                if -c.dist * 1000 > max_penetration:
                    max_penetration = float(-c.dist * 1000)
                    worst_contact=dict(time=float(t),depth_mm=depth,names=names,position_mm=(c.pos*1000).tolist(),
                                       pad_displacement_mm=(data.qpos[pad_q]*1000).tolist())
                if any(n.startswith("pad_contact") for n in names):
                    if any(n.startswith("sim_module") for n in names):
                        pad_contacts += 1
                    elif any(n.startswith("sim_socket") for n in names):
                        static_pad_contacts += 1
            if step % round(.02/timestep) == 0:
                rows.append(dict(time=float(t), depth_mm=depth, target_depth_mm=float(target*1000+start),
                    drive_force_N=float(data.actuator_force[0]), pad_displacement_mm=(data.qpos[pad_q]*1000).tolist()))
                if renderer is not None and len(rows) % 5 == 0:
                    cam = mujoco.MjvCamera();cam.lookat[:] = [-.005,-.012,0]
                    cam.distance,cam.azimuth,cam.elevation=.18,125,-25
                    opt=mujoco.MjvOption();opt.geomgroup[3:]=0
                    renderer.update_scene(data,camera=cam,scene_option=opt)
                    frames.append(renderer.render().copy())
        mujoco.mj_forward(model,data)
        final_depth=float(data.qpos[q]*1000+start)
        report=dict(asset_id=manifest["asset_id"],x_offset_mm=x_offset_mm,yaw_deg=yaw_deg,locked=locked,timestep=timestep,
            max_depth_mm=max_depth,seated_depth_mm=max_hold_depth,expected_shoulder_mm=manifest["shoulder_depth_mm"],
            reached_shoulder=abs(max_hold_depth-manifest["shoulder_depth_mm"])<.05,
            withdrew_to_start=abs(final_depth-start)<.05,final_depth_mm=final_depth,
            peak_pad_travel_mm=(peak_pad*1000).tolist(),final_pad_travel_mm=(data.qpos[pad_q]*1000).tolist(),
            pad_module_contact_samples=pad_contacts,pad_socket_contact_samples=static_pad_contacts,
            minimum_floor_gap_mm=minimum_floor_gap*1000,maximum_penetration_mm=max_penetration,
            static_clearance_method="conservative rest-gap minus pad travel; legacy fallback .4mm",
            worst_contact=worst_contact,
            real_elasticity_calibrated=False,rows=rows)
        report['accepted_local_cycle'] = bool(report['reached_shoulder'] and report['withdrew_to_start'] and
            max_penetration < .05 and minimum_floor_gap > .000025 and np.max(np.abs(data.qpos[pad_q])) < .00001 and pad_contacts > 0)
        (output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
        if frames:
            import imageio.v2 as imageio
            imageio.mimsave(output/'cycle.gif',frames,duration=100,loop=0)
            imageio.imwrite(output/'preview.png',frames[len(frames)//2])
        print(json.dumps({k:v for k,v in report.items() if k!='rows'}),flush=True)
        return report
    finally:
        if renderer is not None:renderer.close()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--asset-dir',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--x-offset-mm',type=float,default=0.);p.add_argument('--yaw-deg',type=float,default=0.)
    p.add_argument('--locked',action='store_true');p.add_argument('--render',action='store_true')
    p.add_argument('--timestep',type=float,default=.0002)
    a=p.parse_args();validate(a.asset_dir,a.output,x_offset_mm=a.x_offset_mm,yaw_deg=a.yaw_deg,locked=a.locked,render=a.render,timestep=a.timestep)


if __name__=='__main__':main()
