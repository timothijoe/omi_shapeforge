"""Continuous misalignment/alignment/insertion film in the requested reference style.

On-screen terminology is "几何位姿估计". The manifest explicitly records that
this edition uses simulation poses as the stand-in, not learned predictions.
"""
import argparse
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import subprocess

import cv2
import numpy as np
from PIL import Image, ImageDraw

from render_insertion_multiview import Film as BaseFilm, txt, font

PRESENTATION_PATH = Path(__file__).resolve().parents[2]/'configs/pointcloud_presentation.json'
PRESENTATION = json.loads(PRESENTATION_PATH.read_text())
BG = (11, 22, 29)
FG = (233, 242, 247)
MUTED = (151, 174, 186)
GREEN = tuple(PRESENTATION['rgb']['socket_mouth'])
GRAY = tuple(PRESENTATION['rgb']['support_ordinary'])
MODULE_GRAY = (174, 187, 202)
AMBER = (255, 189, 105)
MODULE = tuple(PRESENTATION['rgb']['module_tip'])
MODULE_TONE = (170, 139, 108)
SOCKET_TONE = (112, 158, 139)
MODULE_NEUTRAL = tuple(PRESENTATION['rgb']['module_ordinary'])
SOCKET_NEUTRAL = tuple(PRESENTATION['rgb']['socket_upper_ordinary'])
W, H, FPS = 1920, 1080, 30


