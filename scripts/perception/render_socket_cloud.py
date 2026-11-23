"""Render independently fitted socket and module, excluding movable handle from fitting."""
import argparse
import base64
import json
from pathlib import Path
import numpy as np
import open3d as o3d


def encode(a):
    return base64.b64encode(np.ascontiguousarray(a, dtype='<f4').tobytes()).decode()


def combine(parts):
    vertices, faces, offset = [], [], 0
    for v, f in parts:
        vertices.append(v); faces.append(f+offset); offset += len(v)
    return np.concatenate(vertices), np.concatenate(faces)


def buffers(parts):
    v, f = combine(parts)
    tri = v[f]
    normals = np.cross(tri[:, 1]-tri[:, 0], tri[:, 2]-tri[:, 0])
    normals /= np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-12)
    adjacency = {}
    for i, face in enumerate(f):
        for a, b in zip(face, np.roll(face, -1)):
            adjacency.setdefault(tuple(sorted((int(a), int(b)))), []).append(i)
    edges = np.array([edge for edge, fs in adjacency.items()
                      if len(fs) != 2 or normals[fs[0]] @ normals[fs[1]] < np.cos(.35)])
    mesh = np.c_[tri.reshape(-1, 3), np.repeat(normals, 3, axis=0)]
    lines = np.c_[v[edges].reshape(-1, 3), np.zeros((len(edges)*2, 3))]
    return {'mesh': encode(mesh), 'lines': encode(lines)}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run', type=Path, required=True)
    p.add_argument('--socket-inputs', type=Path, required=True)
    p.add_argument('--module-inputs', type=Path, required=True)
    a = p.parse_args()
    report = json.loads((a.run/'report.json').read_text())
    cloud = np.load(a.run/'projection.npz')
    roi = np.load(a.run/'socket_roi_refined.npz')
    groups = []
    socket_parts = []
    for kind, directory in [('socket', a.socket_inputs), ('module', a.module_inputs)]:
        manifest = json.loads((directory/'manifest.json').read_text())[kind]
        divided = {'main': [], 'extra': []}
        for rec in manifest['parts']:
            data = np.load(directory/kind/rec['file'])
            part = (data['vertices']/1000., data['faces'])
            extra = rec.get('group') == 'stand' if kind == 'socket' else rec['file'] in ['009.npz', '011.npz']
            divided['extra' if extra else 'main'].append(part)
            if kind == 'socket':
                socket_parts.append(part)
        for name, parts in divided.items():
            toggle = kind if name == 'main' else ('stand' if kind == 'socket' else 'handle')
            color = [.15, .8, 1.] if kind == 'socket' else [1., .65, .2]
            if toggle == 'handle': color = [.25, .85, .35]
            groups.append({'object': kind, 'toggle': toggle, 'color': color, **buffers(parts)})
    v, f = combine(socket_parts)
    T = np.array(report['socket_T_cloud_from_model'])
    mesh = o3d.geometry.TriangleMesh(o3d.utility.Vector3dVector(v@T[:3, :3].T+T[:3, 3]), o3d.utility.Vector3iVector(f))
    o3d.io.write_triangle_mesh(str(a.run/'matched_socket_full.ply'), mesh)
    candidates = json.loads((a.run/'socket_candidates_refined.json').read_text())['distinct'][:4]
    marks = np.zeros(len(cloud['xyz']), dtype=np.float32)
    marks[roi['indices']] = 1
    focus = (roi['xyz'].mean(0)+np.array(report['module_T_cloud_from_model'])[:3, 3])/2
    payload = {'cloud': encode(np.c_[cloud['xyz'], cloud['gray']]), 'roi': encode(marks),
               'groups': groups, 'candidates': candidates, 'module_T': report['module_T_cloud_from_model'],
               'focus': focus.tolist(), 'scene_center': np.median(cloud['xyz'], axis=0).tolist()}
    html = Path(__file__).with_name('socket_cloud_viewer.html').read_text()
    metrics = f"插座检查点 P90 {report['check']['p90_mm']:.1f} mm；全部原始选区 P90 {report['all_raw_roi']['p90_mm']:.1f} mm，不代表真实位姿精度。"
    html = html.replace('__PAYLOAD__', json.dumps(payload, separators=(',', ':'))).replace('__METRICS__', metrics)
    out = a.run/'overlay.html'
    if out.exists(): raise FileExistsError(out)
    out.write_text(html)
    assert np.array_equal(np.frombuffer(base64.b64decode(payload['cloud']), dtype='<f4').reshape(-1, 4)[:, :3], cloud['xyz'].astype(np.float32))
    print(out)


if __name__ == '__main__':
    main()
