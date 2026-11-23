"""Review real feature tracks, model bindings, and explicitly predicted geometry."""
import argparse
import json
from pathlib import Path
import cv2
import numpy as np
from PIL import Image,ImageDraw,ImageFont
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from mesh_feature_tracker import MeshSurface
from run_mesh_feature_tracking import make_camera


FONT='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'


def state_label(record):
    if record['state']=='initializing':return '初值绑定，精度待验证'
    if record['state']=='lost':return '位姿观测丢失，不输出新位姿'
    if record['state']=='prediction_only':return '短时预测，没有视觉更新'
    if record.get('measurement_dof_count')==2:return '仅二维更新，深度/朝向依赖先验'
    if record['state']=='prior_assisted_update':return '六参数更新，观测约束较弱'
    return '局部六维更新，绝对精度未验证'


class WireRenderer:
    def __init__(self,surface):
        self.surface=surface
        data=np.load('/data/omi_runtime/runs/pointcloud_v3_overlay_20261121_face_corrected/body_mesh.npz');self.V=data['vertices'];self.F=data['triangles']
        tri=self.V[self.F];norm=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);norm/=np.maximum(np.linalg.norm(norm,axis=1,keepdims=True),1e-12);adj={}
        for index,face in enumerate(self.F):
            for a,b in zip(face,np.roll(face,-1)):adj.setdefault(tuple(sorted([int(a),int(b)])),[]).append(index)
        self.samples=[]
        for edge,fs in adj.items():
            if len(fs)==2 and norm[fs[0]]@norm[fs[1]]>np.cos(.4):continue
            a,b=self.V[list(edge)];count=max(3,min(35,int(np.linalg.norm(b-a)/.002)+1));self.samples.append(np.linspace(a,b,count))
        self.points=np.concatenate(self.samples);self.ends=np.cumsum([len(p) for p in self.samples])

    def draw(self,image,camera,record,mask):
        out=image.copy()
        if record['state']=='lost':return out
        T=np.array(record['prediction_for_display_only']);uv=camera.project(self.points,T);cam=self.points@T[:3,:3].T+T[:3,3];pix=np.rint(uv).astype(int)
        valid=(pix[:,0]>=0)&(pix[:,0]<camera.width)&(pix[:,1]>=0)&(pix[:,1]<camera.height)&(cam[:,2]>0)
        visible=np.zeros(len(uv),bool)
        if valid.any():
            hit,_,ok=self.surface.intersect(uv[valid],camera,T);depth=(hit@T[:3,:3].T+T[:3,3])[:,2]
            visible[valid]=ok&(cam[valid,2]<=depth+.0004)
        observed=np.ones(len(uv),bool)
        if mask is not None:
            observed[:]=False;observed[valid]=mask[pix[valid,1],pix[valid,0]]>0
        if not record['measurement_update'] or record.get('measurement_dof_count',0)<6:observed[:]=False
        start=0
        for end in self.ends:
            for j in range(start,end-1):
                if not visible[j] or not visible[j+1]:continue
                strong=observed[j] and observed[j+1]
                if not strong and (j-start)%2:continue
                cv2.line(out,tuple(pix[j]),tuple(pix[j+1]),(0,185,255) if strong else (160,160,160),1,cv2.LINE_AA)
            start=end
        tip=camera.project([[0,-.035093169659,0]],T)[0]
        if 0<=tip[0]<camera.width and 0<=tip[1]<camera.height:
            cv2.drawMarker(out,tuple(np.rint(tip).astype(int)),(220,220,220),cv2.MARKER_TILTED_CROSS,5 if camera.width<256 else 9,1)
        return out


