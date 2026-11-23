"""Build same-view image comparisons and force plots from recorded experiments."""
import argparse
import json
from pathlib import Path


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    import numpy as np
    from PIL import Image,ImageDraw,ImageFont
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    font='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
    title_font=ImageFont.truetype(font,28);small_font=ImageFont.truetype(font,22)
    variants=[('旧采样：128×128放大','image_ablation/baseline_128'),
              ('原生768×768＋DLAA','image_ablation/native_768'),
              ('原生高分辨率＋分材质/光照','image_refined_r03/refined_768')]
    for camera in ['wrist_rgb','head_rgb']:
        canvas=Image.new('RGB',(1536,860),'#14202b');draw=ImageDraw.Draw(canvas)
        draw.text((18,10),'同一相机、同一姿态；下排是同区域放大，未做后期锐化',font=title_font,fill='white')
        for col,(label,folder) in enumerate(variants):
            im=Image.open(a.root/folder/f'{camera}.png').convert('RGB')
            canvas.paste(im.resize((512,512),Image.Resampling.BICUBIC),(col*512,90))
            draw.text((col*512+12,58),label,font=small_font,fill='white')
            # Same normalized region covers the mouth and surrounding small parts.
            box=tuple(round(v*im.width) for v in (.40,.31,.91,.66))
            crop=im.crop(box);height=round(crop.height*512/crop.width)
            canvas.paste(crop.resize((512,height),Image.Resampling.BICUBIC),(col*512,610))
        canvas.save(a.output/f'{camera}_comparison.png')
    canvas=Image.new('RGB',(1920,780),'#14202b');draw=ImageDraw.Draw(canvas)
    for col,(label,folder) in enumerate(variants):
        label=['旧全景640×480','原生全景1280×960','分材质和光照候选'][col]
        im=Image.open(a.root/folder/'overview.png').convert('RGB')
        canvas.paste(im.resize((640,480),Image.Resampling.LANCZOS),(col*640,60))
        draw.text((col*640+12,16),label,font=small_font,fill='white')
    draw.text((24,575),'清晰度改善已验证；材质/光照为渲染近似，尚未完成真机成像标定。',font=title_font,fill='white')
    draw.text((24,630),'继续使用SIM-r06/旧URDF工具，未把WG-r09或真实腕部鱼眼自动接入。',font=title_font,fill='white')
    canvas=canvas.crop((0,0,1920,700));canvas.save(a.output/'overview_comparison.png')
    base=Path('/data/omi_runtime/runs/isaac_contact_development_20261122/pgs_robot/robot_video')
    new=a.root/'gentle_seed7'
    traces=[('Baseline',json.loads((base/'trajectory.json').read_text())),('Gentle approach',json.loads((new/'trajectory.json').read_text()))]
    fig,axes=plt.subplots(1,2,figsize=(12,4.2))
    stats=[]
    for name,rows in traces:
        ins=[x for x in rows if x['phase']=='insert'];first=next(x['step'] for x in ins if x['shoulder_contact'])
        for ax,key in zip(axes,['contact_force_N','step_peak_contact_force_N']):
            ax.plot([(x['step']-first)*.1 for x in ins],[x[key] for x in ins],label=name,linewidth=2)
            ax.set_xlim(-1.5,.3);ax.set_xlabel('Time relative to first shoulder contact (s)');ax.set_ylabel('N');ax.grid(alpha=.25)
        stats.append(dict(name=name,control_peak_N=max(x['contact_force_N'] for x in rows),
            physical_step_peak_N=max(x['step_peak_contact_force_N'] for x in rows)))
    axes[0].axhline(10,color='red',linestyle='--',label='Control-sampled 10 N gate')
    axes[0].set_title('Control-time sample (10 Hz)');axes[1].set_title('Peak within each 0.1 s control interval')
    for ax in axes:ax.legend()
    fig.suptitle('Seed 7: same geometry / PGS / 0.2 ms physics; success thresholds unchanged')
    fig.tight_layout();fig.savefig(a.output/'contact_force_comparison.png',dpi=180);fig.savefig(a.output/'contact_force_comparison.pdf');plt.close(fig)
    cases=[]
    for name in ['gentle_seed7','gentle_seed19','gentle_seed41','gentle_half_seed7','gentle_refined_video_r03']:
        report=a.root/name/'report.json'
        if not report.exists():continue
        r=json.loads(report.read_text());rows=json.loads((report.parent/'trajectory.json').read_text())
        cases.append(dict(case=name,accepted=r['accepted'],phases=r['phases'],dt=r['dt'],
            max_control_force_N=max(x['contact_force_N'] for x in rows),max_physics_step_force_N=max(x['step_peak_contact_force_N'] for x in rows),
            max_penetration_mm=max(x['step_peak_penetration_mm'] for x in rows),force_gate_N=r.get('control_force_limit_N'),
            report=str(report),renderer_executed=r['renderer_executed']))
    (a.output/'summary.json').write_text(json.dumps(dict(seed7_comparison=stats,cases=cases,
        image_scope='Same-pose native-resolution render ablations; no real-camera photometric calibration',
        source_normals_mapping='Rejected due to shading artifacts; automatic geometry normals used',
        added_grain_texture=False),indent=2)+'\n')


if __name__=='__main__':main()
