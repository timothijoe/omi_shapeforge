"""Frozen System1 holdout evaluation and 2D/3D reference visualization.

Network output is a relative socket pose; paths are decoded geometric references.
"""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
import torch
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT.parent/'omi_proj/src')]
from omi_shapeforge.sim.isaac_contact_kinematics import local_pose
from omi_hil_rl.training.hierarchical_insertion.reference import ReferenceProvider,ReferenceConfig,pose,exp_rotation,log_rotation
from omi_hil_rl.training.hierarchical_insertion.system1 import PoseNetwork,decode_pose,S1_VERSION
FONT='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
BG=(12,20,29);FG=(231,237,242);MUTED=(160,176,191);PRED=(255,174,68);GT=(97,218,169);CURRENT=(217,142,255);GRID=(65,80,96)

def text(im,xy,s,size=18,color=FG):ImageDraw.Draw(im).text(xy,s,font=ImageFont.truetype(FONT,size),fill=color)
def transform(t,p):return np.asarray(p)@t[:3,:3].T+t[:3,3]
def lines(im,p,color,width=3,dashed=False):
    d=ImageDraw.Draw(im)
    for i in range(len(p)-1):
        if np.isfinite(p[i:i+2]).all() and not(dashed and i%2):d.line([tuple(p[i]),tuple(p[i+1])],fill=color,width=width)

def project(points,cam,K,D):
    xyz=transform(cam,points);radius=np.linalg.norm(xyz[:,:2],axis=1);theta=np.arctan2(radius,xyz[:,2]);t2=theta**2
    td=theta*(1+D[0]*t2+D[1]*t2**2+D[2]*t2**3+D[3]*t2**4)
    xy=xyz[:,:2]*(td/np.maximum(radius,1e-12))[:,None]
    uv=xy*[K[0,0],K[1,1]]+[K[0,2],K[1,2]]
    sample=np.rint(np.linspace(0,388,128))
    pixel=np.column_stack([np.interp(uv[:,0]-766,sample,np.arange(128),left=-1000,right=1000),np.interp(uv[:,1]-566,sample,np.arange(128),left=-1000,right=1000)])
    return pixel,xyz[:,2]>.001

def references(manifest,socket,tip):
    provider=ReferenceProvider(manifest,ReferenceConfig());provider.reset(0)
    entry=socket@provider.local_entry;goal=socket@provider.local_goal
    provider.active=dict(start=np.eye(4),entry=entry,goal=goal,capture_step=0,version=1)
    f=provider.features(np.eye(4),0)
    short=np.stack([pose(v[:3]*.01,exp_rotation(v[3:]*.1))@tip for v in f[:48].reshape(8,6)])[:,:3]
    full=[]
    axis=goal[:3,3]-entry[:3,3];length=np.linalg.norm(axis);axis/=length
    progress=-entry[:3,3]@axis
    segments=((np.eye(4),entry),(entry,goal)) if progress<0 else ((pose(entry[:3,3]+axis*np.clip(progress,0,length),goal[:3,:3]),goal),)
    for start,end in segments:
        angle=log_rotation(start[:3,:3].T@end[:3,:3])
        for a in np.linspace(0,1,33):
            t=pose((1-a)*start[:3,3]+a*end[:3,3],start[:3,:3]@exp_rotation(a*a*(3-2*a)*angle));full.append((t@tip)[:3])
    return short,np.array(full)

def camera_panel(row,cam,K,D,tip):
    size=512
    im=Image.fromarray(row['image'][3:].transpose(1,2,0)).resize((size,size),Image.Resampling.LANCZOS)
    for key,color,width,dashed in [('full_gt',(93,141,127),1,True),('full_pred',(139,113,77),1,True),('gt',GT,3,True),('pred',PRED,3,False)]:
        uv,valid=project(row[key],cam,K,D);uv=(uv+.5)*4-.5
        for i in range(len(uv)-1):
            if valid[i:i+2].all() and (not dashed or i%2==0):lines(im,uv[i:i+2],color,width)
        if key in ('gt','pred'):
            d=ImageDraw.Draw(im)
            for u,v in uv[valid]:
                if 0<=u<size and 0<=v<size:d.ellipse((u-3,v-3,u+3,v+3),fill=color)
    uv,valid=project(tip[None,:3],cam,K,D)
    if valid[0]:
        u,v=(uv[0]+.5)*4-.5;ImageDraw.Draw(im).ellipse((u-5,v-5,u+5,v+5),outline=CURRENT,width=2)
    return im

