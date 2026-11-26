"""Audit fresh randomized BC/SAC study; report both stages without test selection."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT.parent/'omi_proj/src')]
from omi_hil_rl.training.hierarchical_insertion.intervention import ScriptedInterventionSAC
from omi_hil_rl.training.hierarchical_insertion.randomization import validate_reset_distribution,sample_reset


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run',type=Path,required=True);a=parser.parse_args();root=a.run
    read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    protocol=read(root/'protocol.json');test=read(root/'test.json');validation=read(root/'validation.json')
    distribution=validate_reset_distribution(read(root/'reset_distribution.json'));dataset=read(root/'dataset/dataset.json')
    assert all(r['success'] for r in dataset['episodes']) and len(dataset['episodes'])==120
    models=[];sources=[];worker_sources=[];paired=[]
    for shard in range(2):
        folder=root/f'collect_{shard}';assert read(folder/'result.json')['complete']
        sources.append(read(folder/'source_hashes.json'));worker_sources.append(read(folder/'worker/execution.json')['sources_sha256'])
    for seed in protocol['model_seeds']:
        pair={}
        for mode in ['path','goal']:
            name=f'{mode}_{seed}';bc=root/f'bc_{name}';rl=root/f'rl_{name}';meta=read(rl/'experiment/system0.json')
            report=read(rl/'experiment/training_report.json');audit=read(rl/'experiment/replay_validation.json')
            assert read(bc/'training_report.json')['bc_updates']==protocol['bc']['updates_per_model']
            assert meta['initial_bc_steps']==protocol['bc']['updates_per_model'] and meta['config']['reset_distribution']==distribution
            assert meta['demo_dataset_sha256']==sha(root/'dataset/dataset.json')
            assert report['num_timesteps']==report['sac_updates']==protocol['online']['steps_per_model']
            assert audit['all_actions_and_proposals_match_trace'] and audit['history_uses_executed_action'] and audit['reward_terminal_timeout_and_wrench_verified']
            assert audit['transitions']==protocol['online']['steps_per_model']
            records={}
            for prefix,model_dir,plan in [('bcval',bc,validation),('bctest',bc,test),('test',rl/'experiment',test)]:
                folder=root/f'{prefix}_{name}';receipt=read(folder/'result.json')
                assert receipt['complete'] and all(p['returncode']==0 for p in receipt['processes'].values())
                sources.append(read(folder/'source_hashes.json'));worker_sources.append(read(folder/'worker/execution.json')['sources_sha256'])
                e=read(folder/'experiment/evaluation.json');assert e['source_model_sha256']==sha(model_dir/'system0.zip')
                assert len(e['cases'])==len(plan) and not set(c['seed'] for c in e['cases'])&set(read(model_dir/'system0.json')['training_seeds'])
                resets=[json.loads(l) for l in (folder/'worker/reset_audit.jsonl').read_text().splitlines()]
                assert len(resets)==len(plan)
                for actual,wanted,reset in zip(e['cases'],plan,resets):
                    assert actual['seed']==reset['seed']==wanted['seed'] and actual['socket_pose']==wanted['socket_pose']
                    assert actual['teacher_requests']==0 and actual['initial_pose']['request']==wanted['initial_pose']
                    assert actual['initial_pose']==reset['initial_pose'] and actual['initial_pose']['initial_box_overlap_mm']==0
                records[prefix]=dict(successes=e['successes'],cases=len(e['cases']),details=e['cases'])
            assert read(rl/'result.json')['complete'];sources.append(read(rl/'source_hashes.json'));worker_sources.append(read(rl/'worker/execution.json')['sources_sha256'])
            resets=[json.loads(l) for l in (rl/'worker/reset_audit.jsonl').read_text().splitlines()]
            for row in resets:
                expected=sample_reset(row['seed'],distribution)
                assert row['socket_pose']==expected['socket_pose'] and row['initial_pose']['request']==expected['initial_pose']
                assert row['initial_pose']['initial_box_overlap_mm']==0
            model=ScriptedInterventionSAC.load(rl/'experiment/system0.zip',device='cpu');model.load_replay_buffer(rl/'experiment/replay.pkl');buffer=model.replay_buffer;n=buffer.size()
            assert n==protocol['online']['steps_per_model']
            no_waypoints=not np.any(buffer.observations['reference'][:n,:,:-9]) and not np.any(buffer.next_observations['reference'][:n,:,:-9])
            assert no_waypoints==(mode=='goal') and np.any(buffer.observations['reference'][:n,:,-9:])
            del model,buffer
            counts=report['run_step_counts'];assert counts['policy_steps']+counts['intervention_steps']==n
            record=dict(mode=mode,training_seed=seed,bc_updates=protocol['bc']['updates_per_model'],online_steps=n,
                sac_updates=report['sac_updates'],training_counts=counts,intervention_fraction=counts['intervention_steps']/n,
                bc_validation=records['bcval'],bc_test=records['bctest'],rl_test=records['test'],
                reset_distribution_verified=True,online_reset_count=len(resets),model_sha256=meta['model_sha256'],goal_waypoint_absence_verified=no_waypoints)
            models.append(record);pair[mode]=record
        left=read(root/f'rl_path_{seed}/experiment/system0.json');right=read(root/f'rl_goal_{seed}/experiment/system0.json')
        comparable=copy.deepcopy(right['config']);comparable['schema'].pop('reference_input')
        assert comparable==left['config'] and right['training_recipe']==left['training_recipe']
        for stage in ['bc_test','rl_test']:
            x=np.array([c['success'] for c in pair['path'][stage]['details']],int);y=np.array([c['success'] for c in pair['goal'][stage]['details']],int)
            paired.append(dict(seed=seed,stage=stage,path_successes=int(x.sum()),goal_successes=int(y.sum()),cases=len(x),
                difference_percentage_points=float((x-y).mean()*100),path_only_wins=int(((x==1)&(y==0)).sum()),goal_only_wins=int(((x==0)&(y==1)).sum())))
    assert all(s==sources[0] for s in sources) and all(s==worker_sources[0] for s in worker_sources)
    totals={stage:{mode:dict(successes=sum(m[stage]['successes'] for m in models if m['mode']==mode),trials=sum(m[stage]['cases'] for m in models if m['mode']==mode)) for mode in ['path','goal']} for stage in ['bc_test','rl_test']}
    report=dict(protocol=protocol,collection=read(root/'collect_audit.json'),pairing=read(root/'pairing_audit.json'),models=models,paired_results=paired,pooled=totals,
        all_sources_identical=True,all_replay_checks_passed=True,all_online_reset_distributions_verified=True,
        interpretation='fresh BC then assisted SAC; BC and RL tested on same heldout conditions with no teacher; report regressions as well as improvements',
        caveat='two training seeds and 24 fixed heldout cases; ideal GT, fixed attachment, XY target shifts only; not visual or real-robot generalization')
    (root/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.font_manager import FontProperties
    font=FontProperties(fname='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')
    fig,axes=plt.subplots(1,3,figsize=(17,5),facecolor='#f6f8fb');x=np.arange(len(protocol['model_seeds']));width=.34
    for ax,stage,title in [(axes[0],'bc_test','BC：同一留出集，无接管'),(axes[1],'rl_test','RL：同一留出集，无接管')]:
        for j,mode in enumerate(['path','goal']):
            rows=[m for m in models if m['mode']==mode];scores=[100*m[stage]['successes']/m[stage]['cases'] for m in rows]
            bars=ax.bar(x+(j-.5)*width,scores,width,color='#2984b0' if mode=='path' else '#ca8938',label='有路径' if mode=='path' else '仅目标')
            for bar,m in zip(bars,rows):ax.text(bar.get_x()+bar.get_width()/2,bar.get_height()+2,f"{m[stage]['successes']}/{m[stage]['cases']}",ha='center')
        ax.set_ylim(0,115);ax.set_xticks(x,[str(s) for s in protocol['model_seeds']]);ax.set_title(title,fontproperties=font);ax.legend(prop=font);ax.grid(axis='y',alpha=.2)
    ax=axes[2]
    for j,mode in enumerate(['path','goal']):
        rows=[m for m in models if m['mode']==mode];values=[m['intervention_fraction']*100 for m in rows]
        bars=ax.bar(x+(j-.5)*width,values,width,color='#2984b0' if mode=='path' else '#ca8938')
        for bar,value in zip(bars,values):ax.text(bar.get_x()+bar.get_width()/2,bar.get_height()+2,f'{value:.1f}%',ha='center')
    ax.set_ylim(0,110);ax.set_xticks(x,[str(s) for s in protocol['model_seeds']]);ax.set_title('训练规则接管占比 / %',fontproperties=font);ax.grid(axis='y',alpha=.2)
    fig.suptitle('随机插口＋随机远初态 · 新数据与同预算重训',fontproperties=font,fontsize=21);fig.tight_layout(rect=(0,0,1,.94));fig.savefig(root/'comparison.png',dpi=140);plt.close(fig)
    print(json.dumps(dict(pooled=totals,paired=paired),indent=2))


if __name__=='__main__':main()
