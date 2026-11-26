"""Wide asset scenes and outlined gradient paths for distant System1 probes."""
import argparse
import json
from pathlib import Path
import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from render_system1_assets import prepare, label
from render_system1_paths import transform, project
from omi_shapeforge.sim.isaac_contact_kinematics import local_pose

INK=(27,39,55);MUTED=(101,118,137);BG=(246,248,251)
PRED=((25,106,194),(45,200,179));GT=((124,70,189),(210,126,219))


def dense(points, count=320):
    p=np.asarray(points,float)
    length=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]
    keep=np.r_[True,np.diff(length)>1e-10];p=p[keep];length=length[keep]
    if len(p)<2:return np.repeat(p,count,axis=0)
    t=np.linspace(0,length[-1],count)
    return np.stack([np.interp(t,length,p[:,i]) for i in range(p.shape[1])],axis=1)


def ribbon(im, points, colors, width=10, dashed=False):
    aa=3
    layer=Image.new('RGBA',(im.width*aa,im.height*aa),(0,0,0,0))
    p=np.asarray(points,float)*aa;d=ImageDraw.Draw(layer);width*=aa
    def segments():
        arc=0.
        for i,(a,b) in enumerate(zip(p[:-1],p[1:])):
            if not np.isfinite([a,b]).all() or np.linalg.norm(a-b)>500*aa:continue
            arc+=np.linalg.norm(a-b)
            if dashed and int(arc/(16*aa))%3==2:continue
            yield i,a,b
    for _,a,b in segments():
        d.line([tuple(a),tuple(b)],fill=(255,255,255),width=width+6*aa)
        r=(width+6*aa)/2
        for x,y in (a,b):d.ellipse((x-r,y-r,x+r,y+r),fill='white')
    for i,a,b in segments():
        color=tuple(np.rint(np.array(colors[0])*(1-i/(len(p)-1))+np.array(colors[1])*i/(len(p)-1)).astype(int))
        d.line([tuple(a),tuple(b)],fill=color,width=width)
        r=width/2
        for x,y in (a,b):d.ellipse((x-r,y-r,x+r,y+r),fill=color)
    # Endpoint arrow, aligned with the projected path. No invented control points.
    if len(p)>8 and np.isfinite(p[-8:]).all():
        end=p[-1];v=end-p[-8];norm=np.linalg.norm(v)
        if norm>1e-3:
            v/=norm;n=np.array([-v[1],v[0]])
            tri=[end+v*4*aa,end-v*19*aa+n*12*aa,end-v*19*aa-n*12*aa]
            d.polygon([tuple(x) for x in tri],fill=colors[1])
    layer=layer.resize(im.size,Image.Resampling.LANCZOS)
    im.paste(layer,(0,0),layer)
    return im


def enrich(a):
    file=a.output/'scene_packet.json';s=json.loads(file.read_text())
    packet=json.loads((a.transfer/'transfer.json').read_text());m=packet['manifest']
    camera=next(c for c in packet['cameras'] if c['name']=='wrist_rgb')
    C=np.diag([1.,-1.,-1.,1.])@np.linalg.inv(local_pose(camera))
    K=np.array(m['observation_projection']['K']);D=np.array(m['observation_projection']['D'])
    for case in s['cases']:
        paths={}
        for key in ['pred','gt']:
            full=np.array(case['complete_paths_mm']['full_'+key])
            # Existing decoder uses 33 samples for each segment. Keep its exact
            # start-to-preinsert segment, not an aesthetic spline or GT substitute.
            paths[key]=dense(full[:33]).tolist()
        case['approach_mm']=paths
        case['approach_endpoint_error_mm']=float(np.linalg.norm(np.array(paths['pred'][-1])-paths['gt'][-1]))
        pixels={}
        for key,points in paths.items():
            tcp=transform(np.linalg.inv(case['socket_from_tcp']),np.array(points)/1000)
            uv,valid=project(tcp,C,K,D);uv[~valid]=np.nan
            pixels[key]=((uv+.5)*6.25-.5).tolist()
        case['approach_wrist_pixels']=pixels
    s['presentation']='full decoded approach, white-outline blue/teal prediction, dashed purple GT; no geometric smoothing'
    file.write_text(json.dumps(s,indent=2)+'\n')


