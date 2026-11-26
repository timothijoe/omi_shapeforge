"""Compose synchronized policy replay panels without changing recorded motion."""
import argparse
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageFont


@lru_cache(maxsize=20)
def font(size, bold=False):
    return ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-'+('Bold' if bold else 'Regular')+'.ttc', size)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run', type=Path, required=True)
    p.add_argument('--wrist-layout', action='store_true', help='Large wrist ROI, uncropped wrist and synchronized external view')
    p.add_argument('--realtime', action='store_true', help='Keep simulation-time playback; hold sampled images between captured control steps')
    a = p.parse_args(); run = a.run
    selection = json.loads((run/'selection.json').read_text())
    capture = json.loads((run/'capture/capture_report.json').read_text())
    states = {m: json.loads(Path(s['states']).read_text()) for m, s in selection['modes'].items()}
    by_step = {m:{r['step']:r for r in rows} for m,rows in states.items()}
    correction=None
    if selection.get('correction_metrics'):
        correction_data=json.loads(Path(selection['correction_metrics']).read_text())
        assert correction_data['state_sha256']=={m:s['states_sha256'] for m,s in selection['modes'].items()}
        correction={m:{v['step']:v for v in values} for m,values in correction_data['modes'].items()}
        for mode in by_step:assert set(correction[mode])==set(by_step[mode])
    pose = selection['modes']['path']['evaluation']['socket_pose']
    assert pose == selection['modes']['goal']['evaluation']['socket_pose']
    colors = {'path': '#5ed3ed', 'goal': '#f4b36a'}
    output = run/'system1_vs_system0.mp4'
    fps = 10; stride = capture['stride']; assert stride in (1,2,3)
    if a.wrist_layout:assert capture.get('wrist') and selection.get('wrist_crop')
    last = max(max(v) for v in by_step.values())
    first = max(min(v) for v in by_step.values())
    timeline_step=1 if a.realtime else stride
    playback_speed=timeline_step*fps/10
    timeline = sorted(set([*range(first, last+1, timeline_step), last]))
    bg = '#101923'; fg = '#edf3f8'; muted = '#a4b3c1'

    @lru_cache(maxsize=12)
    def panel(mode, step, name):
        return Image.open(run/'capture'/mode/f'{step:04d}'/f'{name}.jpg').convert('RGB')

    def frame(step, final=False):
        im = Image.new('RGB', (1920, 1080), bg); d = ImageDraw.Draw(im)
        def text(x, y, s, size=24, color=fg, bold=False):
            d.text((x, y), s, font=font(size, bold), fill=color)
        text(30, 18, selection.get('label', 'System1 路径是否有帮助？'), 40, bold=True)
        subtitle=selection.get('initial_pose_label', f'同一目标位置：X {pose["dx_mm"]:+g} mm / Y {pose["dy_mm"]:+g} mm   ·   两边均为自主策略，规则接管关闭')
        text(30, 77, subtitle, 24, muted)
        text(1465, 32, f'执行记录回放  /  {playback_speed:g}×', 26, muted)
        d.line((960, 125, 960, 1030), fill='#354351', width=2)
        for j, mode in enumerate(['path', 'goal']):
            x = 30+j*960; rows = states[mode]
            available = capture['modes'][mode]['steps']
            total_steps=max(by_step[mode])
            chosen = min(step, total_steps)
            chosen = max(s for s in available if s <= chosen)
            row = by_step[mode][chosen]
            done = step >= total_steps
            result = selection['modes'][mode]['evaluation']
            title = '有 System1 路径 + System0' if mode == 'path' else '仅目标位姿 + System0（无路径）'
            text(x, 125, title, 29, colors[mode], True)
            if a.wrist_layout:
                im.paste(panel(mode,chosen,'wrist_focus'),(x,175))
                full=panel(mode,chosen,'wrist').resize((440,248),Image.Resampling.LANCZOS)
                fd=ImageDraw.Draw(full);crop=selection['wrist_crop'];scale=440/capture['wrist']['projection']['image_size'][0]
                fd.rectangle(tuple(round(v*scale) for v in crop),outline=colors[mode],width=2)
                im.paste(full,(x,735))
                im.paste(panel(mode,chosen,'detail').resize((440,264),Image.Resampling.LANCZOS),(x+460,735))
                for px,py,label in [(x+12,188,'腕部相机 · 插接区域'),(x+10,745,'完整腕图 · 方框为上方区域'),(x+470,745,'同步外部近景')]:
                    d.rectangle((px-3,py-2,px+len(label)*20,py+31),fill=bg);text(px,py,label,19)
            else:
                im.paste(panel(mode, chosen, 'detail'), (x, 175))
                d.rectangle((x+12, 188, x+160, 224), fill=bg)
                text(x+21, 190, '孔口固定近景', 20)
                im.paste(panel(mode, chosen, 'overview').resize((400, 300), Image.Resampling.LANCZOS), (x, 735))
                d.rectangle((x+8, 743, x+158, 777), fill=bg)
                text(x+17, 745, '机器人全景', 20)
            mx = x+425
            failure = {'ik_action_rejected': '失败：IK 拒绝动作',
                       'entrance_not_qualified': '失败：入口对准未通过',
                       'large_contact_point_penetration': '失败：接触保护触发',
                       'timeout': '失败：超时'}.get(result['failure'], '失败：'+str(result['failure']))
            status = ('已成功插入' if result['success'] else failure) if done else '自主执行中'
            status_color = ('#81e4af' if result['success'] else '#ffa59b') if done else colors[mode]
            if a.wrist_layout:
                d.rectangle((x,665,x+900,715),fill=bg)
                text(x+12,672,status,24,status_color,True)
                if correction:
                    c=correction[mode][chosen]
                    text(x+365,676,f'横偏 {c["lateral_mm"]:+.1f} mm  俯仰 {c["pitch_deg"]:+.1f}°  偏航 {c["yaw_deg"]:+.1f}°',18)
                else:text(x+410,674,f'深度 {row["insertion_depth_mm"]:.2f} mm   姿态 {np.rad2deg(row["alignment_angle_rad"]):.2f}°',22)
                text(x,1008,f'步 {chosen}/{total_steps} · {chosen/10:.1f} 秒 · 接管 0 次'+(' · 已结束，保持末帧' if done else ''),22,muted)
            else:
                text(mx, 740, status, 28, status_color, True)
                text(mx, 789, f'控制步  {chosen} / {total_steps}', 24)
                text(mx, 829, f'插入深度  {row["insertion_depth_mm"]:.2f} mm', 24)
                if correction:
                    c=correction[mode][chosen]
                    text(mx,869,f'夹爪横偏  {c["lateral_mm"]:+.2f} mm',24)
                    text(mx,909,f'俯仰 {c["pitch_deg"]:+.1f}° / 偏航 {c["yaw_deg"]:+.1f}°',24)
                else:
                    text(mx, 869, f'横向偏差  {row["lateral_error_mm"]:.2f} mm', 24)
                    text(mx, 909, f'姿态偏差  {np.rad2deg(row["alignment_angle_rad"]):.2f}°', 24)
                text(mx, 949, '规则接管  0 次', 24)
                text(mx, 995, '回合已结束，保持末帧' if done else f'仿真时间  {chosen/10:.1f} 秒', 20, muted)
        footer='原腕部相机位置与鱼眼投影 · 固定区域高清重渲染 · 完整腕图与外部视角同步 · 沿用同一执行记录' if a.wrist_layout else f'PhysX 执行记录重渲染 · 同步按控制步播放 · 训练种子 {selection["training_seed"]} / 测试 {selection["evaluation_seed"]} · 单例不代表总体成功率'
        if correction:footer=f'数值为实际夹爪偏差，0对应目标轴／姿态 · 左右同初态，无接管 · 画面采样 {10/stride:g} Hz，按仿真时间 {playback_speed:g}× 播放'
        text(30, 1044, footer, 19, muted)
        return im

    command = ['ffmpeg', '-v', 'error', '-n', '-f', 'rawvideo', '-pixel_format', 'rgb24',
               '-video_size', '1920x1080', '-framerate', str(fps), '-i', '-', '-an',
               '-c:v', 'libx264', '-preset', 'fast', '-crf', '19', '-pix_fmt', 'yuv420p',
               '-movflags', '+faststart', str(output)]
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    frames = 0
    try:
        start_hold=round(selection.get('start_hold_seconds',1.5)*fps)
        for step in [*[timeline[0]]*start_hold, *timeline, *[timeline[-1]]*25]:
            im = frame(step); process.stdin.write(im.tobytes()); frames += 1
            if frames % 50 == 0: print('ENCODE', frames, flush=True)
        process.stdin.close()
        if process.wait() != 0: raise RuntimeError('ffmpeg failed')
    except BaseException:
        process.kill(); process.wait(); raise
    frame(341).save(run/'preview.jpg', quality=95)
    frame(timeline[0]).save(run/'start.jpg', quality=95)
    frame(timeline[-1]).save(run/'end.jpg', quality=95)
    report = dict(video=str(output), frames=frames, fps=fps, duration_seconds=frames/fps,
                  playback_speed=playback_speed, start_hold_seconds=start_hold/fps, end_hold_seconds=2.5,
                  input_sampling_control_steps=stride,frames_held_between_samples=timeline_step<stride,
                  layout='wrist-focus-full-external' if a.wrist_layout else 'external-detail-overview',
                  completed_side_holds_final_frame=True, missing_frames_interpolated=False,
                  source=selection, capture=capture,
                  sha256=hashlib.sha256(output.read_bytes()).hexdigest())
    if correction:report['correction_metrics_sha256']=hashlib.sha256(Path(selection['correction_metrics']).read_bytes()).hexdigest()
    (run/'video_manifest.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(dict(video=str(output), duration=frames/fps)), flush=True)


if __name__ == '__main__': main()
