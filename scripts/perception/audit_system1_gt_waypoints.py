"""Offline IK/FK checks of rule GT approach poses; no motion or collision claim."""
import argparse
import json
from pathlib import Path
import numpy as np

from render_system1_orientation import decoded_approach
from omi_shapeforge.sim.tianji_ik import TianjiIK, pose_error
from omi_hil_rl.training.hierarchical_insertion.reference import pose


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['probes','transfer','tianji-sdk']:parser.add_argument('--'+name,type=Path,required=True)
    a=parser.parse_args()
    packet=json.loads((a.transfer/'transfer.json').read_text());m=packet['manifest']
    samples=np.load(a.probes/'samples.npz',allow_pickle=False)
    names=json.loads((a.probes/'worker/kinematics_check.json').read_text())['joint_names']
    ik=TianjiIK(packet,a.tianji_sdk)
    report=json.loads((a.probes/'report.json').read_text());cases=[]
    end=pose(m['preinsert_tcp_position'],m['goal_tcp_rotation'])
    for case in report['cases']:
        i=case['id'];held=json.loads((a.probes/f'case_{i:02d}.json').read_text())['held_info']
        current=pose(held['tcp_position'],held['tcp_rotation'])
        q={j['name']:packet['initial_qpos'][j['qpos_index']] for j in packet['joints']}
        q.update(zip(names,held['joint_positions']))
        records=[]
        for index,T in enumerate(decoded_approach(m,samples['target_socket'][i])):
            target=current@T
            try:
                q=ik.solve(q,target);p,r=pose_error(ik.kin.tcp(q),target)
                records.append(dict(index=index,valid=True,fk_position_error_mm=p*1000,fk_angle_error_deg=float(np.rad2deg(r))))
            except Exception as exc:
                records.append(dict(index=index,valid=False,error=repr(exc)));break
        p,r=pose_error(current@decoded_approach(m,samples['target_socket'][i])[-1],end)
        cases.append(dict(id=i,waypoints=records,all_33_reachable=len(records)==33 and all(v['valid'] for v in records),
                          rule_endpoint_position_error_mm=p*1000,rule_endpoint_rotation_error_deg=float(np.rad2deg(r))))
    result=dict(cases=cases,all_passed=all(c['all_33_reachable'] for c in cases),
                scope='discrete IK with joint limits, continuity and FK backcheck; no collision sweep or dynamic path execution')
    (a.probes/'gt_waypoint_audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
