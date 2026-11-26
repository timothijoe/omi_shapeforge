"""One actor, one episode, synchronized external/wrist views with plain stages."""
import argparse
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import subprocess

from PIL import Image,ImageDraw,ImageFont


@lru_cache(maxsize=16)
def font(size):return ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',size)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    read=lambda p:json.loads(p.read_text());selection=read(a.run/'selection.json');source=selection['modes']['path']
    assert hashlib.sha256(Path(source['states']).read_bytes()).hexdigest()==source['states_sha256']
    rows=read(Path(source['states']));metrics=read(Path(selection['correction_metrics']))
    assert metrics['state_sha256']['path']==source['states_sha256'];values=metrics['modes']['path']
    capture=read(a.run/'capture/capture_report.json');available=capture['modes']['path']['steps']
    last=rows[-1]['step'];assert rows[-1]['is_success'] and source['evaluation']['success']
    assert [r['step'] for r in rows]==list(range(last+1)) and all(r['teacher_requests']==0 for r in rows)
    entry=next(r['step'] for r in rows if r['insertion_depth_mm']>=0)
    @lru_cache(maxsize=8)
    def picture(step,name):return Image.open(a.run/'capture/path'/f'{step:04d}'/(name+'.jpg')).convert('RGB')
    def frame(step):
        chosen=max(s for s in available if s<=step);row=rows[chosen];m=values[chosen]
        im=Image.new('RGB',(1920,1080),'#101923');d=ImageDraw.Draw(im)
        def text(x,y,t,size=26,color='#eef4f8'):d.text((x,y),t,font=font(size),fill=color)
        if chosen==0:title='① 起点：左偏 10 mm，俯仰和左右转向各偏 5°'
        elif row['is_success']:title='③ 插入完成'
        elif chosen>=entry:title='③ 进入孔口，继续插入'
        else:title='② 在孔外调整位置和角度，并逐步靠近'
        text(30,20,title,39)
        text(30,80,'一个有路径模型的一次完整动作 · 外部视角与腕部画面同步 · 全程无接管',25,'#afc1ce')
        im.paste(picture(chosen,'detail').resize((1260,756),Image.Resampling.LANCZOS),(30,165))
        d.rectangle((44,179,240,218),fill='#101923');text(54,180,'外部视角',25)
        text(1330,155,'同一动作的腕部画面',28,'#71d7ed')
        im.paste(picture(chosen,'wrist_focus').resize((560,336),Image.Resampling.LANCZOS),(1330,205))
        text(1330,585,'看这些偏差逐渐接近 0：',26,'#afc1ce')
        text(1330,642,f'左右偏差  {m["lateral_mm"]:+.2f} mm',31)
        text(1330,702,f'俯仰偏差  {m["pitch_deg"]:+.2f}°',31)
        text(1330,762,f'左右转向  {m["yaw_deg"]:+.2f}°',31)
        text(1330,837,f'仿真时间  {chosen/10:.1f} 秒',25,'#afc1ce')
        text(30,956,'开始时距孔口约 41 mm；轨迹来自实际策略执行，包含调整、接近和完整插入。',25)
        text(30,1005,'两个画面显示同一次动作 · 原速播放（5 Hz画面采样）· 本片不做有／无路径模型对比',23,'#afc1ce')
        return im
    timeline=[*[0]*30,*range(last+1),*[last]*25]
    command=['ffmpeg','-v','error','-n','-f','rawvideo','-pixel_format','rgb24','-video_size','1920x1080','-framerate','10','-i','-','-an','-c:v','libx264','-preset','fast','-crf','19','-pix_fmt','yuv420p','-movflags','+faststart',str(a.output)]
    process=subprocess.Popen(command,stdin=subprocess.PIPE)
    try:
        for step in timeline:process.stdin.write(frame(step).tobytes())
        process.stdin.close();assert process.wait()==0
    except BaseException:process.kill();process.wait();raise
    frame(0).save(a.output.with_suffix('.jpg'),quality=97,subsampling=0)
    report=dict(video=str(a.output),duration_seconds=len(timeline)/10,source_selection=str(a.run/'selection.json'),source_mode='path',
        model_sha256=source['model_sha256'],states_sha256=source['states_sha256'],actual_entry_step=entry,
        end_step=last,success=True,teacher_requests=0,layout='one episode; external view left and wrist view right',
        stages='initial / outside-mouth correction and approach / measured mouth crossing and insertion / recorded success',
        sha256=hashlib.sha256(a.output.read_bytes()).hexdigest())
    a.output.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))


if __name__=='__main__':main()
