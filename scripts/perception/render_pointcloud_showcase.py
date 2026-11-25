"""Make a designed film from frozen held-out predictions, without changing results.

Run with the foundation_stereo Python environment (Pillow, OpenCV, NumPy).
All 3D positions and 2D overlays use the saved rigid predictions and templates.
Only the presentation camera moves; source sequences are held at their 6 fps.
"""
from __future__ import annotations

import argparse
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path
import subprocess
import wave

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, FPS, DURATION = 1920, 1080, 30, 56
BG = (9, 15, 25)
FG = (238, 245, 249)
MUTED = (137, 159, 180)
CYAN = (89, 221, 240)
GREEN = (92, 235, 175)
ORANGE = (255, 180, 101)
RULE = (40, 58, 77)
PANEL = (15, 25, 39)
FONT = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
BOLD = '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'
MONO = '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'
SCENES = [(0, 6, '01', '从图像到三维'), (6, 14, '02', '仅以 RGB 为输入'),
          (14, 26, '03', '留出配置 · 逐帧对照'), (26, 34, '04', '旧新模型 · 同图比较'),
          (34, 42, '05', '完整测试集'), (42, 49, '06', '保留失效案例'),
          (49, 56, '07', '下一步 · 感知预训练')]


@lru_cache(maxsize=100)
def font(size, weight='regular'):
    return ImageFont.truetype({'regular': FONT, 'bold': BOLD, 'mono': MONO}[weight], size)


def text(im, xy, message, size=24, color=FG, weight='regular'):
    ImageDraw.Draw(im).text(xy, message, font=font(size, weight), fill=color, spacing=14)


def line(im, xy, color=RULE, width=1):
    ImageDraw.Draw(im).line(xy, fill=color, width=width)


def box(im, xy, fill=PANEL, outline=RULE, radius=22):
    ImageDraw.Draw(im).rounded_rectangle(xy, radius, fill=fill, outline=outline)


def ease(t):
    t = np.clip(t, 0, 1)
    return float(t*t*(3-2*t))


