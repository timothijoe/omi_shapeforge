"""Audit matched frozen-policy runs and plot measured gripper correction."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from omi_shapeforge.sim.pose_correction import gripper_pose_errors


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=Path,required=True);a=p.parse_args();root=a.run
    read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    protocol=read(root/'protocol.json');assert read(root/'result.json')['complete']
    modes={};sources=[];workers=[]
    for mode in ['path','goal']:
        run=root/mode;assert read(run/'result.json')['complete']
        evaluation=read(run/'experiment/evaluation.json')
        resets=[json.loads(s) for s in (run/'worker/reset_audit.jsonl').read_text().splitlines()]
        steps=[json.loads(s) for s in (run/'worker/step_audit.jsonl').read_text().splitlines()]
        trace=[json.loads(s) for s in (run/'experiment/trace.jsonl').read_text().splitlines() if json.loads(s)['event']=='step']
        assert len(trace)==len(steps) and len(resets)==len(evaluation['cases'])==len(protocol['cases'])
        for w,t in zip(steps,trace):
            assert w['step']==t['step'] and w['executed_action']==t['action'] and w['teacher_requests']==t['teacher_requests']==0 and t['action_source']=='policy'
        assert len({tuple(s['task_goal_position']) for s in steps})==1
        model=Path(protocol['models'][mode]);assert sha(model)==evaluation['source_model_sha256']
        assert evaluation['config']['schema']==read(model.with_suffix('.json'))['config']['schema']
        sources.append(read(run/'source_hashes.json'));workers.append(read(run/'worker/execution.json')['sources_sha256'])
        modes[mode]=dict(evaluation=evaluation,resets=resets,steps=steps,model_sha256=sha(model))
    assert sources[0]==sources[1] and workers[0]==workers[1]
    output=root/'correction';output.mkdir(exist_ok=True);records=[]
    for i,case in enumerate(protocol['cases']):
        path=modes['path']['resets'][i];goal=modes['goal']['resets'][i]
        np.testing.assert_allclose(path['tcp_position'],goal['tcp_position'],rtol=0,atol=1e-8)
        np.testing.assert_allclose(path['tcp_rotation'],goal['tcp_rotation'],rtol=0,atol=1e-8)
        data={};record=dict(name=case['name'],seed=case['seed'],request=case['initial_pose'],results={})
        for mode,m in modes.items():
            reset=m['resets'][i];evaluation=m['evaluation']['cases'][i];initial=reset['initial_pose']
            assert reset['seed']==evaluation['seed']==case['seed'] and initial['request']==case['initial_pose']
            assert initial['initial_box_overlap_mm']==0 and initial['position_error_mm']<.1 and initial['rotation_error_deg']<.05
            assert initial['initialization_solver']['physical_preparation_actions']==0 and evaluation['teacher_requests']==0
            rows=[reset]+[s for s in m['steps'] if s['episode']==i+1]
            assert [r['step'] for r in rows]==list(range(evaluation['steps']+1))
            axis=-np.asarray(reset['socket_to_world']['rotation'])[:,1]
            data[mode]=[dict(step=r['step'],time_s=r['step']/10,depth_mm=r['insertion_depth_mm'],**gripper_pose_errors(r,initial,axis)) for r in rows]
            first,last=data[mode][0],data[mode][-1]
            for key,tolerance in [('lateral_mm',.1),('vertical_mm',.1),('pitch_deg',.05),('yaw_deg',.05)]:
                assert abs(first[key]-case['initial_pose'][key])<tolerance
            record['results'][mode]=dict(success=evaluation['success'],steps=evaluation['steps'],failure=evaluation['failure'],
                initial=first,final=last,actual_initial_gap_mm=initial['actual_tip_gap_mm'])
            with (output/f'{case["name"]}_{mode}.csv').open('w') as stream:
                writer=csv.DictWriter(stream,fieldnames=list(first));writer.writeheader();writer.writerows(data[mode])
        metrics=dict(definition='signed gripper-center transverse offsets in aligned gripper Y/Z; progress removed along actual insertion axis; intrinsic ZYX orientation relative to aligned gripper',
            scope='measured state diagnostic only; never used to alter task success or control',case=case,modes=data)
        (output/f'{case["name"]}.json').write_text(json.dumps(metrics,indent=2)+'\n')
        records.append(record)
    summary=dict(scope=protocol['purpose'],training_seed=protocol['training_seed'],cases=records,
        totals={m:dict(successes=v['evaluation']['successes'],cases=len(records),model_sha256=v['model_sha256']) for m,v in modes.items()},
        initial_poses_matched=True,no_initial_overlap=True,all_teacher_requests_zero=True,task_goal_unchanged=True,
        learner_sources_identical=True,worker_sources_identical=True,
        caveat='one frozen model pair, one reset per explicit condition; signed correction diagnostics do not replace insertion success')
    (root/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.font_manager import FontProperties
    font=FontProperties(fname='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')
    for record in records:
        metrics=read(output/f'{record["name"]}.json');fig,axes=plt.subplots(2,2,figsize=(13,7),facecolor='#f6f8fb')
        for ax,(key,label) in zip(axes.flat,[('lateral_mm','夹爪横向偏差 / mm'),('vertical_mm','夹爪上下偏差 / mm'),('pitch_deg','俯仰偏差 / °'),('yaw_deg','偏航偏差 / °')]):
            for mode,color,title in [('path','#2186ae','有路径'),('goal','#c47d28','无路径')]:
                rows=metrics['modes'][mode];ax.plot([r['time_s'] for r in rows],[r[key] for r in rows],color=color,label=title,lw=1.8)
                ax.scatter(rows[-1]['time_s'],rows[-1][key],color=color,s=24)
            ax.axhline(0,color='#6d7680',linestyle='--',lw=.8);ax.set_title(label,fontproperties=font);ax.set_xlabel('仿真时间 / 秒',fontproperties=font);ax.grid(alpha=.18);ax.legend(prop=font)
        outcome=' / '.join(('路径' if m=='path' else '无路径')+('成功' if record['results'][m]['success'] else '失败') for m in ['path','goal'])
        fig.suptitle(f'{record["name"]} · {outcome} · 曲线终点为实际结束时刻',fontproperties=font,fontsize=16)
        fig.tight_layout(rect=(0,0,1,.95));fig.savefig(output/f'{record["name"]}.png',dpi=140);plt.close(fig)
    print(json.dumps(summary['totals'],indent=2))


if __name__=='__main__':main()
