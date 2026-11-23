"""Summarize the bounded smooth-guide physics qualification, not RL results."""
import argparse
import json
import re
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    args = parser.parse_args()
    root = args.run
    local = ['local_normal', 'local_offset_plus', 'local_offset_minus', 'local_yaw_plus', 'local_half_step']
    robot = ['robot_recovery_plus_slow', 'robot_recovery_minus_slow', 'robot_aligned_half_step']
    summaries = {}
    for name in local+robot:
        report_path = root/name/'report.json'
        if report_path.exists():
            report = json.loads(report_path.read_text())
        else:
            failure = json.loads((root/name/'failure.json').read_text())
            trace_path = root/name/'trajectory.jsonl'
            trace = [json.loads(line) for line in trace_path.read_text().splitlines()] if trace_path.exists() else []
            report = dict(accepted=False, error=failure['error'],
                final_depth_mm=trace[-1]['insertion_depth_mm'] if trace else None,
                last_phase=trace[-1].get('probe_phase') if trace else None,
                phases_completed_or_attempted=list(dict.fromkeys(r.get('probe_phase') for r in trace)),
                steps_recorded=len(trace))
        summaries[name] = {k:v for k,v in report.items() if k in (
            'accepted', 'phases', 'interior', 'offset_mm', 'dt', 'seed',
            'reset_count', 'teleport_after_reset', 'learned_policy', 'contact_offset_m',
            'seated_target_overtravel_mm', 'minimum_final_axial_target_increment_mm',
            'error', 'final_depth_mm', 'last_phase', 'phases_completed_or_attempted', 'steps_recorded')}
        trace = [json.loads(line) for line in (root/name/'trajectory.jsonl').read_text().splitlines()]
        summaries[name]['all_substeps_contact_sum_peak_N'] = max(r['step_peak_contact_force_N'] for r in trace)
        summaries[name]['sampled_contact_sum_peak_N'] = max(r['contact_force_N'] for r in trace)
    all_receipts = sum([json.loads((root/name).read_text()) for name in (
        'matrix_receipts.json', 'robot_matrix_receipts.json', 'slow_matrix_receipts.json')], [])
    receipts = [r for r in all_receipts if r['name'] in local+robot]
    assert len(receipts) == 8 and set(local+robot) == {r['name'] for r in receipts}, receipts
    for receipt in receipts:
        if receipt['exit_code'] != 0:
            assert not summaries[receipt['name']]['accepted'], receipt
    cooking = json.loads((root/'local_normal/cooking_audit.json').read_text())
    packet = json.loads((root/'local_transfer/transfer.json').read_text())
    shapes = [g for g in packet['geoms'] if g['contact']]
    scene_text = (root/'local_normal/scene.usda').read_text()
    assert len(shapes) == 6 and all(g['kind'] == 6 for g in shapes) and cooking == []
    assert all(re.search(r'def Cube "'+re.escape(g['name'])+'"', scene_text) for g in shapes)
    summary = dict(qualification_cases=summaries, passed=sum(d['accepted'] for d in summaries.values()),
                   total=len(summaries), learned_policy_evaluated=False, physically_calibrated=False,
                   local_passed=sum(summaries[n]['accepted'] for n in local), local_total=len(local),
                   robot_passed=sum(summaries[n]['accepted'] for n in robot), robot_total=len(robot),
                   candidate='SIM-SMOOTH-GUIDE-candidate-r04',
                   protocol=json.loads((root/'protocol.json').read_text()),
                   subprocess_receipts=receipts, cooked_geometry=cooking,
                   native_box_shapes=[g['name'] for g in shapes],
                   other_development_receipts=[r for r in all_receipts if r['name'] not in local+robot],
                   failed_probe_development=['parent/robot_recovery_plus: phase bookkeeping stopped after successful outside positioning',
                       'parent/robot_recovery_plus_r02: force-only obstruction detector timed out despite sustained entrance contact',
                       'r01 full-motion cases: top-only shoulder detector rejected real bottom/side mouth contact; final r02 recognizes all four mouth faces',
                       'r02 5um-offset trials: entrance penetration exceeded 0.05 mm with both faster and slower approach; final recipe restores 0.1um offset',
                       'r02 half-step with 10um final increment: stalled before shoulder; final recipe uses bounded 50um target increment',
                       'r04 shoulder-only 5um offset with mesh convexes: initial stop penetration exceeded 0.05mm; native box representation tested separately'],
                   development_failure_files=[str(p) for p in sorted(root.parent.rglob('failure.json'))],
                   source_preservation=json.loads((root/'source_preservation.json').read_text()))
    (root/'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n')
    font = Path('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')
    if font.exists():
        font_manager.fontManager.addfont(str(font))
        plt.rcParams['font.family'] = font_manager.FontProperties(fname=str(font)).get_name()
    plt.rcParams['axes.unicode_minus'] = False
    rows = [json.loads(line) for line in (root/robot[0]/'trajectory.jsonl').read_text().splitlines()]
    time = np.arange(1, len(rows)+1)*.1
    depth = np.array([r['insertion_depth_mm'] for r in rows])
    fig, ax = plt.subplots(2, 2, figsize=(14, 9), layout='constrained')
    fig.suptitle(f'接触候选检查：局部 {summary["local_passed"]}/{summary["local_total"]}；机械臂 {summary["robot_passed"]}/{summary["robot_total"]}\n入口受阻 → 退回纠偏 → 内部顺滑（目标行为）；未重新训练 BC／RL', fontsize=16)
    channel = ax[0, 0]
    for sign in [-1, 1]:
        channel.fill([0, 60, 60, 0], np.array([9.4,9.4,10.9,10.9])*sign, color='#b0bec5')
    channel.fill([0,51.28,51.28,0], [-9.05,-9.05,9.05,9.05], color='#4caf50', alpha=.45, label='轴身对准示意')
    channel.plot([0,0],[-11,11],color='#d32f2f',ls='--',label='入口')
    channel.set(xlim=(-3,55),ylim=(-12,12),xlabel='距入口深度 / mm',ylabel='相对中心横向位置 / mm',title='碰撞截面示意：连续侧壁与平直入口')
    channel.legend(fontsize=9,loc='lower center')
    channel.text(26,0,'18.8 mm 通道 / 18.1 mm 轴身\n所有新碰撞体始终启用',ha='center',va='center',fontsize=10)
    phase_labels = {'offset_outside':'入口外偏移','approach_offset_outside':'靠近入口外','push_misaligned':'偏着轻推','retreat_same_offset':'保持偏移后退',
                    'align_outside':'入口外纠偏','insert_aligned':'对准插入','withdraw_aligned':'退出'}
    phases = list(dict.fromkeys(r['probe_phase'] for r in rows))
    colors = plt.get_cmap('tab10').colors
    for i, phase in enumerate(phases):
        mask = np.array([r['probe_phase']==phase for r in rows])
        ax[0,1].plot(time[mask],depth[mask],color=colors[i],label=phase_labels[phase],lw=2)
    ax[0,1].axhline(0,color='gray',ls='--',lw=.8)
    ax[0,1].set(xlabel='仿真时间 / s',ylabel='插入深度 / mm',title='+1 mm 偏移后的恢复尝试；仅开头 reset')
    ax[0,1].legend(fontsize=8,ncol=2)
    ax[1,0].plot(time,[r['scalar_contact_sum_mean_N'] for r in rows],label='接触力模长之和：控制区间均值')
    ax[1,0].plot(time,[r['axial_absolute_sum_mean_N'] for r in rows],label='轴向投影绝对值之和：控制区间均值',ls='--')
    ax[1,0].set(xlabel='仿真时间 / s',ylabel='接触指标 / N',title='区分接触方向；这些指标不是净插入力')
    ax[1,0].legend(fontsize=8)
    for i,name in enumerate(robot):
        data=[json.loads(s) for s in (root/name/'trajectory.jsonl').read_text().splitlines()]
        data=[r for r in data if r['probe_phase']=='insert_aligned']
        ax[1,1].plot([r['insertion_depth_mm'] for r in data],
                     [r['axial_absolute_sum_mean_N'] for r in data],
                     label=['+1 mm 受阻后恢复','−1 mm 受阻后恢复','对准／半步长'][i]+('（未通过）' if not summaries[name]['accepted'] else ''),alpha=.8)
        if name == 'robot_aligned_half_step':
            ax[1,1].plot([r['insertion_depth_mm'] for r in data],
                         [r['step_peak_contact_force_N'] for r in data],
                         color='black', ls=':', label='半步长：接触力模长和的子步峰值')
    ax[1,1].axvspan(5,50.2816944,color='#4caf50',alpha=.08,label='内部检查区间')
    ax[1,1].set(xlabel='插入深度 / mm',ylabel='接触指标 / N（均值与峰值）',title='对准后的内部通行；末端仍有瞬时力峰值')
    ax[1,1].legend(fontsize=8)
    for axis in ax.flat:
        axis.grid(alpha=.2)
    fig.savefig(root/'review.png',dpi=160)
    fig.savefig(root/'review.pdf')
    print(json.dumps(dict(passed=summary['passed'],total=summary['total'],review=str(root/'review.png'))))


if __name__ == '__main__':
    main()
