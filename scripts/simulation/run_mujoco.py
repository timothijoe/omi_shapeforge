"""Load the generated optical scene, run a bounded settling test and render it."""
import argparse
import hashlib
import json
import os
from pathlib import Path

os.environ.setdefault('MUJOCO_GL', 'egl')
import imageio.v2 as imageio
import mujoco
import numpy as np


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--scene', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--steps', type=int, default=240)
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    model = mujoco.MjModel.from_xml_path(str(args.scene.resolve()))
    model.vis.headlight.ambient[:] = 0.4
    model.vis.headlight.diffuse[:] = 0.8
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    initial = data.qpos.copy()
    count = model.nq // 7
    camera = mujoco.MjvCamera()
    camera.lookat[:] = [0, 0.015, 0.01]
    camera.distance = 0.24 * max(1, np.sqrt(count))
    camera.azimuth = 130
    camera.elevation = -35
    renderer = mujoco.Renderer(model, height=720, width=960)
    try:
        renderer.update_scene(data, camera=camera)
        imageio.imwrite(args.output / 'initial.png', renderer.render())
        samples = []
        for step in range(args.steps):
            mujoco.mj_step(model, data)
            if not np.isfinite(data.qpos).all() or not np.isfinite(data.qvel).all():
                raise RuntimeError('Non-finite simulated state')
            if step % 12 == 0:
                samples.append({'time_s': float(data.time), 'qpos': data.qpos.tolist()})
        renderer.update_scene(data, camera=camera)
        imageio.imwrite(args.output / 'settled.png', renderer.render())
    finally:
        renderer.close()
    contacts = []
    for contact in data.contact[:data.ncon]:
        contacts.append([mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, int(i))
                         for i in contact.geom])
    halfsize = None
    for index in range(count):
        geom = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, f'module_collision_{index}')
        halfsize = model.geom_size[geom]
        center = data.geom_xpos[geom]
        rotation = data.geom_xmat[geom].reshape(3, 3)
        if center[2] - np.abs(rotation[2]) @ halfsize < -0.001:
            raise RuntimeError('Module penetrated the table')
        if data.qpos[index * 7 + 2] >= initial[index * 7 + 2] - 0.01:
            raise RuntimeError('Module did not fall under gravity')
        if not any(f'module_collision_{index}' in pair for pair in contacts):
            raise RuntimeError('Module has no final contact')
    if np.max(np.abs(data.qvel)) > 0.05:
        raise RuntimeError('Object did not settle')
    np.savez_compressed(args.output / 'trajectory.npz', initial_qpos=initial,
                        final_qpos=data.qpos, final_qvel=data.qvel)
    report = {'status': 'passed_mujoco_load_step_render_and_settle',
              'scene': str(args.scene.resolve()),
              'scene_sha256': hashlib.file_digest(args.scene.open('rb'), 'sha256').hexdigest(),
              'runner_sha256': hashlib.file_digest(Path(__file__).open('rb'), 'sha256').hexdigest(),
              'mujoco_version': mujoco.__version__, 'modules': count,
              'steps': args.steps, 'simulated_seconds': float(data.time),
              'initial_qpos': initial.tolist(), 'final_qpos': data.qpos.tolist(),
              'max_final_speed': float(np.max(np.abs(data.qvel))), 'final_contacts': contacts,
              'collision_model': 'Rigid bounding box; groove and flexible-handle contacts are not represented.',
              'physical_accuracy_validated': False}
    (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    (args.output / 'samples.json').write_text(json.dumps(samples, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
