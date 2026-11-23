"""Derive a scene with the inactive right arm extended horizontally outboard."""
import argparse,hashlib,json,shutil
from pathlib import Path
import mujoco
import numpy as np


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    scene=a.source/'scene.xml';source_hash=hashlib.sha256(scene.read_bytes()).hexdigest()
    manifest=json.loads((a.source/'robot_manifest.json').read_text());m=mujoco.MjModel.from_xml_path(str(scene));d=mujoco.MjData(m)
    d.qpos[:]=manifest['initial_qpos'];mujoco.mj_forward(m,d)
    left_before=d.xpos[m.body('TCP_Link_L').id].copy();module_before=d.xpos[m.body('sim_module').id].copy()
    cam=m.camera('wrist_rgb').id;camera_before=d.cam_xpos[cam].copy();camera_rotation_before=d.cam_xmat[cam].copy()
    previous={f'Arm_R{i}_Joint':float(d.joint(f'Arm_R{i}_Joint').qpos[0]) for i in range(1,8)}
    for name in previous:
        assert m.joint(name).range[0]<=0<=m.joint(name).range[1]
        d.joint(name).qpos[0]=0.
    mujoco.mj_forward(m,d)
    np.testing.assert_array_equal(d.xpos[m.body('TCP_Link_L').id],left_before)
    np.testing.assert_array_equal(d.xpos[m.body('sim_module').id],module_before)
    np.testing.assert_array_equal(d.cam_xpos[cam],camera_before)
    np.testing.assert_array_equal(d.cam_xmat[cam],camera_rotation_before)
    points={n:d.xpos[m.body(n).id].tolist() for n in ['Link1_R','Link2_R','Link3_R','Link4_R','Link5_R','Link7_R','TCP_Link_R']}
    span=float(np.ptp([v[2] for v in points.values()]))
    assert span<1e-5,'right arm is not horizontal in world Z'
    shutil.copy2(scene,a.output/'scene.xml')
    manifest.update(initial_qpos=d.qpos.tolist(),scene=str((a.output/'scene.xml').resolve()),
        scene_sha256=source_hash,inactive_right_arm=dict(joint_positions_rad={n:0. for n in previous},
        previous_positions_rad=previous,role='horizontal outboard parking, not a hardware motion trajectory',
        world_joint_points_m=points,world_height_spread_m=span))
    (a.output/'robot_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    validation=dict(source_scene=str(scene),source_scene_sha256=source_hash,scene_geometry_unchanged=True,
        left_tcp_unchanged=True,module_unchanged=True,wrist_extrinsics_unchanged=True,
        right_arm_world_points_m=points,horizontal_height_spread_m=span,
        transition_trajectory_validated=False)
    (a.output/'parking_validation.json').write_text(json.dumps(validation,indent=2)+'\n')
    assert hashlib.sha256(scene.read_bytes()).hexdigest()==source_hash
    print(json.dumps(validation),flush=True)


if __name__=='__main__':main()
