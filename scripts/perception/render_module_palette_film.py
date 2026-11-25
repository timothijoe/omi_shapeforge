"""Compare neutral module-only point colors; preserve the accepted r9 film."""
import argparse
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import subprocess

from PIL import Image, ImageDraw
from render_alignment_film import Film as BaseFilm, txt, FG, MUTED, BG, FPS, W, H

TONES = {
    'cool-silver': {'rgb': (216, 221, 228), 'label': 'A  冷银灰', 'note': '更明亮、偏冷的中性银灰'},
    'warm-titanium': {'rgb': (187, 181, 170), 'label': 'B  暖钛灰', 'note': '微暖、低饱和，避开橙棕色'},
    'graphite': {'rgb': (119, 125, 133), 'label': 'C  深石墨灰', 'note': '更深的中性灰，强调主体轮廓'},
}


class R9Baseline(BaseFilm):
    """Keep comparison labels truthful after r10 becomes the global default."""
    def ordinary_colors(self):
        colors = super().ordinary_colors()
        colors[2] = (144, 151, 160)
        return colors


class Film(BaseFilm):
    def __init__(self, capture, templates, tone='cool-silver'):
        self.module_tone = tone
        self.module_rgb = TONES[tone]['rgb']
        super().__init__(capture, templates, 3, 'component-grays', 'layered', 'all')

    def ordinary_colors(self):
        colors = super().ordinary_colors()
        colors[2] = self.module_rgb
        return colors


def compare(capture, templates, output):
    """Same insertion state, same view/points; change module ordinary RGB only."""
    original = R9Baseline(capture, templates, 3, 'component-grays', 'layered', 'all')
    index = min(range(len(original.states)), key=lambda i: abs(original.states[i]['depth_mm']-17))
    variants = [('original', original, '原版 r9', '当前可用版本：普通模块深灰')]
    variants.extend((key, Film(capture, templates, key), tone['label'], tone['note']) for key, tone in TONES.items())
    board = Image.new('RGB', (1280, 1160), BG)
    txt(board, (36, 22), '光模块普通点云 · 低饱和配色对比', 32, FG, True)
    txt(board, (38, 78), f'同一插入时刻 · 深度 {original.states[index]["depth_mm"]:.2f} mm · 只改变模块普通面', 19, MUTED)
    d = ImageDraw.Draw(board)
    for j, (key, film, label, note) in enumerate(variants):
        x, y = 24+(j%2)*628, 126+(j//2)*498
        d.rounded_rectangle((x, y, x+604, y+480), 16, fill=(16, 30, 39), outline=(43, 62, 75))
        txt(board, (x+20, y+10), label, 24, FG, True)
        txt(board, (x+20, y+47), note, 17, MUTED)
        # A color-inspection crop, not an added movie panel or a point resample.
        image = film.complete_cloud(index).crop((85, 65, 485, 345)).resize((564, 395), Image.Resampling.NEAREST)
        board.paste(image, (x+20, y+78))
        film.frame(index).save(output/f'preview_{key}_{index:04d}.png')
    txt(board, (38, 1130), '尖端橙色、孔口绿色、插座与底座均保持原样；点数、点径、相机和姿态不变。', 18, MUTED)
    board.save(output/'module_palette_comparison.png')
    return index


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--capture', type=Path, required=True)
    p.add_argument('--templates', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--module-tone', choices=TONES, default='cool-silver')
    p.add_argument('--preview', action='store_true')
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=True)
    compare_index = compare(a.capture, a.templates, a.output)
    film = Film(a.capture, a.templates, a.module_tone)
    for i in [0, 47, compare_index, len(film.states)-1]:
        film.frame(i).save(a.output/f'preview_{i:04d}.png')
    if a.preview:
        print('PREVIEW_COMPLETE', a.output, flush=True)
        return
    schedule = [0]*36+list(range(len(film.states)))+[len(film.states)-1]*36
    target = a.output/'alignment_insertion_module_palette_1080p.mp4'
    enc = subprocess.Popen(['ffmpeg', '-v', 'error', '-n', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
                            '-r', str(FPS), '-i', '-', '-an', '-c:v', 'libx264', '-threads', '6', '-preset', 'fast',
                            '-crf', '18', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(target)], stdin=subprocess.PIPE)
    frame_map = []
    for frame, index in enumerate(schedule):
        enc.stdin.write(film.frame(index).tobytes())
        row = film.states[index]
        frame_map.append(dict(video_frame=frame, source_index=index, source_step=row['source_step'], phase=row['showcase_phase']))
        if frame%120 == 0:
            print('ENCODE', frame, '/', len(schedule), flush=True)
    enc.stdin.close()
    if enc.wait():
        raise RuntimeError('Encoding failed')
    manifest = dict(video=str(target), frames=len(schedule), fps=FPS, dimensions=[W,H], duration_seconds=len(schedule)/FPS,
                    capture=str(a.capture), templates=str(a.templates), frame_map=frame_map, playback_rate=3,
                    source_states=len(film.states), point_style='layered', point_diameter_output_px=1,
                    module_tone=a.module_tone, ordinary_module_rgb=list(film.module_rgb),
                    source_point_positions_changed=False, camera_changed=False, timing_changed=False,
                    source_sampling_pitch_mm={'ordinary':.8, 'focus':.2}, module_tip_rgb=[255,166,68],socket_mouth_rgb=[78,240,112],
                    pointcloud_source='simulation geometry and reference poses, not network predictions', network_inference=False,
                    new_physics_run=False, asset_identity=film.report['asset_identity'],
                    accepted_baseline='r9 retained; accepted as usable version, ordinary module color refinement requested',
                    candidate_user_reviewed=False, comparison_source_index=compare_index,
                    renderer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (a.output/'film_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
    print('FILM_COMPLETE', target, flush=True)


if __name__ == '__main__':
    main()
