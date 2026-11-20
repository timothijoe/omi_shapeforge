"""Decode workflow artifacts in the workflow environment, without model inference."""
import argparse
import json
from pathlib import Path
import platform
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from omi_shapeforge.runner import digest, read_json, write_json


def require(condition, message):
    if not condition:
        raise ValueError(message)


def inspect(manifest_path):
    import numpy as np
    import imageio.v3 as imageio

    record = read_json(manifest_path)
    output = manifest_path.parent / 'backend'
    inputs = {item['id']: Path(item['path']) for item in record['inputs']}
    report = read_json(output / 'report.json')
    workflow = record['workflow']
    versions = {'python': platform.python_version(), 'numpy': np.__version__}

    def array(path):
        result = np.load(path, allow_pickle=False)
        require(np.isfinite(result).all(), f'Non-finite array: {path.name}')
        return result

    def image(name):
        result = imageio.imread(output / name)
        require(result.ndim == 3 and result.shape[2] in (3, 4) and result.size > 0,
                f'Expected a nonempty color image: {name}')
        return result

    if workflow == 'smoke.stereo':
        import open3d as o3d
        left, right = [imageio.imread(inputs[key]) for key in ('left', 'right')]
        require(left.shape == right.shape and left.ndim == 3 and left.shape[2] == 3,
                'Stereo inputs must have matching RGB shape')
        require(report['image_shape'] == list(left.shape), 'Reported image shape differs from inputs')
        parameters = record['parameters']
        require(report['iterations'] == parameters['iterations'] and report['scale'] == parameters['scale'],
                'Stereo parameters differ from report')
        lines = inputs['intrinsics'].read_text().splitlines()
        k = np.array([float(x) for x in lines[0].split()]).reshape(3, 3)
        baseline = float(lines[1])
        require(np.isfinite(k).all() and np.isfinite(baseline) and baseline > 0
                and k[0, 0] > 0 and k[1, 1] > 0, 'Invalid intrinsics or baseline')
        disparity, depth = array(output / 'disparity.npy'), array(output / 'depth_meter.npy')
        require(disparity.shape == depth.shape == left.shape[:2] and (depth >= 0).all(),
                'Depth/disparity shape or sign invalid')
        _, xx = np.indices(depth.shape)
        valid = (disparity > 0) & (xx - disparity >= 0)
        # The stereo backend stores K in float32; use the same precision here.
        expected = np.zeros_like(depth)
        expected[valid] = np.float32(k[0, 0]) * baseline / disparity[valid]
        require(np.allclose(depth, expected, rtol=2e-5, atol=1e-7), 'Depth disagrees with disparity/calibration')
        cloud = o3d.io.read_point_cloud(str(output / 'cloud.ply'))
        points = np.asarray(cloud.points)
        require(points.ndim == 2 and points.shape[1] == 3 and np.isfinite(points).all(), 'Invalid PLY coordinates')
        require(len(points) == report['point_count'], 'PLY count differs from report')
        require(image('vis.png').shape[:2] == (left.shape[0], 2 * left.shape[1]), 'Preview shape mismatch')
        require(report['checkpoint_sha256'] == digest(inputs['checkpoint']), 'Checkpoint identity mismatch')
        for key in ('left', 'right'):
            require(report[key + '_sha256'] == digest(inputs[key]), 'Input image identity mismatch')
        accepted = len(points) > 0
        expected_text = 'Finite official sample outputs and nonempty point cloud'
        observed = json.dumps({'point_count': len(points), 'image_shape': list(left.shape)})
        versions.update(open3d=o3d.__version__, torch=report['torch'], cuda=report['torch_cuda'])
    elif workflow == 'smoke.bundlesdf':
        matches = array(output / 'loftr_matches.npy')
        require(matches.ndim == 2 and matches.shape[1] == 5, 'LoFTR array must be Nx5')
        require(len(matches) == report['loftr_matches'], 'LoFTR count differs from report')
        require(image('loftr_matches.jpg').shape[:2] == (448, 1280), 'LoFTR image dimensions differ')
        require(((matches[:, [0, 2]] >= 0) & (matches[:, [0, 2]] < 640)).all()
                and ((matches[:, [1, 3]] >= 0) & (matches[:, [1, 3]] < 448)).all(),
                'LoFTR coordinates outside resized images')
        require(((matches[:, 4] >= 0) & (matches[:, 4] <= 1)).all(), 'Invalid LoFTR confidences')
        keys = ('hash_grid_forward_backward', 'so3_roundtrip',
                'pytorch3d_cuda_knn_forward_backward', 'warp_cuda_kernel')
        accepted = (len(matches) >= 10 and all(report[key] == 'passed' for key in keys)
                    and report['kaolin_octree_bytes'] > 0 and report['yaml_entries'] > 0
                    and np.allclose(report['cuda_ray_samples'], [[1, 1.5, 3.25, 3.75]]))
        expected_text = 'At least 10 finite matches; C++/CUDA/geometric component assertions pass'
        observed = json.dumps({'matches': len(matches), 'component_checks': {k: report[k] for k in keys}})
        versions.update(torch=report['torch'], cuda=report['cuda'], kaolin=report['kaolin_version'],
                        warp=report['warp_version'])
    elif workflow == 'simulation.mujoco':
        import mujoco
        dependencies = read_json(inputs['scene_dependencies'])
        for item in dependencies['files']:
            path = Path(item['path'])
            require(path.stat().st_size == item['size_bytes'] and digest(path) == item['sha256'],
                    f'MJCF dependency changed: {path}')
        require(report['scene_sha256'] == digest(inputs['scene']), 'Scene identity mismatch')
        require(report['runner_sha256'] == record['sources'][-1]['entrypoint_sha256'], 'Scene runner identity mismatch')
        require(report['steps'] == record['parameters']['steps'], 'Simulation steps differ from request')
        require(report['physical_accuracy_validated'] is False, 'Prototype cannot claim calibrated physics')
        model = mujoco.MjModel.from_xml_path(str(inputs['scene']))
        require(model.nq % 7 == 0 and model.nv == model.nq // 7 * 6,
                'This workflow accepts only the generated free-body optical prototype')
        count = model.nq // 7
        require(count > 0 and report['modules'] == count, 'Module count differs from model')
        with np.load(output / 'trajectory.npz', allow_pickle=False) as arrays:
            initial, final, velocity = [arrays[key].copy() for key in ('initial_qpos', 'final_qpos', 'final_qvel')]
        require(initial.shape == final.shape == (model.nq,) and velocity.shape == (model.nv,), 'State dimensions differ')
        require(all(np.isfinite(x).all() for x in (initial, final, velocity)), 'Non-finite simulated state')
        require(np.allclose(report['initial_qpos'], initial) and np.allclose(report['final_qpos'], final),
                'Report and saved trajectory disagree')
        samples = read_json(output / 'samples.json')
        require(bool(samples), 'Missing state samples')
        times = [s['time_s'] for s in samples]
        require(np.isfinite(times).all() and np.all(np.diff(times) > 0), 'Sample times must increase')
        require(all(np.asarray(s['qpos']).shape == (model.nq,) and np.isfinite(s['qpos']).all()
                    for s in samples), 'Invalid sampled states')
        require(np.isclose(report['simulated_seconds'], model.opt.timestep * report['steps']), 'Simulation duration mismatch')
        image('initial.png'); image('settled.png')
        data = mujoco.MjData(model); data.qpos[:] = final; data.qvel[:] = velocity; mujoco.mj_forward(model, data)
        contacts = {int(i) for c in data.contact[:data.ncon] for i in c.geom}
        bottoms, drops, touched = [], [], []
        for i in range(count):
            geom = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, f'module_collision_{i}')
            require(geom >= 0, 'Missing named collision proxy')
            bottoms.append(float(data.geom_xpos[geom, 2] - np.abs(data.geom_xmat[geom].reshape(3, 3)[2]) @ model.geom_size[geom]))
            drops.append(float(initial[i*7+2] - final[i*7+2])); touched.append(geom in contacts)
        max_speed = float(np.max(np.abs(velocity)))
        require(np.isclose(max_speed, report['max_final_speed']), 'Final speed differs from saved state')
        accepted = min(bottoms) >= -.001 and min(drops) > .01 and all(touched) and max_speed <= .05
        expected_text = 'Each drop >0.01 m, proxy bottom >=-0.001 m, final contact, max(abs(qvel)) <=0.05'
        observed = json.dumps({'bottom_z_m': bottoms, 'drop_m': drops, 'final_contact': touched,
                               'max_abs_qvel_mixed_units': max_speed})
        versions['mujoco'] = mujoco.__version__
    else:
        raise ValueError(f'Unsupported workflow: {workflow}')
    return {'valid': True, 'accepted': bool(accepted), 'content': 'Decoded files and workflow consistency checks passed',
            'expected': expected_text, 'observed': observed, 'versions': versions}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = inspect(args.manifest)
    except Exception as exc:
        result = {'valid': False, 'accepted': False, 'content': f'{type(exc).__name__}: {exc}',
                  'expected': 'Valid workflow artifacts', 'observed': 'Not evaluated',
                  'versions': {'python': platform.python_version()}}
    write_json(args.manifest.parent / 'backend/inspection.json', result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
