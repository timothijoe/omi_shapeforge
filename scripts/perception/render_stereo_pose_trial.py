"""Render actual V3 geometry in calibrated color and withheld right-IR views."""
import argparse
import csv
import json
from pathlib import Path
import cv2
import numpy as np
from PIL import Image,ImageDraw,ImageFont
import torch
import nvdiffrast.torch as dr
from render_socket_cloud import buffers,encode


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=Path,required=True);a=p.parse_args();root=a.run
    inv=json.loads((root/'inventory.json').read_text());session=Path(inv['source_session']);cal=json.loads((root/'calibration.json').read_text())
    rows=json.loads((root/'refinement_summary.json').read_text());Kc=np.array(cal['K_color']);Ki=np.array(cal['K_ir']);Tci=np.array(cal['T_color_from_ir']);baseline=cal['baseline_m']
    data=np.load(root/'model.npz');V,F=data['vertices'],data['triangles'];verts=torch.tensor(V,dtype=torch.float32,device='cuda');faces=torch.tensor(F,dtype=torch.int32,device='cuda');ctx=dr.RasterizeCudaContext()
    tri=V[F];norm=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);norm/=np.maximum(np.linalg.norm(norm,axis=1,keepdims=True),1e-12);adj={}
    for index,face in enumerate(F):
        for x,y in zip(face,np.roll(face,-1)):adj.setdefault(tuple(sorted((int(x),int(y)))),[]).append(index)
    edges=np.array([e for e,ff in adj.items() if len(ff)!=2 or norm[ff[0]]@norm[ff[1]]<np.cos(.35)])
    edges_points=V[edges];edge_samples=edges_points[:,0,None,:]+np.linspace(0,1,17)[None,:,None]*(edges_points[:,1,None,:]-edges_points[:,0,None,:])
    def render(image,K,T,color):
        h,w=image.shape[:2];v=verts@torch.tensor(T[:3,:3],device='cuda',dtype=torch.float32).T+torch.tensor(T[:3,3],device='cuda',dtype=torch.float32)
        x,y,z=v.unbind(1);clip=torch.stack([2*K[0,0]/w*x+(2*K[0,2]/w-1)*z,-2*K[1,1]/h*y+(1-2*K[1,2]/h)*z,1.00002*z-.00200002,z],dim=1)[None]
        rast,_=dr.rasterize(ctx,clip,faces,resolution=[h,w]);mask=(rast[0,...,3]>0).flip(0).cpu().numpy()
        depth=dr.interpolate(v[None,:,2:3].contiguous(),rast,faces)[0][0,...,0].flip(0).cpu().numpy()
        out=image.copy();out[mask]=(.80*out[mask]+.20*np.array(color)).astype(np.uint8)
        pts=edge_samples@T[:3,:3].T+T[:3,3];uv=pts@K.T;uv=uv[:,:,:2]/uv[:,:,2:];pix=np.rint(uv).astype(int)
        valid=(pix[:,:,0]>=0)&(pix[:,:,0]<w)&(pix[:,:,1]>=0)&(pix[:,:,1]<h)&(pts[:,:,2]>0)
        visible=np.zeros_like(valid);yid,xid=np.where(valid);zs=depth[pix[yid,xid,1],pix[yid,xid,0]];visible[yid,xid]=(zs>0)&(pts[yid,xid,2]<zs+.00035)
        for i in range(len(edges)):
            for j in range(16):
                if visible[i,j] and visible[i,j+1]:cv2.line(out,tuple(pix[i,j]),tuple(pix[i,j+1]),color,1,cv2.LINE_AA)
        return out
    font_path='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc';font=ImageFont.truetype(font_path,23);small=ImageFont.truetype(font_path,17)
    (root/'figures').mkdir(exist_ok=True);cards={};csvrows=[]
    for row in rows:
        name=row['id'];out=root/'fits'/name;crop=json.loads((out/'crop.json').read_text());K=np.array(crop['K']);rgb=cv2.imread(str(out/'color_crop.png'));T0=np.array(row['coarse']['T_color_from_model']);T=np.array(row['joint']['T_color_from_model'])
        coarse=render(rgb,K,T0,(255,210,30));fine=render(rgb,K,T,(0,185,255));pixel=render(rgb,K,np.array(row['pixel_only']['T_color_from_model']),(210,90,240))
        m=cv2.imread(str(out/'mask_crop.png'),0);ym,xm=np.where(m>0);all_uv=[np.c_[xm,ym]]
        for pose in [T0,T]:
            cam=V@pose[:3,:3].T+pose[:3,3];uvv=cam@K.T;all_uv.append(uvv[:,:2]/uvv[:,2,None])
        extent=np.concatenate(all_uv);lo_view=np.maximum(0,np.floor(extent.min(0)-14).astype(int));hi_view=np.minimum(512,np.ceil(extent.max(0)+15).astype(int));bounds=[*lo_view,*hi_view]
        cv2.imwrite(str(out/'coarse_color_overlay.png'),coarse);cv2.imwrite(str(out/'joint_color_overlay.png'),fine);cv2.imwrite(str(out/'pixel_only_overlay.png'),pixel)
        # Same final pose is projected into the other physical camera. Its image
        # is never used by the RGB silhouette optimizer (depth still uses both IRs).
        right=cv2.imread(str(session/'frames'/name/'right.png'));obs=np.load(out/'observations.npz');q=obs['xyz_ir'].copy();q[:,0]-=baseline;uv=q@Ki.T;uv=uv[:,:2]/uv[:,2,None]
        lo=np.floor(uv.min(0)-22).astype(int);hi=np.ceil(uv.max(0)+22).astype(int);lo=np.maximum(lo,0);hi=np.minimum(hi,np.array(right.shape[1::-1]));right_crop=right[lo[1]:hi[1],lo[0]:hi[0]];Kr=Ki.copy();Kr[:2,2]-=lo
        Tri=np.eye(4);Tri[0,3]=-baseline;Tr0=Tri@np.linalg.inv(Tci)@T0;Tr=Tri@np.linalg.inv(Tci)@T
        before=render(right_crop,Kr,Tr0,(255,210,30));after=render(right_crop,Kr,Tr,(0,185,255));cv2.imwrite(str(out/'right_ir_coarse.png'),before);cv2.imwrite(str(out/'right_ir_refined.png'),after)
        candidates=sorted(row['joint_candidates'],key=lambda x:x['objective']);gap=candidates[1]['objective']-candidates[0]['objective'] if len(candidates)>1 else None
        canvas=Image.new('RGB',(1540,700),'#14202d');draw=ImageDraw.Draw(canvas)
        titles=['原始彩色图局部','双目点云初值','点云＋像素约束','右目：初值','右目：精修']
        images=[rgb,coarse,fine,before,after]
        for j,(im,title) in enumerate(zip(images,titles)):
            draw.text((15+j*305,60),title,font=small,fill='white')
            if j<3:
                im=im[bounds[1]:bounds[3],bounds[0]:bounds[2]]
            tile=Image.fromarray(cv2.cvtColor(im,cv2.COLOR_BGR2RGB));tile.thumbnail((290,480),Image.Resampling.LANCZOS);canvas.paste(tile,(15+j*305+(290-tile.width)//2,105))
        draw.text((15,15),f'{name} · 固定 V3 主体 / 不含绿色挂件',font=font,fill='white')
        draw.text((15,600),f"彩色轮廓 IoU {row['coarse']['rgb_mask_iou']:.3f} → {row['joint']['rgb_mask_iou']:.3f}；检查点云 P90 {row['coarse']['check_p90_mm']:.3f} → {row['joint']['check_p90_mm']:.3f} mm",font=font,fill='#f7c46b')
        note='右目仅作重投影查看；没有真实位姿 GT。'
        if gap is not None and gap<.03:note+=' 存在评分接近的朝向／位置候选，需复核。'
        draw.text((15,648),note,font=small,fill='white');canvas.save(root/'figures'/f'{name}.png');cards[name]=(rgb,coarse,fine,row,bounds)
        csvrows.append([name,row['coarse']['rgb_mask_iou'],row['joint']['rgb_mask_iou'],row['coarse']['check_p90_mm'],row['joint']['check_p90_mm'],row['pixel_only']['rgb_mask_iou'],row['pixel_only']['check_p90_mm'],row['rotation_change_deg'],row['translation_change_mm'],gap,row['status']])
    with (root/'metrics.csv').open('w') as f:
        writer=csv.writer(f);writer.writerow(['frame','coarse_rgb_iou','joint_rgb_iou','coarse_check_p90_mm','joint_check_p90_mm','pixel_only_iou','pixel_only_check_p90_mm','rotation_change_deg','translation_change_mm','joint_objective_margin','diagnostic_status']);writer.writerows(csvrows)
    chosen=['optical_0015','optical_0270','optical_0540','optical_0885'];canvas=Image.new('RGB',(1120,2040),'#14202d');draw=ImageDraw.Draw(canvas)
    draw.text((18,12),'真实双目测试：原图 → 点云初值 → 点云＋像素联合精修',font=font,fill='white')
    for idx,name in enumerate(chosen):
        raw,coarse,fine,row,bounds=cards[name];x0,y0,x1,y1=bounds
        for j,(im,label) in enumerate(zip([raw,coarse,fine],['原图','点云初值','联合精修'])):
            y=65+idx*475;draw.text((20+j*365,y),label+' · '+name,font=small,fill='white');tile=Image.fromarray(cv2.cvtColor(im[y0:y1,x0:x1],cv2.COLOR_BGR2RGB));tile.thumbnail((330,385),Image.Resampling.LANCZOS);canvas.paste(tile,(20+j*365+(330-tile.width)//2,y+35))
        draw.text((20,65+idx*475+425),f"IoU {row['coarse']['rgb_mask_iou']:.2f} → {row['joint']['rgb_mask_iou']:.2f}；检查点云 P90 {row['coarse']['check_p90_mm']:.2f} → {row['joint']['check_p90_mm']:.2f} mm",font=small,fill='#f7c46b')
    draw.text((20,1990),'指标表示图像／点云相容性，不是物理位姿精度。朝向歧义与失败候选均保留。',font=small,fill='white');canvas.save(root/'overview.png')
    # A self-contained point-cloud view of the side-view branch correction.
    row=next(x for x in rows if x['id']=='optical_0540');obs=np.load(root/'fits/optical_0540/observations.npz');q=obs['xyz_ir'];T0=np.linalg.inv(Tci)@np.array(row['coarse']['T_color_from_model']);T=np.array(row['T_ir_from_model'])
    gray=np.full(len(q),.72);buffer=buffers([(V,F)])
    payload={'cloud':encode(np.c_[q,gray]),'roi':encode(np.zeros(len(q))),
        'groups':[{'object':'socket','toggle':'socket','color':[.15,.8,1.],**buffer},{'object':'module','toggle':'module','color':[1.,.65,.2],**buffer}],
        'candidates':[{'T':T0.tolist(),'score':row['coarse']['check_p90_mm']}], 'module_T':T.tolist(),'focus':np.median(q,axis=0).tolist(),'scene_center':np.median(q,axis=0).tolist()}
    html=Path(__file__).with_name('socket_cloud_viewer.html').read_text().replace('__PAYLOAD__',json.dumps(payload,separators=(',',':'))).replace('__METRICS__','点云初值与联合精修可分别隐藏，坐标与尺寸均保持不变。')
    html=html.replace('插座 OS-001 r04 ＋光模块 V3','侧视样本 optical_0540 · 双目点云与 V3').replace('插座与光模块 · 点云配准','双目点云 · 精修前后')
    html=html.replace('蓝色：插座','蓝色：点云初值').replace('橙色：光模块主体','橙色：联合精修')
    html=html.replace('插座为粗配准候选，光模块保持已确认的翻面结果；两者独立定位，没有强制插合。','同一物体的两种位姿。此帧点云单独拟合存在薄面／宽面混淆；图像约束选择了另一朝向候选。')
    html=html.replace('>插座</label>','>点云初值</label>').replace('>光模块</label>','>联合精修</label>')
    html=html.replace('<label><input id="handle" type="checkbox">绿色挂件（仅显示）</label>','<input id="handle" type="checkbox" hidden>')
    html=html.replace('<label><input id="stand" type="checkbox">下部支架（未验证）</label>','<input id="stand" type="checkbox" hidden>')
    html=html.replace('>插座拟合点</label>','>选区高亮</label>').replace('插座候选','初值候选').replace('插口对应关系仍需复核；绿色挂件没有用于求解。','真实位姿未认证；绿色挂件没有用于求解。')
    html=html.replace('<label><input id="highlight" type="checkbox">选区高亮</label>','<input id="highlight" type="checkbox" hidden>')
    html=html.replace('几何评分','初值检查 P90 / mm').replace('原始点云','主体点云').replace('src="preview.png"','src="overview.png"')
    html=html.replace('yaw=-.3,pitch=-.5,distance=.24','yaw=.25,pitch=-.15,distance=.09').replace('distance=.19','distance=.09').replace('distance=.24','distance=.09')
    (root/'pointcloud_before_after.html').write_text(html)
    print(root/'overview.png')


if __name__=='__main__':main()
