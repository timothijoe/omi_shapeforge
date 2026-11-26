"""Reconstruct frozen System1 probes on their source visual meshes.

Run in omi_sim_train; Blender renders the asset views. Original observations,
weights and probe data are read-only. Output must be a new directory.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'src'), str(ROOT.parent/'omi_proj/src')]
from omi_shapeforge.sim.isaac_contact_kinematics import Kinematics, local_pose
from render_system1_paths import references, transform, project

BG = (14, 22, 33)
FG = (232, 240, 248)
MUTED = (154, 173, 190)
COLORS = {'pred': (255, 156, 45), 'gt': (57, 220, 152), 'tip': (204, 141, 255)}


def label(im, xy, value, size=24, color=FG):
    font = ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', size)
    ImageDraw.Draw(im).text(xy, value, font=font, fill=color)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def overlay(im, paths, visibility=None, scale=1):
    """One drawing convention in asset and camera views. Never move path points."""
    d = ImageDraw.Draw(im)
    for key in ('full_gt', 'full_pred', 'gt', 'pred'):
        color = COLORS['pred' if 'pred' in key else 'gt']
        full = key.startswith('full')
        points = np.asarray(paths[key]) * scale
        visible = np.ones(len(points), bool) if visibility is None else np.array(visibility[key])
        distance_so_far = 0.
        for i, (a, b) in enumerate(zip(points[:-1], points[1:])):
            if not np.isfinite([a, b]).all():
                continue
            # Full references and hidden sections are dashed; visible short paths solid.
            dashed = full or not (visible[i] and visible[i+1])
            dist = np.linalg.norm(b-a)
            steps = max(1, int(np.ceil(dist/2)))
            for j in range(steps):
                if dashed and int((distance_so_far+dist*j/steps)/5) % 3 == 2:
                    continue
                x, y = a+(b-a)*j/steps, a+(b-a)*(j+1)/steps
                d.line([tuple(x), tuple(y)], fill=color, width=2 if full else 4)
            distance_so_far += dist
        if not full:
            # The 8 reference samples are marked, with matching endpoint numbers.
            for i, (u, v) in enumerate(points):
                if not (0 <= u < im.width and 0 <= v < im.height):
                    continue
                d.ellipse((u-3, v-3, u+3, v+3), fill=color)
                if i in (0, 7):
                    shift = (8, -25) if key == 'pred' else (8, 5)
                    label(im, (u+shift[0], v+shift[1]), str(i+1), 19, color)
    u, v = np.asarray(paths['tip'])[0]*scale
    if np.isfinite([u, v]).all():
        d.ellipse((u-7, v-7, u+7, v+7), outline=COLORS['tip'], width=3)
    return im


def prepare(a):
    a.output.mkdir(parents=True, exist_ok=False)
    packet = json.loads((a.transfer/'transfer.json').read_text())
    assert sha(a.transfer/'meshes.npz') == packet['meshes_sha256']
    data = np.load(a.probes/'samples.npz', allow_pickle=False)
    report = json.loads((a.probes/'report.json').read_text())
    m = packet['manifest']
    camera = next(c for c in packet['cameras'] if c['name'] == 'wrist_rgb')
    cam = np.diag([1., -1., -1., 1.]) @ np.linalg.inv(local_pose(camera))
    K, D = np.array(m['observation_projection']['K']), np.array(m['observation_projection']['D'])
    module = np.eye(4)
    module[:3, :3] = m['tool_to_module']['rotation']
    module[:3, 3] = m['tool_to_module']['position_m']
    tip = module @ np.array([0, m['leading_tip_y_mm']/1000, 0, 1])
    kin = Kinematics(packet)
    q = {j['name']: packet['initial_qpos'][j['qpos_index']] for j in packet['joints']}
    frames = kin.frames(q)
    tcp_body = next(s['body'] for s in packet['sites'] if s['name'] == 'urdf_tcp_L')
    tcp_inv = np.linalg.inv(frames[tcp_body])
    meshes = np.load(a.transfer/'meshes.npz', allow_pickle=False)
    parts, geometry = [], {}
    for g in packet['geoms']:
        name = g['name']
        if not name.startswith(('wrist_tool_', 'sim_module_', 'sim_socket_')):
            continue
        if g['group'] >= 3 or g['rgba'][3] == 0 or g['kind'] != 7:
            continue
        category = 'socket' if name.startswith('sim_socket_') else 'tool'
        T = local_pose(g) if category == 'socket' else tcp_inv @ frames[g['body']] @ local_pose(g)
        idx = len(parts)
        geometry[f'v{idx}'] = transform(T, meshes[f"v{g['mesh']}"])
        geometry[f'f{idx}'] = meshes[f"f{g['mesh']}"]
        parts.append(dict(name=name, category=category, rgba=g['rgba']))
    np.savez_compressed(a.output/'asset_geometry.npz', **geometry)
    rows = []
    for i in a.cases:
        truth, pred = data['target_socket'][i], data['predicted_socket'][i]
        gp, gf = references(m, truth, tip)
        pp, pf = references(m, pred, tip)
        np.testing.assert_allclose(pp, data['predicted_tip_path'][i], atol=1e-10)
        inverse = np.linalg.inv(truth)
        paths = dict(gt=gp, pred=pp, full_gt=gf, full_pred=pf, tip=tip[None, :3])
        local = {k: transform(inverse, v)*1000 for k, v in paths.items()}
        # Keep the remaining reference near the entrance in the comparison view.
        # The complete uncut path is retained separately in the packet.
        shown = {}
        for k, v in local.items():
            shown[k] = v[v[:, 1] >= m['mouth_y_mm']-6] if k.startswith('full') else v
        projected = {}
        for k, v in shown.items():
            tcp = transform(truth, v/1000)
            uv, valid = project(tcp, cam, K, D)
            uv[~valid] = np.nan
            projected[k] = ((uv+.5)*5-.5).tolist()
        raw = Image.fromarray(data['images'][i, 3:].transpose(1, 2, 0))
        raw.save(a.output/f'case_{i:02d}_wrist_original.png')
        overlay(raw.resize((640, 640), Image.Resampling.LANCZOS), projected).save(a.output/f'case_{i:02d}_wrist.png')
        rows.append(dict(id=i, summary=report['cases'][i], socket_from_tcp=inverse.tolist(),
                         paths_mm={k:v.tolist() for k,v in shown.items()},
                         complete_paths_mm={k:v.tolist() for k,v in local.items()}, wrist_pixels=projected))
    result = dict(parts=parts, cases=rows, mouth_y_mm=m['mouth_y_mm'],
                  channel_width_mm=m['channel_width_mm'], channel_height_mm=m['channel_height_mm'],
                  center_xz_mm=m['nominal_module_center_xz_mm'],
                  source_hashes={str(p):sha(p) for p in [a.transfer/'transfer.json', a.transfer/'meshes.npz', a.probes/'samples.npz', a.probes/'report.json']},
                  source_transfer=str(a.transfer), source_probes=str(a.probes),
                  coordinate_frame='socket local, millimetres; asset source geometry remains unchanged',
                  tool_joint_policy='frozen nominal finger joints from source transfer; recorded socket-relative TCP pose',
                  wrist_projection='original 128px observation; source fisheye K/D and exact ROI sampling; displayed at 5x',
                  scope='frozen predictions; no training or trajectory execution; Blender appearance is illustrative')
    (a.output/'scene_packet.json').write_text(json.dumps(result, indent=2)+'\n')


def compose(folder):
    packet = json.loads((folder/'scene_packet.json').read_text())
    thumbs = []
    for case in packet['cases']:
        i = case['id']
        im = Image.new('RGB', (2304, 1296), BG)
        label(im, (40, 22), 'SYSTEM1  /  实体资产上的路径', 36)
        s = case['summary']
        label(im, (40, 78), f"起点 {i+1}   横向 {s['requested_lateral_mm']:+.0f} mm · 高度 {s['requested_vertical_mm']:+.0f} mm    |    位姿误差 {s['translation_error_mm']:.3f} mm", 23, MUTED)
        for x, title in [(40, '01  三维资产 · 夹爪、模块与插座'), (40, '02  孔口近景 · 同一条三维路径'), (1620, '03  原始腕图 · 同路径鱼眼投影')]:
            label(im, (x, 600 if title.startswith('02') else 130), title, 25)
        for view, pos in [('overview', (40, 176)), ('detail', (40, 646))]:
            base = Image.open(folder/f'case_{i:02d}_{view}.png').convert('RGB')
            proj = json.loads((folder/f'case_{i:02d}_{view}.json').read_text())
            overlay(base, proj['pixels'], proj['visible'])
            bar_mm = 10 if view == 'overview' else 5
            bar_px = bar_mm*base.width/proj['ortho_scale']
            d = ImageDraw.Draw(base)
            d.rounded_rectangle((base.width-180, base.height-60, base.width-12, base.height-12), radius=6, fill=BG)
            end = base.width-30
            d.line((end-bar_px, base.height-25, end, base.height-25), fill=FG, width=3)
            label(base, (base.width-165, base.height-60), f'{bar_mm} mm', 18)
            base.save(folder/f'case_{i:02d}_{view}_annotated.png')
            im.paste(base, pos)
        im.paste(Image.open(folder/f'case_{i:02d}_wrist.png'), (1620, 176))
        label(im, (1620, 836), '原始策略观测为128×128；此处放大5倍', 20, MUTED)
        for j, (txt, color) in enumerate([('橙色：模型预测参考', COLORS['pred']), ('绿色：GT位姿解码参考', COLORS['gt']), ('紫色：当前模块尖端中心', COLORS['tip'])]):
            label(im, (1620, 890+j*45), txt, 24, color)
        label(im, (1620, 1045), '粗线＋圆点：当前8个参考点', 22)
        label(im, (1620, 1080), '细虚线：后续参考（显示到入口后6mm）', 21)
        label(im, (40, 1140), '三维实物遮挡处用虚线透视标注；腕图参考线穿透遮挡。编号1与8在各视图中对应同一点。', 23, MUTED)
        label(im, (40, 1190), '按记录的TCP／插座相对位姿重建，夹指使用原固定开度。冻结预测未执行；三维光照仅用于展示。', 23, MUTED)
        im.save(folder/f'case_{i:02d}_comparison.png')
        thumbs.append(im.resize((1152,648), Image.Resampling.LANCZOS))
    board = Image.new('RGB', (1152*min(3,len(thumbs)),648*((len(thumbs)+2)//3)), BG)
    for j,t in enumerate(thumbs):board.paste(t, ((j%3)*1152,(j//3)*648))
    board.save(folder/'all_cases.jpg', quality=94)
    print('COMPLETED', folder, flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--transfer', type=Path)
    p.add_argument('--probes', type=Path)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--cases', type=int, nargs='+', default=list(range(9)))
    p.add_argument('--blender', default='blender')
    p.add_argument('--compose-only', action='store_true')
    a=p.parse_args()
    if not a.compose_only:
        prepare(a)
        subprocess.run([a.blender, '-b', '-t', '4', '--python', str(Path(__file__).with_name('render_system1_assets_blender.py')), '--', str(a.output)], check=True)
    compose(a.output)


if __name__ == '__main__':main()