def scene_panel(row,tip,m):
    size=512;im=Image.new('RGB',(size,size),BG);d=ImageDraw.Draw(im);inverse=np.linalg.inv(row['gt_socket'])
    def task(x):
        q=transform(inverse,x)*1000;return np.column_stack([q[:,0],m['mouth_y_mm']-q[:,1],q[:,2]])
    yaw=np.deg2rad(-38);pitch=np.deg2rad(25)
    basis=np.array([[np.cos(yaw),-np.sin(yaw),0],[-np.sin(yaw)*np.sin(pitch),-np.cos(yaw)*np.sin(pitch),np.cos(pitch)]])
    current=task(tip[None,:3])[0]
    center=current+np.array([0.,2.,0.])
    def screen(x):
        a=(np.asarray(x)-center)@basis.T;return np.column_stack([size/2+a[:,0]*30,size/2-a[:,1]*30])
    w=m['channel_width_mm']/2;h=m['channel_height_mm']/2;cx,cz=m['nominal_module_center_xz_mm']
    mouth=np.array([[cx-w,0,cz-h],[cx+w,0,cz-h],[cx+w,0,cz+h],[cx-w,0,cz+h],[cx-w,0,cz-h]])
    lines(im,screen(mouth),GT,2)
    for depth in np.arange(np.floor(current[1]/2)*2-4,np.floor(current[1]/2)*2+10,2):
        p=screen(np.array([[cx,depth,cz],[cx+.3,depth,cz]]));lines(im,p,GRID,1)
        if 40<p[1,0]<460 and 60<p[1,1]<425:text(im,tuple(p[1]),str(int(depth)),13,MUTED)
    lines(im,screen(np.array([[cx,0,cz],[cx,55,cz]])),GRID,1)
    for key,color,width,dash in [('full_gt',(93,141,127),1,True),('full_pred',(139,113,77),1,True),('gt',GT,3,True),('pred',PRED,3,False)]:
        p=screen(task(row[key]));lines(im,p,color,width,dash)
        if key in ('gt','pred'):
            for u,v in p:d.ellipse((u-3,v-3,u+3,v+3),fill=color)
    u,v=screen(task(tip[None,:3]))[0];d.ellipse((u-5,v-5,u+5,v+5),outline=CURRENT,width=2)
    d.rectangle((0,0,512,62),fill=BG)
    d.rectangle((0,435,512,512),fill=BG)
    text(im,(20,20),'短段局部放大 · 三轴等比例',17)
    # Orientation triad identifies lateral X, insertion depth and vertical Z.
    origin=np.array([420.,385.])
    for vec,label in (([1,0,0],'X'),([0,1,0],'深度'),([0,0,1],'Z')):
        delta=np.array(vec)@basis.T*40;end=origin+[delta[0],-delta[1]]
        lines(im,np.stack([origin,end]),MUTED,2);text(im,tuple(end),label,13,MUTED)
    text(im,(20,457),'刻度为插入深度 mm；视窗随当前尖端移动',15,MUTED)
    text(im,(20,482),'深色虚线：剩余参考   亮线：当前8点',15,MUTED)
    return im