def digest(p):
    with open(p, 'rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


class Film:
    def __init__(self, run, output):
        self.run, self.output = run, output
        self.config = json.loads((run/'train/config.json').read_text())
        self.report = json.loads((run/'train/report.json').read_text())
        self.pred = dict(np.load(run/'train/test_predictions.npz'))
        self.old = dict(np.load(run/'transfer_evaluation/old_frozen_predictions.npz'))
        np.testing.assert_array_equal(self.old['frame_ids'], self.pred['frame_ids'])
        np.testing.assert_allclose(self.old['gt'], self.pred['gt'], atol=1e-7)
        self.records = {r['id']: r for r in map(json.loads, (run/'data/records.jsonl').read_text().splitlines())}
        self.rows = [self.records[int(fid)] for fid in self.pred['frame_ids']]
        assert len(self.rows) == 384 and all(r['split'] == 'test' for r in self.rows)
        self.episodes = sorted({r['episode'] for r in self.rows})
        self.by_episode = {e: [i for i, r in enumerate(self.rows) if r['episode'] == e] for e in self.episodes}
        self.worst = int(np.argmax(self.pred['tip_in_socket_error_mm']))
        self.normal = self.by_episode['test_0000'][6]
        self.K = np.array(self.config['calibration']['K'])
        self.D = np.array(self.config['calibration']['D'])
        self.templates = {n: dict(np.load(run/f'network_templates/{n}_{c}.npz'))
                          for n, c in [('module', 37895), ('socket', 204820)]}
        self.counts = {n: len(d['points_m']) for n, d in self.templates.items()}
        self.error = self.pred['tip_in_socket_error_mm']
        self.old_mean = float(self.old['tip_in_socket_error_mm'].mean())
        self.mean = float(self.error.mean())
        self.p90 = float(np.percentile(self.error, 90))
        self.maximum = float(self.error.max())
        np.testing.assert_allclose(self.mean, self.report['test_metrics']['network']['relative_tip_error_mm']['mean'])
        self.base = self.background()
        self.cloud_cache = {}
        self.protected = {str(p): digest(p) for p in [run/'train/best.pt', run/'train/inference.pt',
                          run/'train/test_predictions.npz', run/'train/report.json',
                          run/'data/records.jsonl', run/'transfer_evaluation/old_frozen_predictions.npz',
                          *sorted((run/'network_templates').glob('*'))] if p.is_file()}

    def background(self):
        yy, xx = np.mgrid[:H, :W]
        glow = np.exp(-((xx-1450)/800)**2-((yy-440)/650)**2)
        a = np.empty((H, W, 3), np.uint8)
        for j, value in enumerate(BG):
            a[:, :, j] = value + glow * [2, 9, 15][j]
        im = Image.fromarray(a)
        d = ImageDraw.Draw(im)
        for x in range(64, W, 64):
            for y in range(144, 1010, 64):
                d.point((x, y), fill=(30, 45, 59))
        text(im, (80, 40), 'OMI', 32, FG, 'bold')
        line(im, (166, 47, 166, 84), RULE, 2)
        text(im, (190, 45), 'SHAPEFORGE   /   PERCEPTION LAB', 19, MUTED, 'mono')
        text(im, (1455, 46), 'RGB  →  POSE  →  POINT CLOUD', 18, CYAN, 'mono')
        line(im, (80, 112, 1840, 112))
        line(im, (80, 992, 1840, 992))
        text(im, (80, 1017), 'GC-r01 · 腕部视觉 / 接近阶段仿真', 20, MUTED)
        text(im, (1475, 1019), 'HELD-OUT  /  2026.11', 19, MUTED, 'mono')
        return im

    def chrome(self, im, scene, t):
        start, end, number, title = SCENES[scene]
        text(im, (80, 144), f'{number}  /', 22, CYAN, 'mono')
        text(im, (182, 139), title, 26, MUTED)
        d = ImageDraw.Draw(im)
        for i, (a, b, _, _) in enumerate(SCENES):
            x0, x1 = 80 + a/DURATION*1760, 80 + b/DURATION*1760-5
            d.rounded_rectangle((x0, 982, x1, 985), 1, fill=RULE)
            if t > a:
                xend = x0+(x1-x0)*min(1, (t-a)/(b-a))
                d.rectangle((x0, 982, xend, 985), fill=CYAN)

    @lru_cache(maxsize=100)
    def raw(self, idx):
        return np.array(Image.open(self.run/'data'/self.rows[idx]['image']).convert('RGB'))

    @lru_cache(maxsize=256)
    def detail(self, idx, which='raw', size=(810, 695)):
        """Projected points are thinned in screen space, never mask-corrected."""
        crop = (307, 232, 653, 529)
        x0, y0, x1, y1 = crop
        w, h = size
        raw = self.raw(idx)[y0:y1, x0:x1]
        im = cv2.resize(raw, (w, h), interpolation=cv2.INTER_CUBIC)
        if which == 'raw':
            return Image.fromarray(im)
        Ts = self.pred['gt'][idx] if which == 'gt' else (self.old['pred'][idx] if which == 'old' else self.pred['pred'][idx])
        tint = GREEN if which == 'gt' else ORANGE
        all_points = []
        for j, name in enumerate(['module', 'socket']):
            a, T = self.templates[name], Ts[j]
            xyz = a['points_m']@T[:3, :3].T+T[:3, 3]
            n = a['normals']@T[:3, :3].T
            facing = (n*xyz).sum(1) < 0
            q = xyz[facing].astype(np.float64)
            uv = cv2.fisheye.projectPoints(q[:, None, :], np.zeros(3), np.zeros(3), self.K, self.D)[0][:, 0]
            uv = (uv-[x0, y0])*[w/(x1-x0), h/(y1-y0)]
            level = a['representation_level'][facing]
            valid = (q[:, 2] > .001) & (uv[:, 0] >= 2) & (uv[:, 0] < w-2) & (uv[:, 1] >= 2) & (uv[:, 1] < h-2)
            all_points.append(np.c_[uv[valid], q[valid, 2], level[valid]])
        q = np.concatenate(all_points)
        pixel = np.rint(q[:, :2]).astype(int)
        key = pixel[:, 1]*w+pixel[:, 0]
        zbuf = np.full(w*h, np.inf)
        np.minimum.at(zbuf, key, q[:, 2])
        q = q[q[:, 2] <= zbuf[key]+.0005]
        layer = im.copy()
        for focus, spacing, radius, color in [(False, 10, 1, (137, 158, 172)), (True, 5, 2, tint)]:
            pts = q[(q[:, 3] > .5) == focus]
            cell = np.floor(pts[:, :2]/spacing).astype(int)
            keys = cell[:, 1]*(w//spacing+2)+cell[:, 0]
            order = np.lexsort((pts[:, 2], keys))
            _, first = np.unique(keys[order], return_index=True)
            for u, v in pts[order[first], :2]:
                cv2.circle(layer, (round(u), round(v)), radius, color, -1, cv2.LINE_AA)
        return Image.fromarray(cv2.addWeighted(layer, .86, im, .14, 0))

    def cloud_data(self, idx, compare=False):
        key = (idx, compare)
        if key in self.cloud_cache:
            return self.cloud_cache[key]
        reference = np.linalg.inv(self.pred['pred'][idx, 1])
        points, normals, colors = [], [], []
        kinds = ['gt', 'pred'] if compare else ['pred']
        for kind in kinds:
            for j, name in enumerate(['module', 'socket']):
                a = self.templates[name]
                T = reference@self.pred[kind][idx, j]
                q = a['points_m']@T[:3, :3].T+T[:3, 3]
                n = a['normals']@T[:3, :3].T
                ordinary = np.array((116, 157, 180) if name == 'module' else (75, 110, 138))
                focus = np.array(CYAN if name == 'module' else ORANGE)
                if compare:
                    ordinary = np.array(GREEN if kind == 'gt' else ORANGE)*.55
                    focus = np.array(GREEN if kind == 'gt' else ORANGE)
                level = a['representation_level'] > .5
                col = np.where(level[:, None], focus, ordinary).astype(float)
                light = .53+.47*np.abs(n@np.array([.4, .3, .866]))
                col *= light[:, None]
                points.append(q)
                normals.append(n)
                colors.append(col)
        out = np.concatenate(points), np.concatenate(colors), np.concatenate(normals)
        self.cloud_cache[key] = out
        return out

    def cloud(self, idx, angle, size=(1100, 760), compare=False):
        """Render ALL template points with a per-pixel depth buffer in socket frame."""
        w, h = size
        points, colors, normals = self.cloud_data(idx, compare)
        target = np.array([0, .024, -.045])
        theta = math.radians(angle)
        eye = target+np.array([.29*math.sin(theta), .29*math.cos(theta), .19])
        f = target-eye
        f /= np.linalg.norm(f)
        right = np.cross(f, [0, 0, 1])
        right /= np.linalg.norm(right)
        up = np.cross(right, f)
        basis = np.stack([right, up, f], 1)
        scale = h/.263
        q = (points-target)@basis
        uv = np.rint(q[:, :2]*[scale, -scale]+[w*.5, h*.46]).astype(int)
        valid = (uv[:, 0] >= 1)&(uv[:, 0] < w-1)&(uv[:, 1] >= 1)&(uv[:, 1] < h-1)
        # Cull back-facing surfaces against the independent display camera.
        valid &= ((normals@(eye-target)) > -.003)
        pixels = uv[valid]
        depth = q[valid, 2]
        key = pixels[:, 1]*w+pixels[:, 0]
        order = np.lexsort((depth, key))
        _, first = np.unique(key[order], return_index=True)
        take = order[first]
        colored = np.clip(colors[valid][take], 0, 255).astype('uint8')
        layer = np.zeros((h, w, 3), np.uint8)
        p = pixels[take]
        layer[p[:, 1], p[:, 0]] = colored
        layer = cv2.dilate(layer, np.ones((2, 2), np.uint8))
        halo = cv2.GaussianBlur(layer, (0, 0), 3)
        image = np.zeros((h, w, 3), np.uint8)
        image[:] = (11, 20, 32)
        d = Image.fromarray(image)
        def proj(p):
            q = (np.asarray(p)-target)@basis
            return (q[:2]*[scale, -scale]+[w*.5, h*.46]).tolist()
        for step in np.arange(-.16, .181, .02):
            line(d, [tuple(proj([step, -.15, -.137])), tuple(proj([step, .18, -.137]))], (23, 41, 56))
            line(d, [tuple(proj([-.16, step, -.137])), tuple(proj([.16, step, -.137]))], (23, 41, 56))
        image = np.array(d)
        image = cv2.add(image, (halo*.38).astype('uint8'))
        mask = layer.max(2) > 0
        image[mask] = np.maximum(image[mask], layer[mask])
        return Image.fromarray(image)

    def title(self, im, title, subtitle=None):
        text(im, (80, 194), title, 48, FG, 'bold')
        if subtitle:
            text(im, (82, 269), subtitle, 23, MUTED)

    def hero(self, t, ending=False):
        im = self.base.copy()
        cloud = self.cloud(self.normal, -28+11*t, (1110, 760))
        im.paste(cloud, (770, 195))
        if not ending:
            text(im, (80, 267), '从一帧图像', 72, FG, 'bold')
            text(im, (80, 375), '到三维几何', 72, CYAN, 'bold')
            text(im, (86, 509), '光模块与插座的视觉位姿估计', 28, MUTED)
            line(im, (86, 590, 622, 590))
            text(im, (84, 622), '242,715', 62, FG, 'mono')
            text(im, (87, 715), '完整输出点数 · 整体表面 + 重点加密', 22, MUTED)
            text(im, (86, 813), '01  RGB     02  双物体位姿     03  完整点云', 19, CYAN)
        else:
            text(im, (80, 253), '让视觉变成', 67, FG, 'bold')
            text(im, (80, 355), '可检查的三维状态', 61, CYAN, 'bold')
            text(im, (84, 495), '下一步：三变量覆盖与感知预训练', 27, MUTED)
            line(im, (84, 566, 700, 566))
            text(im, (83, 595), '14,549', 64, FG, 'mono')
            text(im, (87, 684), '张严格网格样本已就绪 · 新数据尚未训练', 23, MUTED)
            text(im, (87, 789), '当前画面来自上一版接触数据模型的留出预测', 21, MUTED)
            text(im, (87, 831), '完整点云由固定模板与预测位姿展开', 21, MUTED)
        text(im, (1105, 879), '青色 / 模块重点区域     橙色 / 插座孔口', 22, MUTED)
        return im

    def input_scene(self, local):
        im = self.base.copy()
        self.title(im, '只看 RGB，估计物体的空间状态', '单帧图像 → 双物体位姿 → 固定表面模板展开')
        box(im, (80, 341, 712, 933))
        text(im, (110, 362), '01 / WRIST RGB', 21, CYAN, 'mono')
        im.paste(Image.fromarray(self.raw(self.normal)).resize((576, 324), Image.Resampling.LANCZOS), (108, 422))
        text(im, (110, 777), '960 × 540 · 完整鱼眼视野', 24, FG)
        text(im, (110, 827), '推理输入仅为 RGB 图像', 24, CYAN)
        text(im, (110, 874), '训练位姿标签只用于监督和评估', 20, MUTED)
        im.paste(self.cloud(self.normal, 38+local*10, (1050, 620)), (778, 319))
        text(im, (806, 348), '02 / PREDICTED GEOMETRY', 21, CYAN, 'mono')
        box(im, (1080, 856, 1800, 929), (13, 24, 37))
        text(im, (1104, 873), '模块 37,895 点     插座 204,820 点', 25, FG)
        return im

    def index_at(self, episode, local):
        # 12 original frames / 6 fps, replayed at half speed for readability.
        return self.by_episode[episode][min(11, int(local*3))]

    def compare_scene(self, local, transfer=False):
        im = self.base.copy()
        if transfer:
            episode = ['test_0000', 'test_0027'][min(1, int(local/4))]
            title = '同一张图像，比较旧新模型'
            subtitle = f'全部 384 张接触版测试图：平均尖端相对误差 {self.old_mean:.3f} → {self.mean:.3f} mm'
            left, right = 'old', 'pred'
            labels = ['旧冻结模型', '接触版续训模型']
        else:
            episode = ['test_0000', 'test_0001', 'test_0003'][min(2, int(local/4))]
            title = '留出配置中的真实预测'
            subtitle = '整体均匀表面 + 尖端 / 孔口加密 · 两幅图使用同一原始 RGB'
            left, right = 'gt', 'pred'
            labels = ['仿真真值', '网络预测']
        idx = self.index_at(episode, local%4)
        self.title(im, title, subtitle)
        for x, kind, label in [(80, left, labels[0]), (980, right, labels[1])]:
            box(im, (x, 337, x+860, 900))
            color = GREEN if kind == 'gt' else ORANGE
            text(im, (x+25, 352), label, 26, color, 'bold')
            # Preserve the detail crop aspect ratio; no stretching the geometry.
            panel = self.detail(idx, kind, (810, 695))
            # Letterbox with a tighter, documented vertical crop for two-panel film view.
            panel = panel.crop((0, 0, 810, 464))
            im.paste(panel, (x+25, 403))
            if kind == 'gt':
                text(im, (x+440, 359), '绿色 / 重点   灰色 / 普通表面', 18, MUTED)
            else:
                err = self.old['tip_in_socket_error_mm'][idx] if kind == 'old' else self.error[idx]
                text(im, (x+518, 357), f'尖端相对误差 {err:.2f} mm', 20, color)
        row = self.rows[idx]
        text(im, (84, 925), f"{episode}  /  frame {row['frame']:02d}    ·    原始 6 fps，0.5× 慢放；未插值预测", 22, MUTED)
        return im

    def chart(self, im, rect, reveal=1):
        x0, y0, x1, y1 = rect
        # Fixed scales and all 384 unfiltered test observations.
        for value in [0, 2, 4, 6, 8, 10, 12]:
            y = y1-value/12*(y1-y0)
            line(im, (x0, y, x1, y), RULE)
            text(im, (x0-52, y-15), str(value), 18, MUTED, 'mono')
        limit = min(len(self.error), int(len(self.error)*reveal))
        d = ImageDraw.Draw(im)
        for i, value in enumerate(self.error[:limit]):
            x = x0+i/383*(x1-x0)
            y = y1-value/12*(y1-y0)
            color = ORANGE if value > 2 else CYAN
            d.ellipse((x-3, y-3, x+3, y+3), fill=color)
        text(im, (x0, y1+20), '384 张留出图 · 按配置与帧序排列', 20, MUTED)
        text(im, (x0, y0-45), '尖端相对误差 / mm', 20, MUTED)

    def metrics_scene(self, local):
        im = self.base.copy()
        self.title(im, '看均值，也看误差的尾部', '32 个独立测试配置 · 384 帧 · 检查点仅由验证集选择')
        cards = [(80, '平均', self.mean, CYAN), (677, 'P90', self.p90, FG), (1274, '最大', self.maximum, ORANGE)]
        for x, label, value, color in cards:
            box(im, (x, 350, x+566, 565))
            text(im, (x+28, 373), label, 25, MUTED)
            text(im, (x+28, 421), f'{value:.3f}', 70, color, 'mono')
            text(im, (x+395, 468), 'mm', 26, MUTED, 'mono')
        self.chart(im, (146, 659, 1770, 864), ease(local/2.4))
        text(im, (83, 926), '指标为固定尖端参考点在插座系中的三维误差；不等同于点云均值或实际插入精度。', 22, MUTED)
        return im

    def failure_scene(self, local):
        im = self.base.copy()
        self.title(im, '最大误差案例，完整保留', f"{self.rows[self.worst]['episode']} / frame {self.rows[self.worst]['frame']:02d} · 未删除该配置，未修改预测")
        box(im, (80, 340, 940, 928))
        panel = self.detail(self.worst, 'raw', (810, 695)).crop((0, 0, 810, 464))
        # Same fixed geometric tip reference, projected through actual fisheye K,D.
        tip = np.array([0, -.0350931697, 0])
        uv = []
        for kind in ['gt', 'pred']:
            T = self.pred[kind][self.worst, 0]
            q = T[:3, :3]@tip+T[:3, 3]
            p = cv2.fisheye.projectPoints(q[None, None].astype(float), np.zeros(3), np.zeros(3), self.K, self.D)[0][0, 0]
            uv.append((p-[307, 232])*[810/346, 695/297])
        d = ImageDraw.Draw(panel)
        a, b = uv
        d.line([tuple(a), tuple(b)], fill=ORANGE, width=2)
        d.ellipse((a[0]-11, a[1]-11, a[0]+11, a[1]+11), outline=GREEN, width=3)
        d.line((b[0]-10, b[1]-10, b[0]+10, b[1]+10), fill=ORANGE, width=3)
        d.line((b[0]-10, b[1]+10, b[0]+10, b[1]-10), fill=ORANGE, width=3)
        im.paste(panel, (105, 370))
        text(im, (108, 864), '○ 真值参考点    × 预测参考点', 24, GREEN)
        text(im, (1010, 354), f'{self.maximum:.3f}', 90, ORANGE, 'mono')
        text(im, (1484, 419), 'mm', 30, MUTED, 'mono')
        text(im, (1015, 489), '该帧尖端相对误差', 29, FG)
        text(im, (1015, 567), '该夹持配置的模块朝向偏离训练覆盖。', 27, FG)
        text(im, (1015, 616), '诊断提示覆盖不足，原因尚未完全隔离。', 24, MUTED)
        line(im, (1015, 694, 1810, 694))
        text(im, (1015, 730), '当前验证范围', 22, CYAN)
        text(im, (1015, 777), '接近阶段仿真内的视觉估计', 29, FG)
        text(im, (1015, 837), '插入后遮挡、策略收益与真机精度仍待验证', 23, MUTED)
        return im

    def frame(self, t):
        scene = next(i for i, (a, b, _, _) in enumerate(SCENES) if a <= t < b)
        start, end, *_ = SCENES[scene]
        local = t-start
        if scene == 0:
            im = self.hero(local)
        elif scene == 1:
            im = self.input_scene(local)
        elif scene == 2:
            im = self.compare_scene(local)
        elif scene == 3:
            im = self.compare_scene(local, True)
        elif scene == 4:
            im = self.metrics_scene(local)
        elif scene == 5:
            im = self.failure_scene(local)
        else:
            im = self.hero(local+16, True)
        self.chrome(im, scene, t)
        # Short dip transitions keep source images and poses paired exactly.
        fade = min(ease(local/.28), ease((end-t)/.28))
        if fade < 1:
            im = Image.blend(self.base, im, fade)
        return im

    def manifest(self):
        return {'source_run': str(self.run), 'dimensions': [W, H], 'fps': FPS, 'duration_seconds': DURATION,
                'scenes': SCENES, 'counts': self.counts, 'prediction_input': 'single wrist RGB only',
                'geometry': 'saved rigid predictions applied to fixed complete surface templates',
                'new_training': False, 'grid_data_status': '14549 strict samples, no training on this set',
                'source_sequences_fps': 6, 'source_sequences_playback': '0.5x; zero-order hold, no pose or image interpolation',
                'display_3d': 'all template points, per-pixel z-buffer and display-camera back-face culling',
                'display_2d': 'screen-space subset; no ground-truth object mask used to correct predictions',
                'detail_crop': [307, 232, 653, 529],
                'detail_film_visible_y_end': 232+464/695*297,
                'test_frames': len(self.rows), 'test_configurations': len(self.episodes),
                'relative_tip_error_mm': {'mean': self.mean, 'p90': self.p90, 'maximum': self.maximum},
                'old_model_same_test_mean_mm': self.old_mean,
                'shown_episodes': ['test_0000', 'test_0001', 'test_0003', 'test_0027'],
                'failure_frame_id': int(self.pred['frame_ids'][self.worst]),
                'checkpoint_selection': 'validation only; this video does not select or change a checkpoint',
                'scope': 'contact-qualified pre-insertion simulation; not insertion or real-world accuracy validation',
                'soundtrack': 'original deterministic synthesized ambient track, no third-party audio',
                'source_sha256': self.protected}


def soundtrack(path):
    """Quiet original stereo synth bed, authored locally from oscillators."""
    rate = 48000
    t = np.arange(DURATION*rate)/rate
    left, right = np.zeros_like(t), np.zeros_like(t)
    # Slow suspended chords, with overlapping envelopes and restrained soft pulses.
    chords = [[45, 52, 59, 64], [41, 48, 55, 60], [48, 55, 62, 67], [43, 50, 57, 62]]
    for i, start in enumerate(np.arange(0, DURATION, 7)):
        local = t-start
        active = (local >= 0)&(local < 9)
        z = np.maximum(local, 0)
        envelope = np.minimum(z/1.6, 1)*np.clip((9-z)/2.4, 0, 1)*active
        for j, note in enumerate(chords[i%4]):
            hz = 440*2**((note-69)/12)
            for signal, detune in [(left, .999), (right, 1.001)]:
                pad = np.sin(2*np.pi*hz*detune*t+.20*np.sin(2*np.pi*.11*t+j))
                pad += .14*np.sin(2*np.pi*hz*2*t)
                signal += .023*envelope*pad
    for beat in np.arange(0, DURATION, .6):
        z = t-beat
        env = np.exp(-np.maximum(z, 0)*17)*(z >= 0)*(z < .45)
        pulse = .035*env*np.sin(2*np.pi*(70*z+2*np.exp(-np.maximum(z, 0)*20)))
        left += pulse
        right += pulse
    fade = np.clip(t/2.5, 0, 1)*np.clip((DURATION-t)/3, 0, 1)
    stereo = np.stack([left, right], 1)*fade[:, None]
    pcm = np.clip(stereo*32767, -32768, 32767).astype('<i2')
    with wave.open(str(path), 'wb') as output:
        output.setnchannels(2)
        output.setsampwidth(2)
        output.setframerate(rate)
        output.writeframes(pcm.tobytes())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--preview', action='store_true')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    film = Film(args.run, args.output)
    (args.output/'storyboard').mkdir(exist_ok=True)
    times = [3, 10, 16, 23, 28, 32, 39, 45, 52]
    tiles = []
    for t in times:
        im = film.frame(t)
        im.save(args.output/f'storyboard/{t:02d}s.png')
        tiles.append(im.resize((640, 360), Image.Resampling.LANCZOS))
    sheet = Image.new('RGB', (1920, 1080))
    for i, tile in enumerate(tiles):
        sheet.paste(tile, (i%3*640, i//3*360))
    sheet.save(args.output/'storyboard.jpg', quality=95)
    film.frame(3).save(args.output/'poster.png')
    (args.output/'manifest.json').write_text(json.dumps(film.manifest(), ensure_ascii=False, indent=2))
    print(f'Storyboard ready: {args.output}', flush=True)
    if args.preview:
        return
    silent = args.output/'picture.mp4'
    process = subprocess.Popen(['ffmpeg', '-v', 'error', '-n', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
                                '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-', '-an', '-c:v', 'libx264',
                                '-threads', '6', '-preset', 'fast', '-crf', '18', '-pix_fmt', 'yuv420p',
                                '-movflags', '+faststart', str(silent)], stdin=subprocess.PIPE)
    try:
        for frame in range(FPS*DURATION):
            process.stdin.write(film.frame(frame/FPS).tobytes())
            if frame%(FPS*2) == 0:
                print(f'Rendered {frame/FPS:.0f}/{DURATION}s', flush=True)
    finally:
        process.stdin.close()
    if process.wait():
        raise RuntimeError('ffmpeg failed')
    soundtrack(args.output/'soundtrack.wav')
    target = args.output/'omi_pointcloud_showcase_1080p.mp4'
    subprocess.run(['ffmpeg', '-v', 'error', '-n', '-i', str(silent), '-i', str(args.output/'soundtrack.wav'),
                    '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', str(target)], check=True)
    changed = [p for p, sha in film.protected.items() if digest(Path(p)) != sha]
    if changed:
        raise RuntimeError(f'Source files changed during rendering: {changed}')
    (args.output/'source_preservation.json').write_text(json.dumps({'all_protected_sources_unchanged': True, 'sha256': film.protected}, indent=2))
    print(f'Finished: {target}', flush=True)


if __name__ == '__main__':
    main()
