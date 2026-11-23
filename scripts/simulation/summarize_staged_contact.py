"""Summarize staged-contact traces without relabelling historical experiments."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',type=Path,required=True)
    args=parser.parse_args();root=args.run
    names=['aligned_520','recovery_plus','recovery_minus','aligned_half_step','interior_rub']
    reports={};traces={};summary={}
    for name in names:
        reports[name]=json.loads((root/name/'report.json').read_text())
        rows=[json.loads(line) for line in (root/name/'trajectory.jsonl').read_text().splitlines()]
        traces[name]=rows
        assert all(np.isclose(r['contact_force_mean_N'],r['scalar_contact_sum_mean_N'],atol=1e-9) for r in rows)
        assert reports[name]['reset_count']==1 and not reports[name]['teleport_after_reset']
        assert rows[-1]['is_success'] and rows[-1]['entry_qualified']
        inside=next(r for r in rows if r.get('entry_qualified'))
        assert inside['entry_good_samples']>=3 and inside['insertion_depth_mm']>=5
        phases=reports[name]['phases']
        if name.startswith('recovery_'):
            blocked=next(p for p in phases if p['phase']=='push_misaligned')
            retreat=next(p for p in phases if p['phase']=='retreat_same_offset')
            assert blocked['reason']=='entrance_blocked' and abs(blocked['depth_mm'])<.1
            assert retreat['depth_mm']< -4.8
            assert not any(r['is_success'] for r in rows if r['probe_phase']!='insert_aligned')
            assert not any(r['entry_qualified'] for r in rows if r['probe_phase']=='push_misaligned')
        summary[name]=dict(accepted=reports[name]['accepted'],steps=len(rows),phases=phases,
            first_qualified_depth_mm=inside['insertion_depth_mm'],final_depth_mm=rows[-1]['insertion_depth_mm'],
            point_penetration_peak_mm=max(r['step_peak_penetration_mm'] for r in rows),
            control_geometry_overlap_peak_mm=max(r['control_box_overlap_mm'] for r in rows),
            contact_mean_peak_N=max(r['contact_force_mean_N'] for r in rows),
            contact_substep_peak_N=max(r['step_peak_contact_force_N'] for r in rows),
            old_point_guard_exceedance_intervals=sum(r.get('legacy_point_guard_would_stop',False) for r in rows),
            old_sample_force_guard_exceedance_intervals=sum(r.get('legacy_force_guard_would_stop',False) for r in rows),
            source_hashes=json.loads((root/name/'execution.json').read_text())['sources_sha256'])
    rubbing=[r for r in traces['interior_rub'] if r['probe_phase']=='slide_with_contact']
    assert sum(r['step_any_module_contact'] for r in rubbing)>0
    result=dict(task_contract='entry-strict-interior-tolerant-v1',passed=sum(x['accepted'] for x in summary.values()),
        total=len(summary),cases=summary,
        interior_rub=dict(contact_intervals=sum(r['step_any_module_contact'] for r in rubbing),intervals=len(rubbing),
            mean_contact_peak_N=max(r['contact_force_mean_N'] for r in rubbing),
            start_depth_mm=rubbing[0]['insertion_depth_mm'],end_depth_mm=rubbing[-1]['insertion_depth_mm']),
        geometry_and_friction_changed=False,rl_retrained=False,real_hardware_calibrated=False,
        limitations=['New task criteria; not an improvement of old BC/RL scores',
            'Contact norm-sum proxy is not real wrist force; thresholds are hypotheses',
            'OBB overlap is control-sampled, not the maximum over physics substeps',
            'Recovery here is a scripted validation controller; online RL recovery arbitration is not integrated'])
    (root/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    font=Path('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')
    if font.exists():
        font_manager.fontManager.addfont(str(font));plt.rcParams['font.family']=font_manager.FontProperties(fname=str(font)).get_name()
    plt.rcParams['axes.unicode_minus']=False
    fig,ax=plt.subplots(2,2,figsize=(14,9),layout='constrained')
    fig.suptitle(f'分阶段接触任务：{result["passed"]}/{result["total"]} 条脚本轨迹满足新判据\n几何与摩擦未改；碰撞全程开启；旧成绩不重算；未重训BC／RL',fontsize=16)
    colors=plt.get_cmap('tab10').colors
    for i,name in enumerate(['recovery_plus','recovery_minus']):
        rows=traces[name];time=np.arange(1,len(rows)+1)*.1
        ax[0,0].plot(time,[r['insertion_depth_mm'] for r in rows],label=['偏+1 mm','偏−1 mm'][i],alpha=.85)
    ax[0,0].axhline(0,color='gray',ls='--');ax[0,0].axhline(5,color='green',ls=':',label='入口资格段终点')
    ax[0,0].set(xlabel='仿真时间 / s',ylabel='深度 / mm',title='真实阻挡→退回→对准→重插（各仅reset一次）');ax[0,0].legend(fontsize=9)
    rows=traces['recovery_plus'];time=np.arange(1,len(rows)+1)*.1
    ax[0,1].plot(time,[r['lateral_error_mm'] for r in rows],label='横向偏差')
    ax[0,1].axhline(.15,color='orange',ls='--',label='入口资格：<0.15 mm')
    first=next(i for i,r in enumerate(rows) if r['entry_qualified'])
    ax[0,1].axvline((first+1)*.1,color='green',ls=':',label='首次通过入口资格')
    ax[0,1].set(xlabel='仿真时间 / s',ylabel='横向偏差 / mm',title='偏着无法获得入口资格，退回后才纠偏');ax[0,1].legend(fontsize=9)
    rows=traces['interior_rub'];time=np.arange(1,len(rows)+1)*.1
    ax[1,0].plot(time,[r['contact_force_mean_N'] for r in rows],label='100ms报告冲量模长和均值')
    ax[1,0].plot(time,[r['step_peak_contact_force_N'] for r in rows],ls=':',alpha=.7,label='物理子步峰值（保留诊断）')
    ax[1,0].set_yscale('symlog',linthresh=.001)
    rub_indices=[i for i,r in enumerate(rows) if r['probe_phase']=='slide_with_contact']
    ax[1,0].axvspan((min(rub_indices)+1)*.1,(max(rub_indices)+1)*.1,color='green',alpha=.1,label='内壁轻擦并前进')
    ax[1,0].set(xlabel='仿真时间 / s',ylabel='接触指标 / N',title='内部有实际接触，仍能滑动并最终到位');ax[1,0].legend(fontsize=8)
    ax[1,1].plot(time,[r['step_peak_penetration_mm'] for r in rows],label='子步最大接触点穿透指标')
    ax[1,1].plot(time,[r['control_box_overlap_mm'] for r in rows],label='控制时刻盒几何重叠')
    ax[1,1].plot(time,[r['active_point_penetration_limit_mm'] for r in rows],ls=':',label='新阶段点指标上限')
    ax[1,1].axhline(.05,color='red',ls='--',label='旧统一点指标门槛')
    ax[1,1].set(xlabel='仿真时间 / s',ylabel='距离 / mm',title='原始波动不删除；几何重叠与点报告分开');ax[1,1].legend(fontsize=8)
    for axis in ax.flat:axis.grid(alpha=.2)
    fig.savefig(root/'review.png',dpi=150);fig.savefig(root/'review.pdf')
    print(json.dumps(dict(passed=result['passed'],total=result['total'],rub=result['interior_rub']),ensure_ascii=False))


if __name__=='__main__':main()
