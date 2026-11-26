"""Candidate GT: finish alignment outside the socket, then approach axially.

This changes the geometric reference itself, not just its plotted shape. It is
not wired into the frozen learned model or runtime ReferenceProvider.
"""
import argparse
import json
from pathlib import Path
import subprocess

import numpy as np
from PIL import Image, ImageDraw

from render_system1_orientation import decoded_approach, gripper_center_frame, triad
from render_system1_far import ribbon, dense, GT, BG, INK, MUTED
from render_system1_assets import label
from render_system1_paths import transform, project
from omi_shapeforge.sim.isaac_contact_kinematics import local_pose
from omi_shapeforge.sim.tianji_ik import TianjiIK, pose_error
from omi_hil_rl.training.hierarchical_insertion.reference import pose, exp_rotation, log_rotation

TIP_COLORS=((218,119,14),(255,177,51))


def axial_approach(start, end, tip_tcp, axis, final_straight_m=.020):
    """C1 tip path and smooth SO(3) rotation, followed by an axial straight.

The alignment stage is monotone in the insertion direction. Refuse starts
already beyond its staging plane; those need a separate retreat strategy.
"""
    axis=np.asarray(axis,float);axis/=np.linalg.norm(axis)
    p0=(start@tip_tcp)[:3];pend=(end@tip_tcp)[:3]
    stage=pend-axis*final_straight_m
    delta=stage-p0;advance=float(delta@axis)
    if advance<=.001:raise ValueError('start is too close for this alignment rule; retreat planning required')
    lateral=delta-axis*advance
    turn=log_rotation(start[:3,:3].T@end[:3,:3])
    result=[]
    for u in np.linspace(0,1,65):
        f=u*u*(3-2*u)
        position=p0+axis*(advance*u)+lateral*f
        R=start[:3,:3]@exp_rotation(f*turn)
        result.append(pose(position-R@tip_tcp[:3],R))
    for distance in np.linspace(0,final_straight_m,21)[1:]:
        position=stage+axis*distance;R=end[:3,:3]
        result.append(pose(position-R@tip_tcp[:3],R))
    np.testing.assert_allclose(result[0],start,atol=1e-12)
    np.testing.assert_allclose(result[-1],end,atol=1e-12)
    return result