def features(image,record,small):
    out=image.copy()
    for f in record['features']:
        p=tuple(np.rint(f['native_xy']).astype(int));cv2.circle(out,p,1 if small else 2,(255,220,20) if f['head'] else (0,180,255),-1,cv2.LINE_AA)
    if 'head_patch_center_native_xy' in record:
        cv2.drawMarker(out,tuple(np.rint(record['head_patch_center_native_xy']).astype(int)),(230,100,230),cv2.MARKER_CROSS,5 if small else 9,1)
    return out


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=Path,required=True);p.add_argument('--results',default='tracking_final');a=p.parse_args();root=a.run;results=root/a.results
    data=json.loads((root/'cases.json').read_text());cal=json.loads(Path(data['calibration']).read_text());surface=MeshSurface(data['module_inputs']);wire=WireRenderer(surface)
    font=ImageFont.truetype(FONT,22);small=ImageFont.truetype(FONT,17)
    cases={x['id']:x for x in data['cases']}
    def annotated(case,record):
        image=cv2.imread(record['image']);camera=make_camera(case,cal)
        if record.get('mask'):mask=cv2.imread(record['mask'],0)
        elif 'phase' in record:mask=(~np.all(image==150,axis=2)).astype(np.uint8)*255
        else:mask=None
        return image,features(wire.draw(image,camera,record,mask),record,camera.width<=256)
    # Feature points shown on the image and in actual model coordinates.
    case=cases['full_fisheye_video'];atlas=json.loads((results/case['id']/'feature_atlas.json').read_text());image=cv2.imread(case['frames'][0]['image']);points=atlas['features'];fake={'features':[{'native_xy':f['reference_native_xy'],'head':f['rigid_head']} for f in points]};image=features(image,fake,False)
    fig=plt.figure(figsize=(5,6));ax=fig.add_subplot(projection='3d');mesh=wire.V*1000;ax.add_collection3d(Poly3DCollection(mesh[wire.F],facecolor='#adbac8',edgecolor='#5e6c7d',linewidth=.08,alpha=.2))
    q=np.array([f['model_xyz_m'] for f in points])*1000;colors=['#1bbddb' if f['rigid_head'] else '#efa433' for f in points];ax.scatter(q[:,0],q[:,1],q[:,2],c=colors,s=15,depthshade=False)
    ax.set(xlim=(-12,12),ylim=(-38,38),zlim=(-5,8),xlabel='X / mm',ylabel='Y / mm',zlabel='Z / mm');ax.set_box_aspect((24,76,13));ax.view_init(22,-56);fig.tight_layout();fig.savefig(results/'model_feature_points.png',dpi=130);plt.close(fig)
    canvas=Image.new('RGB',(1180,800),'#15212e');d=ImageDraw.Draw(canvas);d.text((18,15),'光模块候选特征：图像跟踪已实现，三维绑定待核对',font=font,fill='white')
    photo=Image.fromarray(cv2.cvtColor(image,cv2.COLOR_BGR2RGB));photo.thumbnail((510,640));canvas.paste(photo,(25,80));model=Image.open(results/'model_feature_points.png').convert('RGB');model.thumbnail((620,640));canvas.paste(model,(535,80));d.text((18,730),f"{atlas['feature_count']} 个特征，{atlas['head_feature_count']} 个绑定到模型头部；绿色挂件未使用。",font=small,fill='#ffc56d');d.text((18,760),'绑定依赖初始位姿；这里展示对应关系，不是绝对标定或六维精度认证。',font=small,fill='white');canvas.save(results/'feature_atlas_review.png')
    def movie(case,records,dest,title):
        writer=cv2.VideoWriter(str(dest),cv2.VideoWriter_fourcc(*'mp4v'),10.,(1080,720))
        for record in records:
            original,overlay=annotated(case,record);frame=Image.new('RGB',(1080,720),'#15212e');draw=ImageDraw.Draw(frame);draw.text((18,12),title,font=font,fill='white');draw.text((18,47),'原图',font=small,fill='white');draw.text((555,47),'特征＋模型投影',font=small,fill='white')
            for col,im in enumerate([original,overlay]):
                tile=Image.fromarray(cv2.cvtColor(im,cv2.COLOR_BGR2RGB));tile.thumbnail((510,540),Image.Resampling.NEAREST if case['camera_kind']=='episode_roi' else Image.Resampling.LANCZOS);frame.paste(tile,(18+col*535+(510-tile.width)//2,80))
            draw.text((18,635),f"帧 {record.get('source_frame',record['index'])} · {state_label(record)}",font=font,fill='#ffb16d' if record['state']=='lost' else 'white')
            draw.text((18,671),f"跟踪点 {record['tracked_features']}（头部 {record['tracked_head_features']}）· 灰虚线/叉为模型预测，非直接观测",font=small,fill='#d7e1ea');writer.write(cv2.cvtColor(np.array(frame),cv2.COLOR_RGB2BGR))
        writer.release()
    full_records=json.loads((results/'full_fisheye_video/tracking.json').read_text());movie(case,full_records,results/'full_fisheye_tracking.mp4','原分辨率鱼眼局部 · 刚性特征跟踪与条件位姿更新')
    controlled=json.loads((results/'moving_occlusion/tracking.json').read_text());movie(case,controlled,results/'controlled_occlusion_tracking.mp4','受控遮挡试验（在真实视频上添加遮挡，并非新采集）')
    canvas=Image.new('RGB',(1420,690),'#15212e');draw=ImageDraw.Draw(canvas);draw.text((18,12),'遮挡机制检查：前端遮挡 → 全遮挡 → 重新出现',font=font,fill='white')
    for col,i in enumerate([0,20,36,38]):
        record=controlled[i];_,im=annotated(case,record);tile=Image.fromarray(cv2.cvtColor(im,cv2.COLOR_BGR2RGB));tile.thumbnail((335,500));canvas.paste(tile,(18+col*350+(335-tile.width)//2,90));draw.text((18+col*350,55),f"帧 {record['source_frame']} · {record['phase']}",font=small,fill='white');draw.text((18+col*350,585),f"跟踪点 {record['tracked_features']}，头部 {record['tracked_head_features']}",font=small,fill='white');label='无位姿输出' if record['state']=='lost' else ('有视觉更新' if record['measurement_update'] else '仅预测');draw.text((18+col*350,615),label,font=small,fill='#ffc56d')
    draw.text((18,655),'这是受控遮挡/恢复测试；不代表真实插入过程的位姿精度已通过验证。',font=small,fill='white');canvas.save(results/'occlusion_mechanism_review.png')
    canvas=Image.new('RGB',(1420,1450),'#15212e');draw=ImageDraw.Draw(canvas);draw.text((18,12),'真实 episode：128×128 数据的约束不足与丢失状态均保留',font=font,fill='white')
    for row,ident in enumerate(['8083942d','19c7887c','015d0561']):
        case=cases[ident];records=json.loads((results/ident/'tracking.json').read_text())
        for col,index in enumerate([0,len(records)//3,2*len(records)//3,len(records)-1]):
            record=records[index];_,im=annotated(case,record);tile=Image.fromarray(cv2.cvtColor(im,cv2.COLOR_BGR2RGB)).resize((320,320),Image.Resampling.NEAREST);x=18+col*350;y=70+row*440;draw.text((x,y),f"{ident} · tick {record['source_frame']}",font=small,fill='white');canvas.paste(tile,(x,y+35));label='2D 更新，深度/角度为先验' if record.get('measurement_dof_count')==2 else ('位姿观测丢失' if record['state']=='lost' else record['state']);draw.text((x,y+365),label,font=small,fill='#ffc56d');draw.text((x,y+394),f"特征数 {record['tracked_features']}",font=small,fill='white')
    draw.text((18,1410),'没有把保留的初始深度和角度包装成新的六维观测；这组 ROI 尚不足以证明精确插入定位。',font=small,fill='white');canvas.save(results/'real_episode_review.png')
    print(results/'feature_atlas_review.png')


if __name__=='__main__':main()