class Film(BaseFilm):
    def __init__(self, capture, templates, playback_rate=3,
                 palette=PRESENTATION['default_palette'], point_style=PRESENTATION['default_point_style'],
                 wrist_overlay=None):
        if playback_rate not in (1, 3):
            raise ValueError('Use 1x or 3x to retain every source state at 30fps')
        self.playback_rate = playback_rate
        self.palette = palette
        if point_style not in ('legacy', 'layered'):
            raise ValueError('Unknown point style')
        self.point_style = point_style
        self.wrist_overlay = wrist_overlay or PRESENTATION['display'].get('wrist_overlay', 'all')
        if self.wrist_overlay not in ('all', 'focus-only'):
            raise ValueError('Unknown wrist overlay scope')
        super().__init__(capture, templates)

    def point_regions(self, kind):
        """Stable source-part labels: support, upper socket assembly, module."""
        a = self.clouds[kind]
        if kind == 'module':
            return np.full(len(a['points_m']), 2, np.uint8)
        # Stand mesh, its four pillars and pillar washers stay neutral. The
        # board, cage and board-mounted components form the upper assembly.
        support_numbers = {0, 1, 2, 3, 39, *range(111, 119)}
        names = self.template_manifest['models']['socket']['parts']
        support = [i for i, name in enumerate(names)
                   if int(name.split('_')[2]) in support_numbers]
        return np.where(np.isin(a['part_id'], support), 0, 1).astype(np.uint8)

    def ordinary_colors(self):
        if self.palette == 'component-grays':
            return [GRAY, SOCKET_NEUTRAL, MODULE_NEUTRAL]
        return [GRAY, SOCKET_TONE, MODULE_TONE] if self.palette == 'component-tones' else [GRAY, GRAY, MODULE_GRAY]

    def background(self):
        im = Image.new('RGB', (W, H), BG)
        brand_color = MUTED if self.palette == 'component-grays' else (105, 212, 193)
        txt(im, (40, 26), 'OMI  /  SHAPEFORGE', 18, brand_color, True)
        if self.report.get('asset_identity',{}).get('tool')=='WG-DAIMON-LOGO-r15':
            txt(im,(360,28),'WG-r15 · OM-r08',18,MUTED)
            if self.report['asset_identity'].get('contract')=='wva01-closed-reference-fixture-v1':
                txt(im,(690,28),'固定夹持插入演示',17,MUTED)
        txt(im, (40, 62), '从未对准到完整插入', 36, FG, True)
        if self.point_style == 'layered':
            txt(im, (42, 119), '分层点云 · 普通 0.8 mm / 重点 0.2 mm · 同一点径', 18, MUTED)
        d = ImageDraw.Draw(im)
        for x, number, label in [(36, '01', '机器人第三人称'), (660, '02', '腕部相机 · 点云叠加'),
                                  (1284, '03', '几何位姿估计')]:
            d.rounded_rectangle((x, 166, x+600, 1000), radius=20,
                                fill=(16, 30, 39), outline=(43, 62, 75), width=1)
            txt(im, (x+24, 185), number, 20, brand_color, True)
            txt(im, (x+76, 181), label, 26, FG, True)
            d.line((x+20, 226, x+580, 226), fill=(39, 58, 70))
        if self.wrist_overlay == 'focus-only':
            txt(im, (684, 935), '腕部视角 · 仅叠加关键点云', 22, FG)
            txt(im, (684, 971), '橙色尖端 / 绿色孔口 · 其余保留原图', 18, MUTED)
        else:
            txt(im, (684, 935), '腕部视角 · 可见表面点云', 22, FG)
            txt(im, (684, 971), 'RGB 画面与三维几何同步', 18, MUTED)
        if self.palette in ('component-tones', 'component-grays'):
            support, socket, module = self.ordinary_colors()
            for x, color, label in [(1308, module, '光模块'), (1498, socket, '插座上部'), (1688, support, '底座')]:
                d.ellipse((x, 943, x+9, 952), fill=color)
                txt(im, (x+20, 931), label, 18, color)
            for x, color, label in [(1308, MODULE, '模块尖端'), (1540, GREEN, '插座孔口')]:
                d.ellipse((x, 978, x+9, 987), fill=color)
                txt(im, (x+20, 966), label, 18, color)
        else:
            for x, color, label in [(1308, GRAY, '普通表面'), (1498, MODULE, '模块尖端'), (1688, GREEN, '孔口')]:
                d.ellipse((x, 948, x+9, 957), fill=color)
                txt(im, (x+20, 936), label, 19, color)
        txt(im, (40, 1025), f'{self.playback_rate}× 连续回放', 20, MUTED)
        txt(im, (1538, 1028), '同一轨迹 · 三视图同步', 18, MUTED)
        return im

    @staticmethod
    def paste_view(canvas, image, position):
        mask = Image.new('L', image.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, image.width-1, image.height-1), radius=10, fill=255)
        canvas.paste(image, position, mask)

    @lru_cache(maxsize=3)
    def projection(self, idx):
        state = self.states[idx]
        folder = self.paths(state)
        raw = np.array(Image.open(folder/'wrist.jpg').convert('RGB'))
        depth = np.load(folder/'depth.npz')['radial_m']
        camera_from_world = np.linalg.inv(state['world_from_wrist_cv'])
        layer = raw.copy()
        visible_counts = {}
        projected = []
        for kind in ['socket', 'module']:
            a = self.clouds[kind]
            T = camera_from_world@np.array(state['world_from_'+kind])
            xyz = a['points_m']@T[:3, :3].T+T[:3, 3]
            n = a['normals']@T[:3, :3].T
            take = (n*xyz).sum(1) < 0
            p = xyz[take].astype(float)
            level = a['representation_level'][take]
            region = self.point_regions(kind)[take]
            uv = cv2.fisheye.projectPoints(p[:, None], np.zeros(3), np.zeros(3), self.K, self.D)[0][:, 0]
            pix = np.rint(uv).astype(int)
            ok = (p[:, 2] > .001)&(pix[:, 0] >= 2)&(pix[:, 0] < 958)&(pix[:, 1] >= 2)&(pix[:, 1] < 538)
            ids = np.flatnonzero(ok)
            sensor = depth[pix[ids, 1], pix[ids, 0]]
            radial = np.linalg.norm(p[ids], axis=1)
            ids = ids[np.isfinite(sensor)&(np.abs(sensor-radial) < .0012)]
            visible_counts[kind] = dict(total=len(ids), focus=int((level[ids] > .5).sum()))
            focus_color = MODULE if kind == 'module' else GREEN
            if self.point_style == 'layered':
                # Map original sensor pixel centers into the FINAL wrist panel.
                # Both layers use one output pixel, with no screen-grid thinning.
                xy = np.rint((uv[ids]-[360, 260]+.5)*[568/240, 663/280]-.5).astype(int)
                colors = np.asarray(self.ordinary_colors(), np.uint8)[region[ids]].copy()
                colors[level[ids] > .5] = focus_color
                projected.append((xy, np.linalg.norm(p[ids], axis=1), colors, level[ids] > .5))
                continue
            groups = [(6, color, 0, (level[ids] <= .5)&(region[ids] == r))
                      for r, color in enumerate(self.ordinary_colors())]
            if self.wrist_overlay == 'focus-only':
                groups = []
            groups.append((2.5, focus_color, 1, level[ids] > .5))
            for spacing, color, radius, selected in groups:
                select = ids[selected]
                points = np.c_[uv[select], np.linalg.norm(p[select], axis=1)]
                cell = np.floor(points[:, :2]/spacing).astype(int)
                key = cell[:, 1]*(int(np.ceil(960/spacing))+2)+cell[:, 0]
                order = np.lexsort((points[:, 2], key))
                _, first = np.unique(key[order], return_index=True)
                for u, v in points[order[first], :2]:
                    cv2.circle(layer, (round(u), round(v)), radius, color, -1, cv2.LINE_AA)
        if self.point_style == 'layered':
            output = np.array(Image.fromarray(raw).crop((360, 260, 600, 540)).resize((568, 663), Image.Resampling.LANCZOS))
            xy = np.concatenate([a[0] for a in projected])
            z = np.concatenate([a[1] for a in projected])
            colors = np.concatenate([a[2] for a in projected])
            focused = np.concatenate([a[3] for a in projected])
            valid = (xy[:, 0] >= 0)&(xy[:, 0] < 568)&(xy[:, 1] >= 0)&(xy[:, 1] < 663)
            xy, z, colors, focused = xy[valid], z[valid], colors[valid], focused[valid]
            key = xy[:, 1]*568+xy[:, 0]
            depth_buffer = np.full(568*663, np.inf)
            np.minimum.at(depth_buffer, key, z)
            nearest = z <= depth_buffer[key]+PRESENTATION['display']['depth_tolerance_m']
            # Keep all visible geometry in the depth buffer: hiding ordinary
            # markers must not expose focus points behind ordinary surfaces.
            if self.wrist_overlay == 'focus-only':
                nearest &= focused
            output[xy[nearest, 1], xy[nearest, 0]] = colors[nearest]
            return Image.fromarray(output), visible_counts
        overlay = cv2.addWeighted(layer, .92, raw, .08, 0)
        crop = Image.fromarray(overlay).crop((360, 260, 600, 540)).resize((568, 663), Image.Resampling.LANCZOS)
        return crop, visible_counts

    @lru_cache(maxsize=3)
    def complete_cloud(self, idx):
        """Full fixed assembly and module, with camera-facing depth-tested points."""
        state = self.states[idx]
        w, h = 568, 666
        target = np.array([-.002, .018, -.047])
        eye = target+np.array([.07, .29, .205])
        forward = target-eye
        forward /= np.linalg.norm(forward)
        right = np.cross(forward, [0, 0, 1])
        right /= np.linalg.norm(right)
        up = np.cross(right, forward)
        basis = np.stack([right, up, forward], 1)
        scale = 3000
        reference = np.linalg.inv(state['world_from_socket'])
        pts, norms, levels, objects, regions = [], [], [], [], []
        for kind in ['socket', 'module']:
            a = self.clouds[kind]
            T = reference@np.array(state['world_from_'+kind])
            pts.append(a['points_m']@T[:3, :3].T+T[:3, 3])
            norms.append(a['normals']@T[:3, :3].T)
            levels.append(a['representation_level'])
            objects.append(np.full(len(a['points_m']), kind == 'module', bool))
            regions.append(self.point_regions(kind))
        p = np.concatenate(pts)
        n = np.concatenate(norms)
        focused = np.concatenate(levels) > .5
        module = np.concatenate(objects)
        region = np.concatenate(regions)
        q = (p-target)@basis
        uv = np.rint(q[:, :2]*[scale, -scale]+[w*.5, h*.55]).astype(int)
        facing = (n@(eye-target)) > -.001 if self.point_style == 'legacy' else np.ones(len(p), bool)
        valid = facing&(uv[:, 0] >= 1)&(uv[:, 0] < w-1)&(uv[:, 1] >= 1)&(uv[:, 1] < h-1)
        uv, z, focus, module = uv[valid], q[valid, 2], focused[valid], module[valid]
        region = region[valid]
        key = uv[:, 1]*w+uv[:, 0]
        depth = np.full(h*w, np.inf)
        np.minimum.at(depth, key, z)
        tolerance = .0006 if self.point_style == 'legacy' else PRESENTATION['display']['depth_tolerance_m']
        visible = z <= depth[key]+tolerance
        layer = np.zeros((h, w, 3), np.uint8)
        groups = [(visible&(~focus)&(region == r), color) for r, color in enumerate(self.ordinary_colors())]
        groups.extend([(visible&focus&(~module), GREEN), (visible&focus&module, MODULE)])
        for chosen, color in groups:
            xy = uv[chosen]
            temp = np.zeros_like(layer)
            temp[xy[:, 1], xy[:, 0]] = color
            # The reference viewer uses finite circular point sprites, rather than
            # the one-pixel dark sparse rendering in the earlier process film.
            if self.point_style == 'legacy':
                temp = cv2.dilate(temp, np.ones((2, 2), np.uint8))
            mask = temp.max(2) > 0
            layer[mask] = temp[mask]
        # Hidden focus surfaces retain a subdued signal within the complete prior.
        # The source and this visualization convention are explicit in the manifest.
        if self.point_style == 'legacy':
            hidden_layer = np.zeros_like(layer)
            for is_module, color in [(False, (29, 98, 48)), (True, (111, 66, 28))]:
                xy = uv[(~visible)&focus&(module == is_module)]
                hidden_layer[xy[:, 1], xy[:, 0]] = color
            layer = np.maximum(layer, hidden_layer)
        image = np.zeros_like(layer)
        image[:] = (7, 20, 25)
        mask = layer.max(2) > 0
        image[mask] = layer[mask]
        return Image.fromarray(image)

    def stage(self, state):
        phase = state['showcase_phase']
        alignment_color = MUTED if self.palette == 'component-grays' else AMBER
        if state['is_success']:
            return 2, '完成落座', GREEN
        if phase == 'misaligned':
            return 0, '尚未对准', alignment_color
        if phase == 'aligning':
            return 1, '调整位置与姿态', alignment_color
        if state['depth_mm'] < 0:
            return 1, '已对准 · 接近孔口', GREEN
        return 2, '保持对准 · 连续插入', GREEN

    @lru_cache(maxsize=3)
    def frame(self, idx):
        state = self.states[idx]
        folder = self.paths(state)
        im = self.base.copy()
        overview = Image.open(folder/'overview.jpg').crop((150, 0, 850, 820)).resize((568, 665), Image.Resampling.LANCZOS)
        self.paste_view(im, overview, (52, 242))
        overlay, _ = self.projection(idx)
        self.paste_view(im, overlay, (676, 243))
        self.paste_view(im, self.complete_cloud(idx), (1300, 242))
        stage, label, color = self.stage(state)
        for i, name in enumerate(['未对准', '对准', '插入']):
            x = 1006+i*292
            active = i == stage
            d = ImageDraw.Draw(im)
            d.rounded_rectangle((x, 55, x+264, 100), 10, fill=(29, 63, 58) if active else (24, 39, 47),
                                outline=color if active else (50, 70, 81), width=2)
            txt(im, (x+74, 59), name, 22, color if active else MUTED, active)
        txt(im, (60, 934), label, 24, color, True)
        # These are task-state measurements, not an estimated network error score.
        txt(im, (60, 971), f"横向偏差 {state['lateral_error_mm']:.2f} mm   深度 {state['depth_mm']:.2f} mm", 18, MUTED)
        d = ImageDraw.Draw(im)
        d.line((300, 1044, 1460, 1044), fill=(44, 63, 76), width=3)
        d.line((300, 1044, 300+1160*idx/max(1, len(self.states)-1), 1044), fill=color, width=3)
        return im


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--capture', type=Path, required=True)
    p.add_argument('--templates', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--preview', action='store_true')
    p.add_argument('--playback-rate', type=int, choices=[1, 3], default=3)
    p.add_argument('--palette', choices=['neutral', 'component-tones', 'component-grays'], default=PRESENTATION['default_palette'])
    p.add_argument('--point-style', choices=['legacy', 'layered'], default=PRESENTATION['default_point_style'])
    p.add_argument('--wrist-overlay', choices=['all', 'focus-only'],
                   default=PRESENTATION['display'].get('wrist_overlay', 'all'))
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=True)
    film = Film(a.capture, a.templates, a.playback_rate, a.palette, a.point_style, a.wrist_overlay)
    aligned = next(i for i, s in enumerate(film.states) if s['showcase_phase'] == 'aligned')
    indices = sorted({0, aligned, len(film.states)//2, len(film.states)-1})
    for i in indices:
        film.frame(i).save(a.output/f'preview_{i:04d}.png')
    if a.preview:
        print('PREVIEW_COMPLETE', a.output, flush=True)
        return
    assert len(film.states) == film.report['source_total_frames']
    assert [s['source_index'] for s in film.states] == list(range(len(film.states)))
    assert film.states[0]['lateral_error_mm'] > 10
    assert film.states[0]['alignment_angle_rad'] > np.deg2rad(2)
    assert film.states[aligned]['lateral_error_mm'] < .1
    assert film.states[aligned]['depth_mm'] < 0 and film.states[-1]['is_success']
    target = a.output/'alignment_insertion_geometry_pose_1080p.mp4'
    repeats = FPS//(film.report['source_control_fps']*a.playback_rate)
    schedule = [0]*36+[i for i in range(len(film.states)) for _ in range(repeats)]+[len(film.states)-1]*36
    enc = subprocess.Popen(['ffmpeg', '-v', 'error', '-n', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '1920x1080',
                            '-r', str(FPS), '-i', '-', '-an', '-c:v', 'libx264', '-threads', '6', '-preset', 'fast',
                            '-crf', '18', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(target)], stdin=subprocess.PIPE)
    frame_map = []
    for frame, index in enumerate(schedule):
        enc.stdin.write(film.frame(index).tobytes())
        s = film.states[index]
        frame_map.append(dict(video_frame=frame, source_index=index, source_step=s['source_step'], phase=s['showcase_phase']))
        if frame%120 == 0:
            print('ENCODE', frame, '/', len(schedule), flush=True)
    enc.stdin.close()
    if enc.wait():
        raise RuntimeError('Encoding failed')
    manifest = dict(video=str(target), dimensions=[W, H], frames=len(schedule), fps=FPS, duration_seconds=len(schedule)/FPS,
                    capture=str(a.capture), templates=str(a.templates), source_control_fps=10, source_playback_speed=a.playback_rate,
                    on_screen_playback_rate=f'{a.playback_rate}× 连续回放', endpoint_holds_seconds=[1.2, 1.2],
                    on_screen_title='几何位姿估计', reference_image='/home/linux/Downloads/img/20261124-155231.jpg',
                    pointcloud_source='simulation pose reference / ground-truth stand-in; NOT learned predictions',
                    network_inference=False, pointcloud_geometry='complete module and entire fixed socket including support',
                    pointcloud_display_frame='socket coordinates; same rigid reference transform applied to both objects',
                    palette=a.palette,
                    focus_color='orange module TIP ONLY; green socket mouth; unchanged from previous edition',
                    ordinary_module_rgb=list(film.ordinary_colors()[2]), ordinary_socket_rgb=list(film.ordinary_colors()[1]),
                    socket_support_rgb=list(GRAY),
                    component_partition='source part_id: support parts 000-003,039,111-118; other socket parts upper assembly; module separate',
                    module_tip_rgb=list(MODULE), socket_mouth_rgb=list(GREEN),
                    ordinary_object_grays_distinct=True,
                    hidden_focus_display='none' if a.point_style == 'layered' else 'subdued orange/green for hidden module/mouth focus points',
                    point_style=a.point_style,
                    presentation_policy=PRESENTATION['id'],
                    presentation_config_sha256=hashlib.sha256(PRESENTATION_PATH.read_bytes()).hexdigest(),
                    point_diameter_output_px=1 if a.point_style == 'layered' else None,
                    same_point_diameter_for_all_layers=a.point_style == 'layered',
                    source_points_thinned=False,
                    wrist_screen_grid_thinning=a.point_style == 'legacy',
                    point_dilation=a.point_style == 'legacy',
                    sampling_pitch_mm={k:film.template_manifest[k] for k in ['ordinary_pitch_mm','focus_pitch_mm']},
                    wrist_occlusion='RTX radial depth, 1.2mm tolerance', wrist_crop=[360, 260, 600, 540],
                    wrist_overlay=a.wrist_overlay,
                    wrist_ordinary_markers_drawn=a.wrist_overlay == 'all',
                    wrist_non_marker_pixels='original RGB after the unchanged crop and resize',
                    third_person_crop=[150, 0, 850, 820], layout='three equal primary-view cards; no auxiliary or macro panels',
                    wrist_macro_removed=True, third_person_detail_removed=True, unused_full_field_panel_removed=True,
                    ordinary_module_points_colored=a.palette == 'component-tones',
                    ordinary_surfaces_neutral=a.palette != 'component-tones',
                    ui_accents_neutral=a.palette == 'component-grays',
                    vivid_accent_colors_require_representation_level_1=True,
                    all_source_states_included=True, aligned_source_index=aligned, frame_map=frame_map,
                    renderer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    manifest['asset_identity']=film.report.get('asset_identity',{})
    (a.output/'film_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    print('FILM_COMPLETE', target, flush=True)


if __name__ == '__main__':
    main()
