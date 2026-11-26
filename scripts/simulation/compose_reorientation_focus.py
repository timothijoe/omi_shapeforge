"""Show opposite initial states correcting under the SAME path-conditioned actor.

Both columns use recorded policy states. This is an early correction excerpt,
not the path-versus-goal baseline comparison and not a complete insertion film.
"""
import argparse
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np
from PIL import Image,ImageDraw,ImageFont


@lru_cache(maxsize=20)
def font(size):return ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',size)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);p.add_argument('--seconds',type=int,default=15)
    a=p.parse_args();root=a.root;read=lambda p:json.loads(p.read_text());columns=[]
    camera=['detail',[.88,.47,1.015],[.625,.203,.807],[900,540],46]
    eye=np.array(camera[1]);forward=np.array(camera[2])-eye;forward/=np.linalg.norm(forward)
    right=np.cross(forward,[0.,0.,1.]);right/=np.linalg.norm(right);up=np.cross(right,forward);f=camera[4]/36*900
    def project(points):
        delta=np.asarray(points)-eye;depth=delta@forward;assert np.all(depth>0)
        return np.c_[450+f*(delta@right)/depth,270-f*(delta@up)/depth]
    for name,label in [('01_combined_plus','左偏 10 mm · 俯仰 +5° · 偏航 +5°'),('02_combined_minus','右偏 10 mm · 俯仰 −5° · 偏航 −5°')]:
        run=root/name;selection=read(run/'selection.json');source=selection['modes']['path']
        rows=read(Path(source['states']));assert hashlib.sha256(Path(source['states']).read_bytes()).hexdigest()==source['states_sha256']
        metrics=read(Path(selection['correction_metrics']));assert metrics['state_sha256']['path']==source['states_sha256']
        transform=np.array(source['evaluation']['initial_pose']['tcp_from_gripper']);gripper=[]
        for row in rows:
            t=np.eye(4);t[:3,:3]=row['tcp_rotation'];t[:3,3]=row['tcp_position'];gripper.append(t@transform)
        columns.append(dict(run=run,label=label,selection=selection,rows=rows,metrics=metrics['modes']['path'],gripper=gripper))
    assert columns[0]['selection']['modes']['path']['model_sha256']==columns[1]['selection']['modes']['path']['model_sha256']
    last=a.seconds*10;assert all(len(c['rows'])>last for c in columns)
    for c in columns:
        for step in range(0,last+1,2):assert (c['run']/'capture/path'/f'{step:04d}'/'wrist_pose.json').exists()
    bg='#101923';fg='#eef4f8';muted='#a4b5c3';colors=['#ff625e','#5ed78b','#6baeff']
    @lru_cache(maxsize=12)
    def panel(index,step,name):return Image.open(columns[index]['run']/'capture/path'/f'{step:04d}'/(name+'.jpg')).convert('RGB')
    def frame(step):
        selected=step-step%2;im=Image.new('RGB',(1920,1080),bg);d=ImageDraw.Draw(im)
        def text(x,y,t,size=23,color=fg):d.text((x,y),t,font=font(size),fill=color)
        text(30,18,'同一有路径模型 · 两种相反初态怎样调回',38)
        text(30,77,'起始约 40 mm · 实际执行前 15 秒 · 无接管 · 青线为夹爪中心轨迹，RGB 为当前朝向',24,muted)
        d.line((960,125,960,1040),fill='#354351',width=2)
        for j,c in enumerate(columns):
            x=30+960*j;text(x,128,c['label'],28,'#65d5ed')
            picture=panel(j,selected,'detail').copy();pd=ImageDraw.Draw(picture)
            transforms=c['gripper'];pts=project([t[:3,3] for t in transforms[:selected+1:2]])
            if len(pts)>1:
                pd.line([tuple(p) for p in pts],fill='white',width=7);pd.line([tuple(p) for p in pts],fill='#19c4df',width=3)
            t=transforms[selected];origin=project(t[:3,3][None])[0]
            for k,color in enumerate(colors):
                end=project((t[:3,3]+t[:3,k]*.015)[None])[0]
                pd.line((tuple(origin),tuple(end)),fill='white',width=6);pd.line((tuple(origin),tuple(end)),fill=color,width=3)
                delta=(end-origin)/np.linalg.norm(end-origin);normal=np.array([-delta[1],delta[0]])
                pd.polygon([tuple(end),tuple(end-10*delta+4*normal),tuple(end-10*delta-4*normal)],fill=color)
                pd.text(tuple(end+[4,-12]),'XYZ'[k],font=font(18),fill=color)
            im.paste(picture,(x,175))
            im.paste(panel(j,selected,'wrist_focus').resize((400,240),Image.Resampling.LANCZOS),(x,745))
            d.rectangle((x+8,753,x+166,786),fill=bg);text(x+15,755,'同步腕部局部',20)
            m=c['metrics'][selected];mx=x+425
            text(mx,742,f'实际横偏  {m["lateral_mm"]:+.2f} mm',28)
            text(mx,788,f'俯仰 {m["pitch_deg"]:+.2f}° / 偏航 {m["yaw_deg"]:+.2f}°',25)
            text(mx,834,f'上下偏差  {m["vertical_mm"]:+.2f} mm',24)
            text(mx,878,f'尖端距孔口  {-m["depth_mm"]:.2f} mm',24)
            text(mx,923,f'仿真时间 {selected/10:.1f} s · 控制步 {selected}',23,muted)
            text(x,1003,'红 X 向前 · 绿 Y 向左 · 蓝 Z 向上；坐标原点位于夹爪中心',21,muted)
        text(30,1046,'两侧都是有路径模型、不同初态；本片仅截取校正阶段，后续插入见完整 demo · 5 Hz画面采样，原速播放',19,muted)
        return im
    output=root/'Reorientation_First15s.mp4';command=['ffmpeg','-v','error','-n','-f','rawvideo','-pixel_format','rgb24','-video_size','1920x1080','-framerate','10','-i','-','-an','-c:v','libx264','-preset','fast','-crf','19','-pix_fmt','yuv420p','-movflags','+faststart',str(output)]
    proc=subprocess.Popen(command,stdin=subprocess.PIPE);timeline=[*[0]*30,*range(last+1),*[last]*25]
    try:
        for step in timeline:proc.stdin.write(frame(step).tobytes())
        proc.stdin.close();assert proc.wait()==0
    except BaseException:proc.kill();proc.wait();raise
    frame(0).save(root/'correction_start.jpg',quality=97,subsampling=0);frame(last).save(root/'correction_15s.jpg',quality=97,subsampling=0)
    report=dict(video=str(output),duration_seconds=len(timeline)/10,simulation_excerpt_seconds=a.seconds,
        both_columns='same path-conditioned frozen actor; opposite initial states; not the path/goal comparison',
        external_camera=camera,overlays='measured gripper-center trail and X/Y/Z axes, not the System1 reference',
        image_sampling_hz=5,playback_speed=1,scope='first 15 simulation seconds only; full insertion videos separate',
        cases=[dict(label=c['label'],selection=str(c['run']/'selection.json'),initial=c['metrics'][0],at_excerpt_end=c['metrics'][last]) for c in columns],
        sha256=hashlib.sha256(output.read_bytes()).hexdigest())
    (root/'focus_manifest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(video=str(output),seconds=len(timeline)/10)))


if __name__=='__main__':main()