def compose(root):
    s=json.loads((root/'scene_packet.json').read_text());cards=[]
    samples=np.load(Path(s['source_probes'])/'samples.npz',allow_pickle=False)
    for case in s['cases']:
        i=case['id'];q=case['summary']
        im=Image.new('RGB',(2400,1320),BG)
        label(im,(48,25),'SYSTEM1  /  远距离、未对准起点',40,INK)
        label(im,(50,90),f"孔口前 {q['requested_distance_mm']:.0f} mm    横向 {q['requested_lateral_mm']:+.0f} mm    高度 {q['requested_vertical_mm']:+.0f} mm    初始角度偏差 {q['actual_angular_offset_deg']:.1f}°",25,MUTED)
        label(im,(50,150),'3D  /  实体场景中的接近路径',28,INK)
        label(im,(1550,150),'2D  /  同一路径投影到腕图',28,INK)
        asset=Image.open(root/f'case_{i:02d}_wide.png').convert('RGB')
        proj=json.loads((root/f'case_{i:02d}_wide.json').read_text())
        ribbon(asset,proj['pixels']['gt'],GT,8,True);ribbon(asset,proj['pixels']['pred'],PRED,11)
        tip=proj['tip'];d=ImageDraw.Draw(asset)
        d.ellipse((tip[0]-9,tip[1]-9,tip[0]+9,tip[1]+9),fill='white',outline=INK,width=3)
        label(asset,(tip[0]+14,tip[1]+4),'起点',21,INK)
        asset.save(root/f'case_{i:02d}_wide_annotated.png')
        im.paste(asset,(50,205))
        raw=Image.fromarray(samples['images'][i,3:].transpose(1,2,0)).resize((800,800),Image.Resampling.LANCZOS)
        ribbon(raw,case['approach_wrist_pixels']['gt'],GT,8,True)
        ribbon(raw,case['approach_wrist_pixels']['pred'],PRED,11)
        current=np.asarray(case['wrist_pixels']['tip'][0]);current=(current+.5)*1.25-.5
        d=ImageDraw.Draw(raw);u,v=current
        d.ellipse((u-8,v-8,u+8,v+8),fill='white',outline=INK,width=3)
        raw.save(root/f'case_{i:02d}_wrist_ribbon.png');im.paste(raw,(1550,205))
        label(im,(1550,1020),'原始128×128模型输入放大；线条穿透遮挡',20,MUTED)
        d=ImageDraw.Draw(im)
        d.rounded_rectangle((50,1100,2350,1220),radius=18,fill=(233,239,245))
        d.line((80,1134,155,1134),fill=PRED[0],width=11)
        label(im,(175,1114),'蓝→青：当前模型预测',24,INK)
        d.line((650,1134,725,1134),fill=GT[0],width=9)
        label(im,(745,1114),'紫色虚线：GT几何参考',24,INK)
        label(im,(1400,1114),f"接近终点偏差 {case['approach_endpoint_error_mm']:.1f} mm",24,INK)
        label(im,(80,1166),'显示现有解码器的整段接近参考；加粗、描边与渐变只改变画法。',22,MUTED)
        label(im,(50,1250),'仿真已实际到达该起点；预测路径尚未执行。三维按同一记录重建，照明用于展示。',22,MUTED)
        im.save(root/f'case_{i:02d}_wide_comparison.png');cards.append(im.resize((1200,660),Image.Resampling.LANCZOS))
    board=Image.new('RGB',(1200,660*len(cards)),BG)
    for j,card in enumerate(cards):board.paste(card,(0,660*j))
    board.save(root/'far_starts.jpg',quality=95)
    # A separate equal-scale spatial plot reveals depth differences that a single
    # oblique asset view may hide. Positions are the exact same decoded samples.
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.font_manager import FontProperties
    from mpl_toolkits.mplot3d.art3d import Line3DCollection
    font=FontProperties(fname='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')
    fig=plt.figure(figsize=(18,6),facecolor='#f6f8fb')
    for j,case in enumerate(s['cases']):
        ax=fig.add_subplot(1,len(s['cases']),j+1,projection='3d',facecolor='#f6f8fb')
        for key,colors in [('gt',GT),('pred',PRED)]:
            points=np.array(case['approach_mm'][key]);points[:,1]-=s['mouth_y_mm']
            n=len(points)-1;t=np.linspace(0,1,n)[:,None]
            rgb=(np.array(colors[0])*(1-t)+np.array(colors[1])*t)/255
            lc=Line3DCollection(np.stack([points[:-1],points[1:]],axis=1),colors=rgb,linewidths=4 if key=='pred' else 2.5,linestyles='solid' if key=='pred' else 'dashed')
            ax.add_collection(lc);ax.scatter(*points[-1],color=[rgb[-1]],s=45)
        cx,cz=s['center_xz_mm'];w=s['channel_width_mm']/2;h=s['channel_height_mm']/2
        mouth=np.array([[cx-w,0,cz-h],[cx+w,0,cz-h],[cx+w,0,cz+h],[cx-w,0,cz+h],[cx-w,0,cz-h]])
        ax.plot(*mouth.T,color='#8794a1',linewidth=1.8)
        ax.set_xlim(-45,45);ax.set_ylim(-5,100);ax.set_zlim(-25,35);ax.set_box_aspect((90,105,60));ax.view_init(elev=26,azim=145)
        ax.set_xlabel('横向 / mm',fontproperties=font);ax.set_ylabel('孔口前距离 / mm',fontproperties=font);ax.set_zlabel('高度 / mm',fontproperties=font)
        ax.set_title(f"起点 {j+1} · {case['summary']['requested_distance_mm']:.0f} mm\n终点偏差 {case['approach_endpoint_error_mm']:.1f} mm",fontproperties=font,fontsize=15)
    fig.suptitle('同一批三维路径 · 等比例空间对照   蓝青：预测   紫色：GT   灰框：孔口',fontproperties=font,fontsize=18)
    fig.tight_layout(rect=(0,0,1,.88));fig.savefig(root/'paths_space.png',dpi=160);plt.close(fig)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['transfer','probes','output']:p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--compose-only',action='store_true')
    p.add_argument('--assets-only',action='store_true',help='Prepare/render bases for a downstream specialized presentation')
    a=p.parse_args()
    if not a.compose_only:
        a.cases=list(range(len(json.loads((a.probes/'report.json').read_text())['cases'])))
        prepare(a);enrich(a)
        subprocess.run(['blender','-b','-t','4','--python',str(Path(__file__).with_name('render_system1_far_blender.py')),'--',str(a.output)],check=True)
    if not a.assets_only:compose(a.output)


if __name__=='__main__':main()