def angle_to_axis(v,axis):
    return float(np.rad2deg(np.arccos(np.clip(v@axis/np.linalg.norm(v),-1,1))))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['source','output','tianji-sdk']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    s=json.loads((a.source/'scene_packet.json').read_text());transfer=Path(s['source_transfer']);probes=Path(s['source_probes'])
    packet=json.loads((transfer/'transfer.json').read_text());m=packet['manifest']
    data=np.load(probes/'samples.npz',allow_pickle=False)
    G,_=gripper_center_frame(packet,transfer);M=pose(m['tool_to_module']['position_m'],m['tool_to_module']['rotation'])
    tip_tcp=M@np.array([0,m['leading_tip_y_mm']/1000,0,1.])
    W=pose(m['socket_to_world']['position_m'],m['socket_to_world']['rotation'])
    end=np.linalg.inv(W)@pose(m['preinsert_tcp_position'],m['goal_tcp_rotation'])
    axis=np.array([0.,-1.,0.]);cx,cz=m['nominal_module_center_xz_mm'];mouth=m['mouth_y_mm']
    ik=TianjiIK(packet,a.tianji_sdk)
    names=json.loads((probes/'worker/kinematics_check.json').read_text())['joint_names']
    camera=next(c for c in packet['cameras'] if c['name']=='wrist_rgb')
    C=np.diag([1.,-1.,-1.,1.])@np.linalg.inv(local_pose(camera));K=np.array(m['observation_projection']['K']);D=np.array(m['observation_projection']['D'])
    rows=[]
    for case in s['cases']:
        i=case['id'];start=np.array(case['socket_from_tcp'])
        poses=axial_approach(start,end,tip_tcp,axis)
        old=[start@v for v in decoded_approach(m,data['target_socket'][i])]
        center=np.array([(v@G)[:3,3]*1000 for v in poses]);tips=np.array([(v@tip_tcp)[:3]*1000 for v in poses])
        old_tip=np.array([(v@tip_tcp)[:3]*1000 for v in old])
        metrics=dict(old_last_tip_segment_angle_deg=angle_to_axis(old_tip[-1]-old_tip[-2],axis),
                     new_last_tip_segment_angle_deg=angle_to_axis(tips[-1]-tips[-2],axis),
                     axial_segment_max_angle_deg=max(angle_to_axis(v,axis) for v in np.diff(tips[64:],axis=0)),
                     axial_segment_lateral_max_mm=float(np.max(np.linalg.norm(tips[64:][:,[0,2]]-[cx,cz],axis=1))),
                     staging_tip_gap_mm=float(tips[64,1]-mouth),end_tip_gap_mm=float(tips[-1,1]-mouth),
                     alignment_complete_before_straight_deg=float(np.rad2deg(np.linalg.norm(log_rotation(poses[64][:3,:3].T@end[:3,:3])))))
        assert metrics['axial_segment_max_angle_deg']<1e-5
        assert metrics['axial_segment_lateral_max_mm']<1e-8
        assert metrics['alignment_complete_before_straight_deg']<1e-8
        held=json.loads((probes/f'case_{i:02d}.json').read_text())['held_info']
        q={j['name']:packet['initial_qpos'][j['qpos_index']] for j in packet['joints']};q.update(zip(names,held['joint_positions']))
        checks=[]
        for j,v in enumerate(poses):
            try:
                q=ik.solve(q,W@v);p_err,r_err=pose_error(ik.kin.tcp(q),W@v)
                checks.append(dict(index=j,valid=True,position_error_mm=p_err*1000,angle_error_deg=float(np.rad2deg(r_err))))
            except Exception as exc:
                checks.append(dict(index=j,valid=False,error=repr(exc)));break
        row=dict(id=i,tcp_poses_socket_m=[v.tolist() for v in poses],center_mm=center.tolist(),tip_mm=tips.tolist(),
                 old_tip_mm=old_tip.tolist(),metrics=metrics,ik=checks,all_ik_passed=len(checks)==len(poses) and all(x['valid'] for x in checks))
        rows.append(row)
        view=json.loads((a.source/f'case_{i:02d}_wide.json').read_text());Tcam=np.linalg.inv(view['camera_world'])
        def asset_screen(points):
            v=transform(Tcam,points);return v[:,:2]*[1450/view['ortho_scale'],-1450/view['ortho_scale']]+[725,425]
        def wrist_screen(points):
            uv,valid=project(transform(np.linalg.inv(start),np.array(points)/1000),C,K,D);uv[~valid]=np.nan
            return (uv+.5)*6.25-.5
        img=Image.new('RGB',(2400,1390),BG)
        label(img,(48,25),'GT修正候选  /  孔外完成对准，再沿孔轴直线接近',39,INK)
        label(img,(50,90),f"案例 {i+1}   原末段偏轴 {metrics['old_last_tip_segment_angle_deg']:.1f}° → 修正后 {metrics['new_last_tip_segment_angle_deg']:.1f}°   |   最后20 mm保持朝向、沿轴移动",25,MUTED)
        label(img,(50,150),'3D  /  紫：夹爪中心    橙：模块尖端',27,INK);label(img,(1550,150),'2D  /  同路径鱼眼投影',27,INK)
        asset=Image.open(a.source/f'case_{i:02d}_wide.png').convert('RGB')
        wrist=Image.fromarray(data['images'][i,3:].transpose(1,2,0)).resize((800,800),Image.Resampling.LANCZOS)
        center=dense(center);tips=dense(tips)
        axis_points=np.array([[cx,mouth+35,cz],[cx,mouth-10,cz]])
        for im,screen in [(asset,asset_screen),(wrist,wrist_screen)]:
            ribbon(im,screen(dense(axis_points,80)),((113,133,151),(113,133,151)),3,True)
            ribbon(im,screen(center),GT,7);ribbon(im,screen(tips),TIP_COLORS,6)
            u,v=screen([[cx,mouth,cz]])[0];draw=ImageDraw.Draw(im)
            draw.ellipse((u-7,v-7,u+7,v+7),fill='white',outline=(22,143,85),width=3)
            draw.line((u-4,v,u+4,v),fill=(22,143,85),width=2);draw.line((u,v-4,u,v+4),fill=(22,143,85),width=2)
            label(im,(u+12,v+8),'孔口中心',18,(22,143,85))
            for j in [0,16,32,48,64,84]:
                T=poses[j]@G;origin=T[:3,3]*1000
                axes=np.vstack([origin,origin+6*T[:3,:3].T])
                triad(im,screen(axes),('转正完成' if j==64 else '终点' if j==84 else ''),INK,j==84)
        img.paste(asset,(50,205));img.paste(wrist,(1550,205))
        label(img,(1550,1020),'灰虚线为孔轴；橙线是模块尖端参考。',21,MUTED)
        label(img,(50,1100),'先在尖端距孔口25 mm处完成对准，再沿孔轴走到入口前5 mm。',27,INK)
        label(img,(50,1155),'末段位置变化与孔轴一致，且模块朝向保持；夹爪中心线与尖端线平行，但不重合。',25,INK)
        label(img,(50,1220),'这是独立的新规则候选，尚未替换训练接口；图中线路是参考，未做物理执行。',23,MUTED)
        label(img,(50,1270),'初态实体保持原记录。原始路径和模型保留；完整碰撞与动力学效果须另行核验。',23,MUTED)
        img.save(a.output/f'case_{i:02d}_corrected.png')
    report=dict(source=str(a.source),source_transfer=str(transfer),cases=rows,rule='tip-space axial advance + smooth lateral/rotation alignment; final 20mm axial',
                staging_gap_mm=25,end_gap_mm=5,runtime_integrated=False,physical_execution=False)
    (a.output/'axial_reference.json').write_text(json.dumps(report,indent=2)+'\n')
    # Reuse the explanatory asset renderer for a start/staging/endpoint triptych.
    row=rows[1];snapshots=[]
    for j in [0,64,84]:
        v=np.array(row['tcp_poses_socket_m'][j]);T=v@G;center=T[:3,3]*1000;tip=(v@tip_tcp)[:3]*1000
        snapshots.append(dict(index=j,tcp_socket_m=v.tolist(),axes_mm=np.vstack([center,center+6*T[:3,:3].T]).tolist(),
            center_mm=center.tolist(),tip_mm=tip.tolist(),tip_gap_mm=float(tip[1]-mouth),center_gap_mm=float(center[1]-mouth)))
    explanation=dict(source=str(a.source),case=1,snapshots=snapshots,path_mm=row['center_mm'],tip_path_mm=row['tip_mm'],tool_names=[g['name'] for g in s['parts'] if g['category']=='tool'])
    (a.output/'explanation.json').write_text(json.dumps(explanation,indent=2)+'\n')
    subprocess.run(['blender','-b','-t','4','--python',str(Path(__file__).with_name('explain_system1_gt_blender.py')),'--',str(a.output)],check=True)
    board=Image.new('RGB',(3060,1010),BG)
    label(board,(30,20),'修正规则的实体姿态  /  先对准，再沿轴接近',39,INK)
    label(board,(30,80),'三个参考位姿的静态重建；不代表物理执行。',25,MUTED)
    for k,(snap,title) in enumerate(zip(snapshots,['起点：原始未对准状态','孔口前25 mm：对准完成','孔口前5 mm：沿轴接近终点'])):
        x=30+k*1010;label(board,(x,140),title,27,INK)
        raw=Image.open(a.output/f"pose_{snap['index']:02d}.png").convert('RGB')
        uv=json.loads((a.output/f"pose_{snap['index']:02d}.json").read_text());ribbon(raw,uv['path'],GT,6)
        triad(raw,uv['axes'],'',INK,True);u,v=uv['tip'];ImageDraw.Draw(raw).ellipse((u-6,v-6,u+6,v+6),fill=TIP_COLORS[1],outline='white',width=2)
        board.paste(raw,(x,185));label(board,(x,860),f"尖端距孔口 {snap['tip_gap_mm']:.1f} mm",28,INK)
    label(board,(30,940),'最后两张朝向相同，仅沿孔轴平移20 mm。紫线跟踪夹爪中心，橙点标出模块尖端。',27,MUTED)
    board.save(a.output/'corrected_poses.png')
    print('COMPLETE',a.output,flush=True)


if __name__=='__main__':main()
