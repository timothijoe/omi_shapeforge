"""Show actual asset placements along a rule reference, not an executed rollout."""
import argparse
import json
from pathlib import Path
import subprocess

import numpy as np
from PIL import Image, ImageDraw

from render_system1_orientation import decoded_approach, gripper_center_frame, triad
from render_system1_far import ribbon, GT, BG, INK, MUTED
from render_system1_assets import label
from omi_hil_rl.training.hierarchical_insertion.reference import pose


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--case',type=int,default=1);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    s=json.loads((a.source/'scene_packet.json').read_text());case=s['cases'][a.case]
    transfer=Path(s['source_transfer']);packet=json.loads((transfer/'transfer.json').read_text());m=packet['manifest']
    data=np.load(Path(s['source_probes'])/'samples.npz',allow_pickle=False)
    reference=decoded_approach(m,data['target_socket'][a.case])
    T=np.array(case['socket_from_tcp']);G,_=gripper_center_frame(packet,transfer)
    M=pose(m['tool_to_module']['position_m'],m['tool_to_module']['rotation'])
    tip_local=M@np.array([0,m['leading_tip_y_mm']/1000,0,1.])
    snapshots=[]
    for j in [0,16,32]:
        tcp=T@reference[j];frame=tcp@G;tip=(tcp@tip_local)[:3]*1000
        center=frame[:3,3]*1000
        snapshots.append(dict(index=j,tcp_socket_m=tcp.tolist(),axes_mm=np.vstack([center,center+6*frame[:3,:3].T]).tolist(),
                              center_mm=center.tolist(),tip_mm=tip.tolist(),tip_gap_mm=float(tip[1]-m['mouth_y_mm']),
                              center_gap_mm=float(center[1]-m['mouth_y_mm'])))
    poses=dict(source=str(a.source),case=a.case,snapshots=snapshots,path_mm=[((T@v@G)[:3,3]*1000).tolist() for v in reference],
               tool_names=[g['name'] for g in s['parts'] if g['category']=='tool'],
               scope='static reference-pose reconstruction only; not physical execution')
    (a.output/'explanation.json').write_text(json.dumps(poses,indent=2)+'\n')
    subprocess.run(['blender','-b','-t','4','--python',str(Path(__file__).with_name('explain_system1_gt_blender.py')),'--',str(a.output)],check=True)
    board=Image.new('RGB',(3060,1030),BG)
    label(board,(30,18),'这条GT参考表示什么？  /  夹爪中心移动，模块随夹爪转正',39,INK)
    label(board,(30,80),'将同一套资产摆到三个参考位姿，解释路径含义；这些画面不是机器人执行记录。',25,MUTED)
    for k,(snap,title) in enumerate(zip(snapshots,['0%  起点：实际记录的偏移与倾斜','50%  中途：规则参考位姿','100%  终点：预插入位姿'])):
        x=30+k*1010;label(board,(x,138),title,26,INK)
        raw=Image.open(a.output/f'pose_{snap["index"]:02d}.png').convert('RGB')
        uv=json.loads((a.output/f'pose_{snap["index"]:02d}.json').read_text())
        ribbon(raw,uv['path'],GT,6)
        triad(raw,uv['axes'],'夹爪中心',INK,True)
        u,v=uv['tip'];d=ImageDraw.Draw(raw)
        d.ellipse((u-6,v-6,u+6,v+6),fill=(255,153,34),outline='white',width=2)
        label(raw,(u+10,v-24),'模块尖端',19,(194,104,14))
        board.paste(raw,(x,185))
        label(board,(x,852),f"模块尖端距孔口：{snap['tip_gap_mm']:.1f} mm",27,INK)
        label(board,(x,898),f"夹爪中心距孔口：{snap['center_gap_mm']:.1f} mm（轴向）",23,MUTED)
    label(board,(30,970),'紫线只画夹爪中心；终点并非孔口。已检查离散IK，尚未验证整段碰撞安全、动力学或插接成功。',25,MUTED)
    board.save(a.output/'gt_explained.png')
    print('COMPLETE',a.output,flush=True)


if __name__=='__main__':main()