def compose(row,cam,K,D,tip,m):
    im=Image.new('RGB',(1440,810),BG)
    text(im,(30,18),'System1 预测路径 · 独立回合回放',28)
    text(im,(30,65),'网络：双RGB → 插座相对位姿     路径：固定几何解码     动作：8个位姿参考点',18,MUTED)
    text(im,(30,109),'腕部图像叠加 · 原始128×128观测放大',19);text(im,(570,109),'三维参考 · 模块尖端的计划运动',19)
    im.paste(camera_panel(row,cam,K,D,tip),(30,150));im.paste(scene_panel(row,tip,m),(570,150))
    for y,s,c in [(160,'橙色实线  预测',PRED),(200,'绿色虚线  真值',GT),(240,'紫色圆点  当前尖端',CURRENT)]:text(im,(1110,y),s,18,c)
    text(im,(1110,306),f"回合 {row['seed']}");text(im,(1110,340),f"第 {row['index']} 帧")
    text(im,(1110,390),'位姿平移误差',18,MUTED);text(im,(1110,422),f"{row['translation_mm']:.3f} mm",25)
    text(im,(1110,468),'短段尖端误差均值',17,MUTED);text(im,(1110,501),f"{row['path_error_mm']:.3f} mm",25)
    text(im,(30,690),'只画未来参考，不代表机器人已经执行；遮挡后的参考线仍显示。',20)
    text(im,(30,730),'同一仿真资产的未训练回合；视频隔3帧取样、3×播放。未验证真机泛化。',18,MUTED)
    return im

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('checkpoint','dataset','transfer','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--stride',type=int,default=3);args=p.parse_args();args.output.mkdir(parents=True,exist_ok=False);torch.set_num_threads(2)
    packet=json.loads((args.transfer/'transfer.json').read_text());m=packet['manifest']
    state=torch.load(args.checkpoint,map_location='cpu',weights_only=True)
    assert state['version']==S1_VERSION and state['transfer_sha256']==hashlib.sha256((args.transfer/'transfer.json').read_bytes()).hexdigest()
    model=PoseNetwork().eval();model.load_state_dict(state['model']);meta=json.loads((args.dataset/'dataset.json').read_text())
    assert not set(state['training_seeds']+state['validation_seeds'])&{r['seed'] for r in meta['episodes']},'holdout overlaps training/selection'
    camera=next(c for c in packet['cameras'] if c['name']=='wrist_rgb')
    assert camera['body']==next(s for s in packet['sites'] if s['name']=='urdf_tcp_L')['body']
    cam=np.diag([1.,-1.,-1.,1.])@np.linalg.inv(local_pose(camera));K=np.array(m['observation_projection']['K']);D=np.array(m['observation_projection']['D'])
    tip=pose(m['tool_to_module']['position_m'],m['tool_to_module']['rotation'])@np.array([0,m['leading_tip_y_mm']/1000,0,1.])
    rows=[];errors=[];angles=[];patherrors=[];episodes=[]
    for ep in meta['episodes']:
        file=args.dataset/ep['file'];assert hashlib.sha256(file.read_bytes()).hexdigest()==ep['sha256']
        with np.load(file,allow_pickle=False) as data:images=data['images'];labels=data['labels']
        with torch.inference_mode():pred=torch.cat([model.predict(torch.from_numpy(images[i:i+32])) for i in range(0,len(images),32)]).numpy()
        eplist=[]
        for i,(x,y) in enumerate(zip(pred,labels)):
            gt=decode_pose(y);prediction=decode_pose(x);gp,gf=references(m,gt,tip);pp,pf=references(m,prediction,tip)
            e=float(np.linalg.norm(x[:3]-y[:3])*1000);angle=float(np.rad2deg(np.linalg.norm(log_rotation(gt[:3,:3].T@prediction[:3,:3]))));pe=float(np.linalg.norm(pp-gp,axis=1).mean()*1000)
            rows.append(dict(seed=ep['seed'],index=i,image=images[i],gt_socket=gt,pred_socket=prediction,gt=gp,pred=pp,full_gt=gf,full_pred=pf,translation_mm=e,path_error_mm=pe))
            errors.append(e);angles.append(angle);patherrors.append(pe);eplist.append(e)
        episodes.append(dict(seed=ep['seed'],frames=len(images),translation_mean_mm=float(np.mean(eplist))))
    report=dict(checkpoint=str(args.checkpoint),checkpoint_sha256=hashlib.sha256(args.checkpoint.read_bytes()).hexdigest(),selected_epoch=state['selected_epoch'],test_episodes=episodes,test_frames=len(rows),
        translation_mean_mm=float(np.mean(errors)),translation_p90_mm=float(np.percentile(errors,90)),translation_max_mm=float(max(errors)),rotation_mean_deg=float(np.mean(angles)),
        preview_tip_error_mean_mm=float(np.mean(patherrors)),preview_tip_error_p90_mm=float(np.percentile(patherrors,90)),
        output_semantics='network predicts socket pose; 8-point path and remaining reference generated by existing geometry decoder',scope='held-out seeds in same narrow simulation domain; no policy rollout or real-robot result',
        preview_metric_limit='path projection and clipping can suppress axial pose errors; preview error is not endpoint accuracy or task success',
        video_stride=args.stride,video_fps=10,video_playback_rate=args.stride,
        projection=dict(camera='wrist',source_pixels=[128,128],sensor_roi=[766,566,1155,955],sampling='inverse interpolation of rint(linspace(0,388,128))',path='module tip, not TCP origin',occlusion='reference shown through occlusion'))
    (args.output/'evaluation.json').write_text(json.dumps(report,indent=2)+'\n')
    first_episode=[(i,r) for i,r in enumerate(rows) if r['seed']==episodes[0]['seed']]
    entry_index=min(first_episode,key=lambda item:abs(m['mouth_y_mm']-transform(np.linalg.inv(item[1]['gt_socket']),tip[None,:3])[0,1]*1000))[0]
    selected=[int(np.argmax(errors)),entry_index,len(rows)//2];thumb=Image.new('RGB',(1440,2430),BG)
    for j,(name,index) in enumerate(zip(('worst','entry','middle'),selected)):
        im=compose(rows[index],cam,K,D,tip,m);im.save(args.output/(name+'.png'));thumb.paste(im,(0,j*810))
    thumb.resize((1200,2025),Image.Resampling.LANCZOS).save(args.output/'overview.jpg',quality=92)
    first=[r for r in rows if r['seed']==episodes[0]['seed']][::args.stride]
    proc=subprocess.Popen(['ffmpeg','-y','-v','error','-f','rawvideo','-pix_fmt','rgb24','-s','1440x810','-r','10','-i','-','-an','-c:v','libx264','-crf','20','-pix_fmt','yuv420p','-movflags','+faststart',str(args.output/'system1_paths.mp4')],stdin=subprocess.PIPE)
    try:
        for row in first:proc.stdin.write(np.asarray(compose(row,cam,K,D,tip,m)).tobytes())
    finally:proc.stdin.close()
    assert proc.wait()==0
    np.savez_compressed(args.output/'predictions.npz',predicted_socket=np.stack([r['pred_socket'] for r in rows]),target_socket=np.stack([r['gt_socket'] for r in rows]),predicted_preview_tip=np.stack([r['pred'] for r in rows]),target_preview_tip=np.stack([r['gt'] for r in rows]),seed=np.array([r['seed'] for r in rows]),frame=np.array([r['index'] for r in rows]))
    print(json.dumps(report),flush=True)
if __name__=='__main__':main()
