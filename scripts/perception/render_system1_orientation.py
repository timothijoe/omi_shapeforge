"""Add sampled module orientation frames to frozen 3D/2D approach views.

Axes follow decoded SO(3) poses, not the position-curve tangent. Historical
images and scenes remain read-only. Default frame: gripper contact-pad midpoint,
X forward, Y left, Z tool-up. Legacy module-based frames are reproducible.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np
from PIL import Image, ImageDraw

from render_system1_far import ribbon, dense, PRED, GT, BG, INK, MUTED
from render_system1_assets import label
from render_system1_paths import transform, project
from omi_shapeforge.sim.isaac_contact_kinematics import Kinematics, local_pose
from omi_hil_rl.training.hierarchical_insertion.reference import ReferenceProvider, pose, exp_rotation, log_rotation

AXES=((224,62,65),(37,170,84),(45,110,227))


def gripper_center_frame(packet, transfer):
    """Fixed nominal jaw midpoint in TCP coordinates; no module pose input."""
    names=['wrist_tool_022','wrist_tool_033']
    arrays=np.load(transfer/'meshes.npz',allow_pickle=False)
    geoms={g['name']:g for g in packet['geoms']}
    q={j['name']:packet['initial_qpos'][j['qpos_index']] for j in packet['joints']}
    frames=Kinematics(packet).frames(q)
    tcp_body=next(s['body'] for s in packet['sites'] if s['name']=='urdf_tcp_L')
    tcp_inv=np.linalg.inv(frames[tcp_body]);centers=[];bounds=[]
    for name in names:
        g=geoms[name]
        v=transform(tcp_inv@frames[g['body']]@local_pose(g),arrays[f"v{g['mesh']}"])
        lo,hi=v.min(0),v.max(0);centers.append((lo+hi)/2);bounds.append([lo.tolist(),hi.tolist()])
    # Native TCP: +Z toward fingertips, +X toward the upper/camera surface.
    Q=np.array([[0.,0.,1.],[0.,-1.,0.],[1.,0.,0.]])
    return pose(np.mean(centers,axis=0),Q),dict(parts=names,bounds_tcp_m=bounds,
        pad_centers_tcp_m=[v.tolist() for v in centers],
        origin_definition='midpoint of the two contact-pad bounding-box centers at nominal fixed jaw opening',
        module_pose_dependency=False,physical_tcp_calibration=False)


def body_center_frame(packet, transfer):
    """Center of the load-bearing casing envelope, excluding handle/plug/head cap."""
    names=['sim_module_000_visual','sim_module_001_visual','sim_module_002_visual','sim_module_013_visual']
    arrays=np.load(transfer/'meshes.npz',allow_pickle=False)
    parts={g['name']:g for g in packet['geoms']}
    vertices=np.concatenate([transform(local_pose(parts[n]),arrays[f"v{parts[n]['mesh']}"]) for n in names])
    lo,hi=vertices.min(0),vertices.max(0)
    # Columns express the new basis in the native module basis.
    Q=np.array([[0.,1.,0.],[-1.,0.,0.],[0.,0.,1.]])
    return pose((lo+hi)/2,Q),dict(parts=names,bounds_native_m=[lo.tolist(),hi.tolist()],
                                origin_definition='midpoint of lower shell, left/right walls and upper shell bounds; not mass center')


def decoded_approach(manifest, socket):
    """The exact first 33 poses of render_system1_paths.references()."""
    provider=ReferenceProvider(manifest)
    entry=socket@provider.local_entry;goal=socket@provider.local_goal
    axis=goal[:3,3]-entry[:3,3];length=np.linalg.norm(axis);axis/=length
    progress=-entry[:3,3]@axis
    if progress<0:
        start,end=np.eye(4),entry
    else:
        start=pose(entry[:3,3]+axis*np.clip(progress,0,length),goal[:3,:3]);end=goal
    turn=log_rotation(start[:3,:3].T@end[:3,:3])
    return [pose((1-f)*start[:3,3]+f*end[:3,3],start[:3,:3]@exp_rotation((f*f*(3-2*f))*turn))
            for f in np.linspace(0,1,33)]


def triad(im, pixels, tag, color, axis_letters=False):
    aa=3
    layer=Image.new('RGBA',(im.width*aa,im.height*aa),(0,0,0,0));d=ImageDraw.Draw(layer)
    p=np.asarray(pixels,float)*aa
    origin=p[0]
    if not np.isfinite(origin).all():return
    for k,end in enumerate(p[1:]):
        if not np.isfinite(end).all():continue
        v=end-origin;length=np.linalg.norm(v)
        if length<1:continue
        v/=length;n=np.array([-v[1],v[0]])
        d.line([tuple(origin),tuple(end)],fill='white',width=7*aa)
        d.line([tuple(origin),tuple(end)],fill=AXES[k],width=3*aa)
        head=min(9*aa,length*.35)
        d.polygon([tuple(end),tuple(end-v*head+n*head*.45),tuple(end-v*head-n*head*.45)],fill=AXES[k])
    u,v=origin;r=4*aa
    d.ellipse((u-r,v-r,u+r,v+r),fill='white',outline=color,width=2*aa)
    layer=layer.resize(im.size,Image.Resampling.LANCZOS);im.paste(layer,(0,0),layer)
    u,v=origin/aa
    font_pos=(u+8,v+10)
    label(im,font_pos,tag,17,color)
    if axis_letters:
        for k,end in enumerate(p[1:]/aa):
            if np.isfinite(end).all():label(im,tuple(end+np.array([3,-19])),['X','Y','Z'][k],16,AXES[k])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--frame',choices=['gripper-center-forward','body-center-forward','tip-native'],default='gripper-center-forward')
    p.add_argument('--no-blend',action='store_true')
    p.add_argument('--only-gt',action='store_true',help='Render only ground-truth references; omit model curves')
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    s=json.loads((a.source/'scene_packet.json').read_text())
    transfer=Path(s['source_transfer']);packet=json.loads((transfer/'transfer.json').read_text());m=packet['manifest']
    samples=np.load(Path(s['source_probes'])/'samples.npz',allow_pickle=False)
    Tmodule=pose(m['tool_to_module']['position_m'],m['tool_to_module']['rotation'])
    local_tip=np.array([0,m['leading_tip_y_mm']/1000,0,1.]);tip=Tmodule@local_tip
    centered=a.frame=='body-center-forward'
    gripper=a.frame=='gripper-center-forward'
    if gripper:
        tcp_from_display,center_geometry=gripper_center_frame(packet,transfer)
        display_frame=None
    elif centered:
        display_frame,center_geometry=body_center_frame(packet,transfer)
    else:
        display_frame=pose(local_tip[:3],np.eye(3));center_geometry=None
    if not gripper:tcp_from_display=Tmodule@display_frame
    camera=next(c for c in packet['cameras'] if c['name']=='wrist_rgb')
    C=np.diag([1.,-1.,-1.,1.])@np.linalg.inv(local_pose(camera))
    K=np.array(m['observation_projection']['K']);D=np.array(m['observation_projection']['D'])
    entries=[];anchor_error=[];rotation_error=[]
    for case in s['cases']:
        i=case['id'];T=np.array(case['socket_from_tcp'])
        view=json.loads((a.source/f'case_{i:02d}_wide.json').read_text());Tcam=np.linalg.inv(view['camera_world'])
        frames={};display_paths={};display_asset_pixels={};display_wrist_pixels={}
        selected=[('gt','target_socket')] if a.only_gt else [('pred','predicted_socket'),('gt','target_socket')]
        for key,array in selected:
            poses=decoded_approach(m,samples[array][i])
            tip_points=transform(T,np.array([(v@tip)[:3] for v in poses]))*1000
            expected=np.array(case['complete_paths_mm']['full_'+key])[:33]
            anchor_error.append(float(np.max(np.linalg.norm(tip_points-expected,axis=1))))
            np.testing.assert_allclose(tip_points,expected,atol=1e-8,rtol=0)
            displayed=[T@v@tcp_from_display for v in poses]
            points=np.array([v[:3,3] for v in displayed])*1000
            curve=dense(points)
            display_paths[key]=curve.tolist()
            camera_curve=transform(Tcam,curve)
            display_asset_pixels[key]=(camera_curve[:,:2]*[1450/view['ortho_scale'],-1450/view['ortho_scale']]+[725,425]).tolist()
            uv,valid=project(transform(np.linalg.inv(T),curve/1000),C,K,D)
            uv[~valid]=np.nan
            display_wrist_pixels[key]=((uv+.5)*6.25-.5).tolist()
            travel=float(np.linalg.norm(np.diff(points,axis=0),axis=1).sum())
            # Five regularly sampled frames. A nearly stationary predicted path
            # gets one frame instead of five unreadable coincident triads.
            indices=[0,8,16,24,32] if travel>=12 else [32]
            axis_length=6.
            items=[]
            for index in indices:
                matrix=displayed[index]
                R=matrix[:3,:3];origin=points[index]
                rotation_error.append(float(np.max(np.abs(R.T@R-np.eye(3)))))
                assert np.linalg.det(R)>.999999
                xyz=np.vstack([origin,origin+axis_length*R.T])
                xyzcam=transform(Tcam,xyz)
                asset_uv=xyzcam[:,:2]*[1450/view['ortho_scale'],-1450/view['ortho_scale']]+[725,425]
                tcp_xyz=transform(np.linalg.inv(T),xyz/1000)
                wrist_uv,valid=project(tcp_xyz,C,K,D);wrist_uv[~valid]=np.nan
                wrist_uv=(wrist_uv+.5)*6.25-.5
                items.append(dict(index=index,fraction=index/32,origin_mm=origin.tolist(),rotation=R.tolist(),
                                  points_mm=xyz.tolist(),axis_length_mm=axis_length,
                                  asset_pixels=asset_uv.tolist(),wrist_pixels=wrist_uv.tolist()))
            frames[key]=items
        row=dict(id=i,frames=frames,source_view=str(a.source/f'case_{i:02d}_wide.json'),
                 socket_from_tcp=case['socket_from_tcp'],summary=case['summary'],
                 paths_mm=display_paths,asset_path_pixels=display_asset_pixels,wrist_path_pixels=display_wrist_pixels)
        entries.append(row)
        for key,_ in selected:
            active_color=PRED[0] if key=='pred' else GT[0]
            title='模型预测' if key=='pred' else 'GT参考'
            asset=Image.open(a.source/f'case_{i:02d}_wide.png').convert('RGB')
            wrist=Image.fromarray(samples['images'][i,3:].transpose(1,2,0)).resize((800,800),Image.Resampling.LANCZOS)
            ribbon(asset,display_asset_pixels['gt'],GT,9 if a.only_gt else 6,not a.only_gt)
            ribbon(wrist,display_wrist_pixels['gt'],GT,9 if a.only_gt else 6,not a.only_gt)
            if not a.only_gt:
                ribbon(asset,display_asset_pixels['pred'],PRED,8);ribbon(wrist,display_wrist_pixels['pred'],PRED,8)
            for f in frames[key]:
                tag=f"{f['fraction']*100:.0f}%"
                triad(asset,f['asset_pixels'],tag,active_color,f['index']==32)
                triad(wrist,f['wrist_pixels'],tag,active_color,f['index']==32)
            im=Image.new('RGB',(2400,1390),BG)
            label(im,(48,25),f'SYSTEM1  /  {title} · '+('夹爪中心位姿' if gripper else '模块中心位姿' if centered else '沿途姿态坐标系'),40,INK)
            q=case['summary']
            label(im,(50,90),f"初始模块尖端距孔口 {q['requested_distance_mm']:.0f} mm    横向 {q['requested_lateral_mm']:+.0f} mm    高度 {q['requested_vertical_mm']:+.0f} mm    初始角度偏差 {q['actual_angular_offset_deg']:.1f}°",25,MUTED)
            label(im,(50,150),'3D  /  '+('原点位于两指之间，固定于夹爪' if gripper else '原点位于模块主壳体正中央' if centered else '坐标原点沿模块尖端路径移动'),28,INK)
            label(im,(1550,150),'2D  /  同一组三轴的相机投影',28,INK)
            im.paste(asset,(50,205));im.paste(wrist,(1550,205))
            label(im,(1550,1020),'腕图128×128放大；箭头按鱼眼模型投影',20,MUTED)
            d=ImageDraw.Draw(im);d.rounded_rectangle((50,1090,2350,1280),radius=18,fill=(233,239,245))
            label(im,(80,1106),'局部坐标系',24,INK)
            for j,(color,text) in enumerate(zip(AXES,['X','Y','Z'])):
                x=285+j*160;d.line((x,1128,x+48,1128),fill=color,width=5)
                d.polygon([(x+48,1128),(x+35,1121),(x+35,1135)],fill=color)
                label(im,(x+60,1108),text,24,color)
            label(im,(850,1106),'X向前 · Y向左 · Z向上；三轴长度均为6 mm' if centered or gripper else '模块插入朝向：−Y；三轴长度均为6 mm',24,INK)
            legend='紫色曲线：GT规则接近路径；红绿蓝箭头：夹爪沿途的实际参考朝向。' if a.only_gt else f'当前三轴来自：{title}的位姿旋转矩阵。蓝青路径＝预测；紫色虚线＝GT。'
            label(im,(80,1160),legend,23,INK)
            note='按33个原始采样点每隔8点显示：0%、25%、50%、75%、100%。' if len(frames[key])>1 else '该预测路径不足12 mm，仅显示末端三轴，避免坐标系重叠。'
            label(im,(80,1210),note,23,MUTED)
            footer=('曲线与三轴跟踪夹爪中心，原点透视显示。此图沿用固定夹持原型，尚未验证滑移补偿。' if gripper else
                    '曲线跟踪壳体中心，原点在壳内透视显示；Z随模块转动。原始TCP位姿不变，预测未执行。' if centered else
                    '箭头表达模块朝向，不是曲线切线。原始预测与路径不变，预测路径尚未执行。')
            if a.only_gt:footer='已通过仿真动作移动并旋转到这个起点；紫色路径只作几何参考展示，尚未执行或验证避障。'
            label(im,(50,1315),footer,23,MUTED)
            im.save(a.output/f'case_{i:02d}_{key}_orientation.png')
            asset.save(a.output/f'case_{i:02d}_{key}_asset.png')
            wrist.save(a.output/f'case_{i:02d}_{key}_wrist.png')
    protected=[a.source/'scene_packet.json',transfer/'transfer.json',transfer/'meshes.npz',Path(s['source_probes'])/'samples.npz']
    report=dict(source=str(a.source),output=str(a.output),source_transfer=str(transfer),cases=entries,
                only_gt=a.only_gt,
                axes='gripper-center frame; X forward, Y left, Z tool up; RGB' if gripper else 'body-center frame; X forward, Y left, Z module up; RGB' if centered else 'module +X/+Y/+Z at leading-tip center; red/green/blue; insertion direction -Y',
                frame_name=a.frame,module_from_display=None if gripper else display_frame.tolist(),
                tcp_from_display=tcp_from_display.tolist(),center_geometry=center_geometry,
                sampling='indices 0,8,16,24,32 of the existing 33-pose approach; only endpoint if length <12 mm',
                max_position_anchor_error_mm=max(anchor_error),max_rotation_orthogonality_error=max(rotation_error),
                source_hashes={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in protected})
    (a.output/'orientation.json').write_text(json.dumps(report,indent=2)+'\n')
    if not a.no_blend:
        subprocess.run(['blender','-b','-t','4','--python',str(Path(__file__).with_name('render_system1_orientation_blender.py')),'--',str(a.output)],check=True)
    print('COMPLETE',a.output,flush=True)


if __name__=='__main__':main()
