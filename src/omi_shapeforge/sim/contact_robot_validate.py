"""Validate robot insertion and withdrawal with contact sampled every physics step."""
import argparse
import json
from pathlib import Path
import subprocess

import imageio.v2 as imageio
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .contact_env import ContactInsertionEnv
from .contact_teacher import ContactInsertionTeacher


def panel(env,info,phase,step):
    canvas=Image.new('RGB',(1024,576),'#101821')
    canvas.paste(Image.fromarray(env.render_overview()),(0,38))
    for camera,y in [('head_rgb',32),('wrist_rgb',296)]:
        canvas.paste(Image.fromarray(env.render_camera(camera)).resize((256,256),Image.Resampling.NEAREST),(736,y))
    font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',18)
    draw=ImageDraw.Draw(canvas)
    draw.text((16,10),f"{env.manifest['asset_id']} | real URDF | contact active",font=font,fill='white')
    draw.text((664,64),'HEAD',font=font,fill='#7dc7ff');draw.text((652,328),'WRIST',font=font,fill='#7dc7ff')
    draw.text((16,528),f"{phase.upper()} | step {step} | depth {info['insertion_depth_mm']:.2f} / 51.28 mm",font=font,fill='white')
    draw.text((16,552),f"Contact {info.get('contact_force_N',0):.2f} N | equivalent spring pads | fixed attachment",font=font,fill='#aabaca')
    return np.asarray(canvas)


def validate(scene,output,seeds=(7,19,41),render=True):
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    env=ContactInsertionEnv(scene,max_steps=350)
    summaries=[];frames=[]
    try:
        for index,seed in enumerate(seeds):
            obs,info=env.reset(seed=seed);teacher=ContactInsertionTeacher();rows=[]
            head_start=env.data.cam_xpos[env.model.camera('head_rgb').id].copy()
            wrist_start=env.data.cam_xpos[env.model.camera('wrist_rgb').id].copy()
            initial_q_right=np.array([env.data.joint(f'Arm_R{i}_Joint').qpos[0] for i in range(1,8)])
            if index==0 and render:frames.append(panel(env,info,'ready',0))
            max_peak,min_gap,max_force=0.,.4,0.
            phase_results={}
            for phase in ['insert','withdraw']:
                if phase=='withdraw':
                    if not info.get('is_success'):break
                    env.begin_withdrawal();teacher.reset()
                for step in range(env.max_steps):
                    action,controller=teacher.act(env)
                    before=env.data.time
                    nxt,reward,terminated,truncated,info=env.step(action)
                    assert abs(env.data.time-before-.1)<1e-8
                    assert not nxt['state'].any() and not nxt['tactile'].any()
                    np.testing.assert_array_equal(obs['rgb'][1:],nxt['rgb'][:-1])
                    np.testing.assert_array_equal(obs['wrist_rgb'][1:],nxt['wrist_rgb'][:-1])
                    obs=nxt
                    max_peak=max(max_peak,info['step_peak_penetration_mm'])
                    min_gap=min(min_gap,info['step_min_floor_gap_mm']);max_force=max(max_force,info['contact_force_N'])
                    rows.append(dict(step=step+1,phase=phase,action=action.tolist(),**{k:info[k] for k in (
                        'insertion_depth_mm','lateral_error_mm','alignment_angle_rad','penetration_mm','step_peak_penetration_mm',
                        'step_min_floor_gap_mm','contact_force_N','shoulder_contact','pad_travel_mm','is_success','failure')}))
                    if index==0 and render:frames.append(panel(env,info,phase,step+1))
                    if terminated or truncated:break
                phase_results[phase]=dict(steps=step+1,is_success=info['is_success'],depth_mm=info['insertion_depth_mm'])
            np.testing.assert_allclose(head_start,env.data.cam_xpos[env.model.camera('head_rgb').id],atol=1e-12)
            right=np.array([env.data.joint(f'Arm_R{i}_Joint').qpos[0] for i in range(1,8)])
            np.testing.assert_allclose(initial_q_right,right,atol=1e-8)
            row=dict(seed=seed,phases=phase_results,max_step_penetration_mm=max_peak,min_floor_gap_mm=min_gap,
                max_sampled_contact_force_N=max_force,final_pad_travel_mm=info['pad_travel_mm'],
                head_camera_fixed=True,causal_camera_history=True,right_arm_held=True,
                accepted=all(phase_results.get(k,{}).get('is_success',False) for k in ['insert','withdraw']) and max_peak<.05 and min_gap>.025)
            summaries.append(row);(output/f'cycle_{seed}.json').write_text(json.dumps(rows,indent=2)+'\n')
            print(json.dumps(row),flush=True)
        if frames:
            imageio.imwrite(output/'preview.png',frames[len(frames)//2])
            imageio.mimsave(output/'robot_contact_cycle.gif',frames,duration=100,loop=0)
            process=subprocess.Popen(['ffmpeg','-v','error','-n','-f','rawvideo','-pixel_format','rgb24','-video_size','1024x576',
                '-framerate','10','-i','-','-an','-c:v','libx264','-pix_fmt','yuv420p','-movflags','+faststart',str(output/'robot_contact_cycle.mp4')],stdin=subprocess.PIPE)
            for frame in frames:process.stdin.write(frame.tobytes())
            process.stdin.close()
            if process.wait():raise RuntimeError('video encoding failed')
        report=dict(asset_id=env.manifest['asset_id'],scene=str(scene),cases=summaries,all_passed=all(x['accepted'] for x in summaries),
                    scope='module/socket/pad/table contact with fixed tool attachment; robot self-contact and contact grasp not validated')
        (output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
        return report
    finally:env.close()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--scene',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();validate(a.scene,a.output)


if __name__=='__main__':main()
