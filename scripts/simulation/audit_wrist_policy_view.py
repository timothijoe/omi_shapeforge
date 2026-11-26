"""Audit calibrated-coordinate wrist replay and deliver the inspected video."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from omi_shapeforge.sim.isaac_contact_kinematics import Kinematics,local_pose
from omi_shapeforge.sim.wrist_fisheye import CV_TO_GL


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',type=Path,required=True)
    p.add_argument('--delivery',type=Path,required=True)
    a=p.parse_args();r=a.run
    read=lambda p:json.loads(p.read_text())
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    assert read(r/'result.json')['complete']
    selection=read(r/'selection.json');capture=read(r/'capture/capture_report.json');video=read(r/'video_manifest.json')
    packet=read(Path(selection['transfer'])/'transfer.json');projection=packet['manifest']['observation_projection']
    assert capture['wrist']['projection']==projection
    context=capture['wrist'].get('context_projection',projection)
    context_sx=context['image_size'][0]/projection['image_size'][0]
    context_sy=context['image_size'][1]/projection['image_size'][1]
    np.testing.assert_allclose(context['K'],np.array([[context_sx,0.,(context_sx-1)/2],[0.,context_sy,(context_sy-1)/2],[0.,0.,1.]])@np.array(projection['K']),rtol=0,atol=1e-9)
    assert context['D']==projection['D']
    assert capture['wrist']['focus_crop']==selection['wrist_crop']
    kin=Kinematics(packet);q={j['name']:packet['initial_qpos'][j['qpos_index']] for j in packet['joints']}
    frames=kin.frames(q);camera=next(c for c in packet['cameras'] if c['name']=='wrist_rgb')
    expected=np.linalg.inv(kin.tcp(q))@frames[camera['body']]@local_pose(camera)
    expected[:3,:3]=expected[:3,:3]@CV_TO_GL
    x0,y0,x1,y1=selection['wrist_crop'];sx=900/(x1-x0);sy=540/(y1-y0)
    focus=capture['wrist']['focus_projection']
    np.testing.assert_allclose(focus['K'],np.array([[sx,0,-sx*x0],[0,sy,-sy*y0],[0,0,1]])@np.array(projection['K']),rtol=0,atol=1e-9)
    assert focus['D']==projection['D'] and focus['image_size']==[900,540]
    count=0;max_attachment=0.;max_world_position_mm=0.;max_world_rotation=0.
    for mode,source in selection['modes'].items():
        assert sha(Path(source['states']))==source['states_sha256']
        assert sha(Path(source['model']))==source['model_sha256']
        rows=read(Path(source['states']));by_step={x['step']:x for x in rows}
        stride=capture['stride'];assert stride in (1,2,3)
        assert capture['modes'][mode]['steps']==sorted(set([*range(0,rows[-1]['step']+1,stride),rows[-1]['step']]))
        for step in capture['modes'][mode]['steps']:
            frame=r/'capture'/mode/f'{step:04d}';pose=read(frame/'wrist_pose.json');row=by_step[step]
            assert pose['source_step']==step and row['teacher_requests']==0
            measured=np.eye(4);measured[:3,:3]=row['tcp_rotation'];measured[:3,3]=row['tcp_position']
            expected_world=measured@expected;actual=np.array(pose['world_from_wrist_cv'])
            attachment=float(abs(np.array(pose['tcp_from_wrist_cv'])-expected).max())
            position=float(np.linalg.norm(actual[:3,3]-expected_world[:3,3])*1000)
            rotation=float(abs(actual[:3,:3]-expected_world[:3,:3]).max())
            assert attachment<1e-9 and position<.01 and rotation<1e-5
            max_attachment=max(max_attachment,attachment);max_world_position_mm=max(max_world_position_mm,position);max_world_rotation=max(max_world_rotation,rotation)
            for name,size in [('wrist',tuple(context['image_size'])),('wrist_focus',(900,540))]:
                with Image.open(frame/(name+'.jpg')) as image:
                    assert image.size==size;image.verify()
            count+=1
    path=r/'system1_vs_system0.mp4';assert sha(path)==video['sha256']
    assert video['playback_speed']==1 and video['fps']==10 and video['layout']=='wrist-focus-full-external'
    assert video.get('input_sampling_control_steps',1)==capture['stride']
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=width,height,nb_frames,avg_frame_rate','-show_entries','format=duration','-of','json',str(path)]))
    assert probe['streams'][0]['width']==1920 and probe['streams'][0]['height']==1080
    assert int(probe['streams'][0]['nb_frames'])==video['frames'] and probe['streams'][0]['avg_frame_rate']=='10/1'
    assert abs(float(probe['format']['duration'])-video['duration_seconds'])<.001
    subprocess.run(['ffmpeg','-v','error','-i',str(path),'-f','null','-'],check=True)
    a.delivery.mkdir(exist_ok=False,parents=True)
    target=a.delivery/'Wrist_View_Pitch_Demo.mp4';shutil.copy2(path,target)
    for name in ['start.jpg','preview.jpg','end.jpg']:shutil.copy2(r/name,a.delivery/name)
    assert sha(target)==sha(path)
    report=dict(complete=True,delivery=str(target),duration_seconds=video['duration_seconds'],video_sha256=sha(path),
        wrist_frames_verified=count,original_camera_attachment_verified=True,original_fisheye_projection_verified=True,
        fixed_crop_verified=True,policy_states_and_weights_unchanged=True,full_video_decode_passed=True,
        max_camera_attachment_matrix_error=max_attachment,max_camera_world_position_error_mm=max_world_position_mm,
        max_camera_world_rotation_matrix_error=max_world_rotation,
        scope='wrist-view re-render of existing simulation states; no new trial or camera relocation; not original actor input pixels')
    (r/'delivery_manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
