"""Continuous synchronized robot, wrist+GT and task-cloud insertion film.

Consumes capture_insertion_multiview.py outputs. All three panels use the same
saved state; no model predictions or insertion success are synthesized here.
"""
import argparse
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'src'))
from omi_shapeforge.sim.isaac_contact_kinematics import local_pose

BG, FG, MUTED = (10, 17, 27), (237, 244, 249), (142, 164, 183)
CYAN, AMBER, GREEN = (69, 226, 241), (255, 176, 91), (112, 231, 172)
W, H, FPS = 1920, 1080, 30


@lru_cache(maxsize=64)
def font(size, bold=False):
    return ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-'+('Bold' if bold else 'Regular')+'.ttc', size)


def txt(im, xy, s, size=22, color=FG, bold=False):
    ImageDraw.Draw(im).text(xy, s, fill=color, font=font(size, bold))


def prepare_templates(transfer, folder):
    """Sample the EXACT visual meshes used by this replay, in object coordinates."""
    from build_regular_surface_schemes import planar_sample, FOCUS_ROI, subset
    from build_interaction_surface import clipped_mesh
    folder.mkdir(parents=True, exist_ok=False)
    packet = json.loads((transfer/'transfer.json').read_text())
    arrays = np.load(transfer/'meshes.npz')
    manifest = {'source_transfer': str(transfer), 'ordinary_pitch_mm': .8, 'focus_pitch_mm': .2,
                'scope': 'GT visualization templates from current transferred visual geometry, not network outputs',
                'moving_green_accessory_in_target': False, 'models': {}}
    for kind in ['module', 'socket']:
        bid = next(b['id'] for b in packet['bodies'] if b['name'] == 'sim_'+kind)
        triangles, part_ids, colors, names = [], [], [], []
        for g in packet['geoms']:
            if g['body'] != bid or g['group'] >= 3 or not g['rgba'][3] or g['kind'] != 7:
                continue
            T = local_pose(g)
            v = arrays[f"v{g['mesh']}"]@T[:3, :3].T+T[:3, 3]
            tri = v[arrays[f"f{g['mesh']}"]]
            good = np.linalg.norm(np.cross(tri[:, 1]-tri[:, 0], tri[:, 2]-tri[:, 0]), axis=1) > 2e-16
            tri = tri[good]
            triangles.append(tri)
            part_ids.append(np.full(len(tri), len(names), np.int16))
            colors.append(np.tile(g['rgba'][:3], (len(tri), 1)))
            names.append(g['name'])
        mesh = dict(triangles=np.concatenate(triangles), part_id=np.concatenate(part_ids), colors=np.concatenate(colors))
        parents = np.arange(len(mesh['triangles']), dtype=np.int32)
        ordinary, oaudit = planar_sample(mesh, mesh['triangles'], np.tile(np.eye(3), (len(parents), 1, 1)), parents, .0008)
        tri, bary, parent = clipped_mesh(mesh, FOCUS_ROI[kind])
        focus, faudit = planar_sample(mesh, tri, bary, parent, .0002)
        inside = ((ordinary['points_m'] >= FOCUS_ROI[kind][0]-1e-8)&(ordinary['points_m'] <= FOCUS_ROI[kind][1]+1e-8)).all(1)
        ordinary = subset(ordinary, ~inside)
        ordinary['representation_level'] = np.zeros(len(ordinary['points_m']), np.uint8)
        focus['representation_level'] = np.ones(len(focus['points_m']), np.uint8)
        result = {key: np.concatenate([ordinary[key], focus[key]]) for key in ordinary}
        np.savez_compressed(folder/f'{kind}.npz', **result)
        manifest['models'][kind] = dict(count=len(result['points_m']), focus_points=len(focus['points_m']),
                                         parts=names, ordinary_audit=oaudit, focus_audit=faudit)
        print('TEMPLATE', kind, len(result['points_m']), flush=True)
    (folder/'manifest.json').write_text(json.dumps(manifest, indent=2))


