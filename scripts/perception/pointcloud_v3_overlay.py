"""Re-fit current V3 rigid body on the hash-verified annotated portable cloud.

This deliberately reuses a user-confirmed ROI, not a general object detector.
The complete 15-part V3 is displayed; handle parts do not drive body fitting.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

import numpy as np
import open3d as o3d


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--html', type=Path, required=True)
    p.add_argument('--package', type=Path, required=True)
    p.add_argument('--model-inputs', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--face-prior', choices=['unconfirmed', 'toward-camera', 'away-camera'],
                   default='unconfirmed', help='Explicit visual prior; not inferred pose ground truth')
    a = p.parse_args()
    pkg = a.package
    config = json.loads((pkg/'config/target.json').read_text())
    if digest(a.html) != config['source_html_sha256']:
        raise ValueError('Different point cloud: manually establish a new ROI first')
    text = a.html.read_text()
    match = re.search(r'const data=new Float32Array\(\[(.*?)\]\)', text, re.S)
    cloud = np.fromstring(match[1], sep=',', dtype=np.float32).reshape(-1, 4)
    packaged = np.load(pkg/'data/pointcloud.npz')
    assert np.array_equal(cloud[:, :3], packaged['xyz'])
    assert np.array_equal(cloud[:, 3], packaged['gray'])
    a.output.mkdir(parents=True, exist_ok=False)
    np.savez_compressed(a.output/'cloud.npz', xyz=cloud[:, :3], gray=cloud[:, 3])
    manifest = json.loads((a.model_inputs/'manifest.json').read_text())
    assert digest(Path(manifest['module']['source'])) == manifest['module']['source_sha256']
    # The portable matching subset excludes the unobserved interior, pull handle,
    # handle seat and open seams. Export it afresh from the CURRENT V3 parts.
    body_ids = {'000.npz', '001.npz', '002.npz', '003.npz', '004.npz',
                '006.npz', '008.npz', '010.npz', '014.npz'}
    selected = {'body': [], 'full': []}
    provenance = []
    for record in manifest['module']['parts']:
        path = a.model_inputs/'module'/record['file']
        with np.load(path) as data:
            v, f = data['vertices']/1000., data['faces'].astype(np.int32)
        selected['full'].append((v, f))
        if record['file'] in body_ids:
            selected['body'].append((v, f))
        provenance.append({'file': str(path), 'sha256': digest(path),
                           'name': record['name'], 'used_for_fit': record['file'] in body_ids})
    meshes = {}
    for name, parts in selected.items():
        vs, fs, offset = [], [], 0
        for v, f in parts:
            vs.append(v); fs.append(f+offset); offset += len(v)
        meshes[name] = (np.concatenate(vs), np.concatenate(fs))
        np.savez_compressed(a.output/f'{name}_mesh.npz', vertices=meshes[name][0], triangles=meshes[name][1])
    run = a.output/'registration'
    command = [sys.executable, str(pkg/'scripts/portable_match.py'), '--output', str(run),
               '--cloud', str(a.output/'cloud.npz'), '--mesh', str(a.output/'body_mesh.npz')]
    subprocess.run(command, check=True)
    fits_path = run/'fit/confirmed_target_results.json'
    fit = json.loads(fits_path.read_text())
    (run/'fit/unconstrained_results.json').write_text(json.dumps(fit, indent=2))
    # Context prior: insertion tip points toward the socket (upper in annotation),
    # handle toward the gripper. Do not let a tiny residual reverse head and tail.
    candidates = fit['distinct_candidates']
    def candidate_key(c):
        transform = np.array(c['T_camera_from_model'])
        facing = np.dot(transform[:3, 2], -transform[:3, 3]) > 0
        wrong_face = (a.face_prior != 'unconfirmed' and
                      facing != (a.face_prior == 'toward-camera'))
        return (transform[1, 1] < 0, wrong_face, c['training_score'])
    candidates.sort(key=candidate_key)
    best = candidates[0]
    T = np.array(best['T_camera_from_model'])
    fit['best'] = best
    fit['selection_prior'] = 'Handle toward gripper, insertion tip toward socket; face remains ambiguous'
    if a.face_prior != 'unconfirmed':
        fit['selection_prior'] = ('Handle toward gripper, insertion tip toward socket; '
                                  f'user-supplied groove-face prior: {a.face_prior}')
    fits_path.write_text(json.dumps(fit, indent=2))
    roi = np.load(pkg/'data/confirmed_target_roi.npz')
    v, f = meshes['body']
    body = o3d.geometry.TriangleMesh(o3d.utility.Vector3dVector(v), o3d.utility.Vector3iVector(f))
    scene = o3d.t.geometry.RaycastingScene(nthreads=4)
    scene.add_triangles(o3d.t.geometry.TriangleMesh.from_legacy(body))
    def distances(q):
        local = (q-T[:3, 3]) @ T[:3, :3]
        return scene.compute_distance(o3d.core.Tensor(local.astype(np.float32))).numpy()*1000
    check = distances(roi['xyz'][~roi['fit']])
    raw = distances(cloud[roi['raw_selection_indices'], :3])
    checks = {'raw_selected_points': len(raw), 'raw_surface_median_mm': float(np.median(raw)),
              'raw_surface_p90_mm': float(np.quantile(raw, .9)), 'filtered_points': len(roi['xyz']),
              'check_points': len(check), 'check_surface_median_mm': float(np.median(check)),
              'check_surface_p90_mm': float(np.quantile(check, .9)), 'absolute_pose_accuracy_validated': False}
    (run/'qa/surface_checks.json').write_text(json.dumps(checks, indent=2))
    fit['heldout_median_mm'] = checks['check_surface_median_mm']
    fit['heldout_p90_mm'] = checks['check_surface_p90_mm']
    all_d = distances(roi['xyz'])
    fit['all_points_median_mm'] = float(np.median(all_d))
    fit['all_points_p90_mm'] = float(np.quantile(all_d, .9))
    fits_path.write_text(json.dumps(fit, indent=2))
    summary = {'status': 'conditional_v3_fit_on_previously_confirmed_roi',
               'input_html': str(a.html), 'input_sha256': digest(a.html),
               'cloud_points': len(cloud), 'T_camera_from_model': T.tolist(),
               'coordinate_frame': 'Original HTML metric XYZ; acquisition-camera optical convention assumed, no robot transform',
               'translation_unit': 'm', 'model_source': manifest['module']['source'],
               'model_sha256': manifest['module']['source_sha256'], 'parts': provenance,
               'fit_part_count': len(selected['body']), 'display_part_count': len(selected['full']),
               'model_scale_changed': False, 'model_deformed': False,
               'selection_prior': fit['selection_prior'], 'pose_orientation_unique': False,
               'face_prior': a.face_prior,
               'checks': checks, 'absolute_pose_accuracy_validated': False,
               'note': 'Check points excluded from ICP, but ROI and initialization use all points; not independent pose truth.'}
    (run/'fit/selected_candidate.json').write_text(json.dumps(summary, indent=2))
    for name, (v, f) in meshes.items():
        transformed = v @ T[:3, :3].T + T[:3, 3]
        mesh = o3d.geometry.TriangleMesh(o3d.utility.Vector3dVector(transformed), o3d.utility.Vector3iVector(f))
        o3d.io.write_triangle_mesh(str(run/'delivery'/f'matched_v3_{name}.ply'), mesh)
    # Replace the generic body's original best-pose export with selected-pose body.
    (run/'delivery/matched_model_confirmed_region.ply').write_bytes((run/'delivery/matched_v3_body.ply').read_bytes())
    subprocess.run([sys.executable, str(pkg/'scripts/render_overlay.py'), '--run', str(run),
                    '--cloud', str(a.output/'cloud.npz'), '--mesh', str(a.output/'full_mesh.npz')], check=True)
    viewer = run/'overlay.html'
    html = viewer.read_text()
    html = html.replace('修正版：按用户圈选光模块叠加 mesh', 'V3 光模块与原始点云配准')
    html = html.replace('修正版：你圈选的光模块＋固定 mesh', '当前 V3 光模块 · 点云配准预览')
    html = html.replace('橙色：已有 mesh 的刚性主体', '橙色：完整 V3 mesh（含拉手）')
    html = html.replace('目标位置已按黄色圈选修正，残差不等于真实位姿精度；可按已知头尾／正反先验切换姿态。',
                        '9 个主体部件参与配准，完整显示 15 个部件。默认插入端朝插座、拉手朝夹爪；正反面仍有歧义，残差不等于位姿精度。')
    html = html.replace('拉手端朝底座', '拉手端朝夹爪').replace('拉手端朝框架', '反向候选：拉手端朝插座')
    if a.face_prior != 'unconfirmed':
        face_label = '朝向采集相机' if a.face_prior == 'toward-camera' else '背向采集相机'
        html = html.replace('正反面仍有歧义，残差不等于位姿精度。',
                            f'按用户正反面纠正，默认槽面{face_label}；残差不等于位姿精度。')
    html = html.replace('模型中心（米）', '模型原点（米）').replace('width:100vw', 'width:100%')
    # Focus initially while keeping the surrounding socket and gripper visible.
    html = html.replace('window.onresize=render;markROI();render();',
                        "window.onresize=render;markROI();center=cases[0].focus.slice();distance=.24;render();")
    viewer.write_text(html)
    summary['viewer'] = str(viewer)
    (a.output/'report.json').write_text(json.dumps(summary, indent=2))
    print(json.dumps({'viewer': str(viewer), 'checks': checks, 'translation_m': T[:3,3].tolist()}, indent=2))


if __name__ == '__main__':
    main()
