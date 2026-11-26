"""Compare actual initial axial gaps with one fixed external camera."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image,ImageDraw,ImageFont


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--previous',type=Path,required=True)
    p.add_argument('--far-video-root',type=Path,required=True)
    a=p.parse_args();root=a.far_video_root
    read=lambda p:json.loads(p.read_text())
    font=lambda size:ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',size)
    camera=read(a.previous/'capture/capture_report.json')['cameras'][0]
    assert camera==read(root/'gap_40mm/preview/capture_report.json')['cameras'][0]
    _,eye,target,size,focal=camera;eye=np.array(eye);forward=np.array(target)-eye;forward/=np.linalg.norm(forward)
    right=np.cross(forward,[0.,0.,1.]);right/=np.linalg.norm(right);up=np.cross(right,forward)
    def project(point):
        delta=point-eye;z=delta@forward;assert z>0
        f=focal/36*size[0]
        return np.array([size[0]/2+f*(delta@right)/z,size[1]/2-f*(delta@up)/z])
    canvas=Image.new('RGB',(2340,720),'#101923');draw=ImageDraw.Draw(canvas)
    draw.text((30,20),'初始前后间距：原来 10 mm → 30 mm / 40 mm',font=font(40),fill='white')
    draw.text((30,78),'同一外部相机、同一俯仰 +2°；箭头表示实测轴向间隙',font=font(26),fill='#b5c6d4')
    records=[]
    for i,(run,label) in enumerate([(a.previous,'原来'),(root/'gap_30mm','额外后退 2 cm'),(root/'gap_40mm','额外后退 3 cm')]):
        selection=read(run/'selection.json');row=read(Path(selection['modes']['path']['states']))[0];assert row['step']==0
        packet=read(Path(selection['transfer'])/'transfer.json');m=packet['manifest'];tcp=np.eye(4);tcp[:3,:3]=row['tcp_rotation'];tcp[:3,3]=row['tcp_position']
        tool=np.eye(4);tool[:3,:3]=m['tool_to_module']['rotation'];tool[:3,3]=m['tool_to_module']['position_m']
        tip=(tcp@tool@np.array([0.,m['leading_tip_y_mm']/1000,0.,1.]))[:3]
        gap=-row['insertion_depth_mm'];axis=-np.array(row['socket_to_world']['rotation'])[:,1]
        plane=tip+axis*gap/1000;u,v=project(tip),project(plane)
        path=run/'capture/path/0000/detail.jpg'
        if not path.exists():path=run/'preview/path/0000/detail.jpg'
        image=Image.open(path).convert('RGB');d=ImageDraw.Draw(image)
        line=[tuple(u),tuple(v)];d.line(line,fill='white',width=9);d.line(line,fill='#03bfe4',width=5)
        delta=(v-u)/np.linalg.norm(v-u);normal=np.array([-delta[1],delta[0]])
        for point,direction in [(u,delta),(v,-delta)]:
            poly=[tuple(point),tuple(point+direction*14+normal*6),tuple(point+direction*14-normal*6)]
            d.polygon(poly,fill='#03bfe4')
        center=(u+v)/2;text=f'{gap:.2f} mm';box=d.textbbox((0,0),text,font=font(27));width=box[2]-box[0]+16
        x=float(center[0]-width/2);y=float(center[1]-47)
        d.rounded_rectangle((x,y,x+width,y+39),radius=5,fill='#101923');d.text((x+8,y+1),text,font=font(27),fill='white')
        px=20+i*780;draw.text((px+10,125),label,font=font(30),fill='#79ddf0')
        canvas.paste(image.resize((760,456),Image.Resampling.LANCZOS),(px,174))
        draw.text((px+10,643),f'实际间隙 {gap:.2f} mm · 真实第 0 步',font=font(25),fill='white')
        records.append(dict(run=str(run),actual_gap_mm=gap,image=str(path),image_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                            projected_tip=u.tolist(),projected_mouth_plane=v.tolist()))
    canvas.save(root/'initial_gap_comparison.jpg',quality=97,subsampling=0)
    (root/'initial_gap_comparison.json').write_text(json.dumps(dict(camera=camera,cases=records,
        scope='actual initial state axial gap; annotations on unchanged fixed-camera images'),indent=2))


if __name__=='__main__':main()