class Film:
    def __init__(self, capture, templates):
        self.capture = capture
        self.report = json.loads((capture/'capture_report.json').read_text())
        self.states = self.report['rows']
        self.template_manifest = json.loads((templates/'manifest.json').read_text())
        self.clouds = {kind: dict(np.load(templates/f'{kind}.npz')) for kind in ['module', 'socket']}
        self.socket_cage_parts = [i for i, name in enumerate(self.template_manifest['models']['socket']['parts'])
                                  if 4 <= int(name.split('_')[2]) <= 32
                                  or int(name.split('_')[2]) == 38
                                  or 51 <= int(name.split('_')[2]) <= 60]
        self.K = np.array(self.report['projection']['K'])
        self.D = np.array(self.report['projection']['D'])
        self.base = self.background()

    def background(self):
        im = Image.new('RGB', (W, H), BG)
        txt(im, (40, 24), 'OMI  /  SHAPEFORGE', 24, CYAN, True)
        txt(im, (40, 67), '机器人插接 · 三视图同步', 36, FG, True)
        txt(im, (1327, 34), 'PHYSX 轨迹回放', 20, MUTED)
        txt(im, (1560, 31), 'GT 点云效果演示', 24, AMBER, True)
        d = ImageDraw.Draw(im)
        d.line((40, 132, 1880, 132), fill=(44, 63, 80), width=1)
        txt(im, (40, 148), '01  第三人称 · 机器人与插座', 24, FG, True)
        txt(im, (1080, 148), '02  腕部相机 · 可见 GT 点云叠加', 24, FG, True)
        txt(im, (1080, 640), '03  模块与插座插接部位 · GT 点云', 24, FG, True)
        txt(im, (1080, 956), '青色：模块尖端     橙色：插座孔口', 22, FG)
        txt(im, (1080, 992), '插接部位几何含遮挡表面；本片点云使用 GT，未运行网络估计', 18, MUTED)
        return im

    def paths(self, state):
        return self.capture/'frames'/f"{state['source_index']:04d}"

    @lru_cache(maxsize=3)
    def wrist_overlay(self, idx):
        state = self.states[idx]
        folder = self.paths(state)
        raw = np.array(Image.open(folder/'wrist.jpg').convert('RGB'))
        depth = np.load(folder/'depth.npz')['radial_m']
        cv_from_world = np.linalg.inv(state['world_from_wrist_cv'])
        all_points = []
        visibility = {}
        for kind in ['module', 'socket']:
            a = self.clouds[kind]
            T = cv_from_world@np.array(state['world_from_'+kind])
            xyz = a['points_m']@T[:3, :3].T+T[:3, 3]
            normals = a['normals']@T[:3, :3].T
            face = (normals*xyz).sum(1) < 0
            xyz = xyz[face].astype(float)
            level = a['representation_level'][face]
            uv = cv2.fisheye.projectPoints(xyz[:, None], np.zeros(3), np.zeros(3), self.K, self.D)[0][:, 0]
            pixel = np.rint(uv).astype(int)
            ok = (xyz[:, 2] > .001)&(pixel[:, 0] >= 2)&(pixel[:, 0] < 958)&(pixel[:, 1] >= 2)&(pixel[:, 1] < 538)
            ids = np.flatnonzero(ok)
            pix = pixel[ids]
            radius = np.linalg.norm(xyz[ids], axis=1)
            sensor_depth = depth[pix[:, 1], pix[:, 0]]
            # RTX depth includes the gripper and other scene occluders.
            visible = np.isfinite(sensor_depth)&(np.abs(radius-sensor_depth) < .0012)
            ids = ids[visible]
            visibility[kind] = dict(visible_points=len(ids), focus_points=int((level[ids] > .5).sum()))
            all_points.append((kind, uv[ids], radius[visible], level[ids]))
        layer = raw.copy()
        for kind, uv, z, level in all_points:
            for focus, spacing, color, radius in [(False, 7, (132, 165, 184), 1),
                                                 (True, 2.7, CYAN if kind == 'module' else AMBER, 1)]:
                use = (level > .5) == focus
                q = np.c_[uv[use], z[use]]
                cell = np.floor(q[:, :2]/spacing).astype(int)
                key = cell[:, 1]*400+cell[:, 0]
                order = np.lexsort((q[:, 2], key))
                _, first = np.unique(key[order], return_index=True)
                for u, v in q[order[first], :2]:
                    cv2.circle(layer, (round(u), round(v)), radius, color, -1, cv2.LINE_AA)
        overlay = cv2.addWeighted(layer, .9, raw, .1, 0)
        # Fixed calibrated pixel crop, with an uncropped full-field inset.
        crop = Image.fromarray(overlay).crop((270, 250, 690, 473)).resize((800, 425), Image.Resampling.LANCZOS)
        full = Image.fromarray(raw).resize((224, 126), Image.Resampling.LANCZOS)
        crop.paste(full, (563, 285))
        d = ImageDraw.Draw(crop)
        d.rectangle((562, 284, 787, 411), outline=(108, 132, 150), width=2)
        txt(crop, (575, 288), '完整鱼眼视野', 14, (20, 31, 40), True)
        return crop, visibility

    @lru_cache(maxsize=3)
    def task_cloud(self, idx):
        state = self.states[idx]
        size = (800, 264)
        w, h = size
        target = np.array([0, .006, .002])
        eye = np.array([.17, .11, .14])
        forward = target-eye
        forward /= np.linalg.norm(forward)
        right = np.cross(forward, [0, 0, 1])
        right /= np.linalg.norm(right)
        up = np.cross(right, forward)
        basis = np.stack([right, up, forward], 1)
        scale = 3500
        socket_from_world = np.linalg.inv(state['world_from_socket'])
        im = np.zeros((h, w, 3), np.uint8)
        im[:] = (12, 24, 37)
        for kind in ['socket', 'module']:
            a = self.clouds[kind]
            T = socket_from_world@np.array(state['world_from_'+kind])
            p = a['points_m']@T[:3, :3].T+T[:3, 3]
            n = a['normals']@T[:3, :3].T
            q = (p-target)@basis
            uv = q[:, :2]*[scale, -scale]+[w*.5, h*.45]
            focus = a['representation_level'] > .5
            roi = np.ones(len(p), bool)
            if kind == 'socket':
                # Show the cage/channel, with the module; the full RGB still shows
                # the stand, housing and PCB. This is explicitly a task-part view.
                roi = np.isin(a['part_id'], self.socket_cage_parts)
            facing = (n@(eye-target)) > -.001
            for special, tint in [(False, (82, 115, 140) if kind == 'socket' else (145, 199, 211)),
                                  (True, AMBER if kind == 'socket' else CYAN)]:
                mask = roi&facing&(focus == special)&(uv[:, 0] >= 1)&(uv[:, 0] < w-1)&(uv[:, 1] >= 1)&(uv[:, 1] < h-1)
                qv = np.c_[uv[mask], q[mask, 2]]
                # Point positions remain original; screen cells only select point IDs.
                cell = np.floor(qv[:, :2]/2.5).astype(int)
                key = cell[:, 1]*(int(np.ceil(w/2.5))+2)+cell[:, 0]
                order = np.lexsort((qv[:, 2], key))
                _, first = np.unique(key[order], return_index=True)
                pts = np.rint(qv[order[first], :2]).astype(int)
                layer = np.zeros_like(im)
                layer[pts[:, 1], pts[:, 0]] = tint
                if special:
                    layer = cv2.dilate(layer, np.ones((2, 2), np.uint8))
                mask = layer.max(2) > 0
                im[mask] = layer[mask]
        halo = cv2.GaussianBlur(im, (0, 0), 1.8)
        im = cv2.addWeighted(im, 1., halo, .13, 0)
        return Image.fromarray(im)

    @lru_cache(maxsize=3)
    def frame(self, idx):
        state = self.states[idx]
        folder = self.paths(state)
        im = self.base.copy()
        im.paste(Image.open(folder/'overview.jpg'), (40, 194))
        # Simultaneous close-up makes the small insertion readable without losing the robot view.
        detail = Image.open(folder/'detail.jpg').resize((448, 294), Image.Resampling.LANCZOS)
        im.paste(detail, (576, 692))
        ImageDraw.Draw(im).rectangle((574, 690, 1026, 988), outline=(92, 126, 146), width=2)
        box = Image.new('RGB', (448, 31), (13, 24, 35))
        txt(box, (10, 1), '同步第三人称近景', 18, MUTED)
        im.paste(box, (576, 692))
        overlay, _ = self.wrist_overlay(idx)
        im.paste(overlay, (1080, 194))
        im.paste(self.task_cloud(idx), (1080, 686))
        depth = state['depth_mm']
        if state['is_success']:
            phase, color = '完成落座', GREEN
        elif depth < 0:
            phase, color = '孔口前 · 对准', CYAN
        elif depth < 5:
            phase, color = '进入孔口', CYAN
        else:
            phase, color = '持续插入', AMBER
        # Lightweight overlay stays out of the central insertion scene.
        banner = Image.new('RGB', (468, 90), (14, 25, 37))
        txt(banner, (18, 8), phase, 28, color, True)
        txt(banner, (18, 52), f"深度 {depth:6.2f} mm    ·    仿真时间 {state['time_s']:5.1f}s", 20, FG)
        im.paste(banner, (58, 212))
        progress = np.clip((depth+5)/(self.report['final_depth_mm']+5), 0, 1)
        d = ImageDraw.Draw(im)
        d.rectangle((40, 1034, 1880, 1039), fill=(43, 61, 78))
        d.rectangle((40, 1034, 40+1840*progress, 1039), fill=color)
        txt(im, (40, 1047), '同一轨迹 · 同一物理状态 · 三视图同步', 17, MUTED)
        txt(im, (1500, 1047), '规则控制 / 仿真回放 / GT', 17, MUTED)
        return im


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--capture', type=Path, required=True)
    p.add_argument('--templates', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--preview', action='store_true')
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    report = json.loads((args.capture/'capture_report.json').read_text())
    if not args.templates.exists():
        prepare_templates(Path(report['transfer']), args.templates)
    film = Film(args.capture, args.templates)
    for i in sorted({0, len(film.states)//2, len(film.states)-1}):
        film.frame(i).save(args.output/f'preview_{film.states[i]["source_index"]:04d}.png')
    if args.preview:
        print('PREVIEW_COMPLETE', args.output, flush=True)
        return
    assert len(film.states) == report['source_total_frames']
    assert [r['source_index'] for r in film.states] == list(range(len(film.states)))
    target = args.output/'robot_insertion_gt_multiview_1080p.mp4'
    encoder = subprocess.Popen(['ffmpeg', '-v', 'error', '-n', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
                                '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-', '-an', '-c:v', 'libx264',
                                '-preset', 'fast', '-threads', '6', '-crf', '18', '-pix_fmt', 'yuv420p',
                                '-movflags', '+faststart', str(target)], stdin=subprocess.PIPE)
    mapping = []
    # Brief endpoint holds; every recorded control state in between is included.
    schedule = [0]*45+[i for i in range(len(film.states)) for _ in range(3)]+[len(film.states)-1]*75
    for frame, index in enumerate(schedule):
        encoder.stdin.write(film.frame(index).tobytes())
        mapping.append(dict(video_frame=frame, source_index=film.states[index]['source_index'],
                            source_step=film.states[index]['source_step'], simulation_time_s=film.states[index]['time_s']))
        if frame%90 == 0:
            print('ENCODE', frame, '/', len(schedule), flush=True)
    encoder.stdin.close()
    if encoder.wait():
        raise RuntimeError('Video encoding failed')
    manifest = dict(video=str(target), dimensions=[W, H], fps=FPS, frame_count=len(schedule),
                    duration_seconds=len(schedule)/FPS, capture=str(args.capture), templates=str(args.templates),
                    all_control_states_included=True, source_control_fps=10, source_playback_speed=1,
                    network_inference=False, pointcloud_source='ground truth poses and current exact visual mesh templates',
                    three_views_synchronized=True, wrist_occlusion='RTX radial depth; tolerance 1.2mm',
                    wrist_full_field_inset=True, wrist_display_crop=[270, 250, 690, 473],
                    cloud_view='module and socket cage/channel GT, including occluded surfaces; support/housing/PCB excluded from task viewport',
                    socket_task_part_ids=film.socket_cage_parts,
                    source_success=report['source_success'], frame_map=mapping)
    (args.output/'film_manifest.json').write_text(json.dumps(manifest, indent=2))
    print('FILM_COMPLETE', target, flush=True)


if __name__ == '__main__':
    main()
