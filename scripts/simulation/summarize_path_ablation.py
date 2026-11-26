"""Audit and summarize the matched path/goal-only study without selecting models."""
import argparse
from collections import Counter
import copy
import hashlib
import json
from pathlib import Path
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT.parent/'omi_proj/src')]
from omi_hil_rl.training.hierarchical_insertion.intervention import ScriptedInterventionSAC


def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=Path,required=True);a=p.parse_args();root=a.run
    protocol=read(root/'protocol.json');test=read(root/'test.json');models=[];paired=[];differences=[]
    routes=read(root/'routes.json') if (root/'routes.json').exists() else {}
    all_sources=[];all_worker_sources=[]
    for seed in protocol['model_seeds']:
        pair={}
        for mode in ['path','goal']:
            name=f'{mode}_{seed}';route=routes.get(name,{})
            train=Path(route.get('training_dir',root/f'rl_{name}'));evaluation=root/f'test_{name}';bcval=root/f'bcval_{name}'
            for folder in [train,evaluation,bcval]:
                receipt=read(folder/'result.json')
                assert receipt['complete'] and all(v['returncode']==0 for v in receipt['processes'].values())
                all_sources.append(read(folder/'source_hashes.json'))
                all_worker_sources.append(read(folder/'worker/execution.json')['sources_sha256'])
            e=read(evaluation/'experiment/evaluation.json');v=read(bcval/'experiment/evaluation.json')
            report=read(train/'experiment/training_report.json');meta=read(train/'experiment/system0.json')
            assert len(e['cases'])==len(test) and all(c['teacher_requests']==0 for c in e['cases'])
            assert e['source_model_sha256']==sha(train/'experiment/system0.zip')==meta['model_sha256']
            assert not set(c['seed'] for c in e['cases'])&set(meta['training_seeds'])
            for actual,planned in zip(e['cases'],test):assert actual['seed']==planned['seed'] and actual['socket_pose']==planned['socket_pose']
            assert report['num_timesteps']==protocol['online']['steps_per_model']
            initial=reactive=0;handed=set();counts=dict(policy_steps=0,intervention_steps=0,takeover_events=0,handoff_events=0)
            completions=[];trace_count=0;seen=set();target_visits=Counter()
            for trace in route.get('trace_files',[str(train/'experiment/trace.jsonl')]):
                for line in Path(trace).read_text().splitlines():
                    row=json.loads(line)
                    if row['event']!='step':continue
                    key=(row['seed'],row['step']);assert key not in seen;seen.add(key);trace_count+=1
                    if row['step']==1 and row.get('socket_pose'):
                        target_visits[tuple(row['socket_pose'][k] for k in ['dx_mm','dy_mm','yaw_deg'])]+=1
                    if row['action_source']=='policy':handed.add(row['seed']);counts['policy_steps']+=1
                    elif row['action_source']=='scripted_intervention':
                        counts['intervention_steps']+=1
                        if row['seed'] in handed:reactive+=1
                        else:initial+=1
                    if row.get('ownership_event')=='takeover':counts['takeover_events']+=1
                    if row.get('ownership_event')=='handoff':counts['handoff_events']+=1
                    if row['terminated'] or row['truncated']:completions.append(row)
            assert initial+reactive==counts['intervention_steps'] and trace_count==protocol['online']['steps_per_model']
            model=ScriptedInterventionSAC.load(train/'experiment/system0.zip',device='cpu')
            model.load_replay_buffer(train/'experiment/replay.pkl');buffer=model.replay_buffer;n=buffer.size()
            assert n==protocol['online']['steps_per_model']
            no_waypoints=not np.any(buffer.observations['reference'][:n,:,:-9]) and not np.any(buffer.next_observations['reference'][:n,:,:-9])
            assert no_waypoints==(mode=='goal')
            assert np.any(buffer.observations['reference'][:n,:,-9:])
            assert model.max_policy_std==protocol['online']['max_policy_std']
            assert model.actor_learning_rate==protocol['online']['actor_learning_rate']
            del model,buffer
            record=dict(mode=mode,training_seed=seed,bc_validation=dict(successes=v['successes'],cases=len(v['cases'])),
                training=dict(steps=report['num_timesteps'],completed_episodes=len(completions),
                    assisted_successes=sum(x['success'] and x['intervention_stats']['intervention_steps']>0 for x in completions),counts=counts,
                    initial_teacher_steps=initial,reactive_teacher_steps=reactive,intervention_fraction=counts['intervention_steps']/report['num_timesteps'],
                    sac_updates=report.get('sac_updates'),distinct_training_targets=len(target_visits),
                    target_visits=[dict(pose=list(p),episodes=n) for p,n in sorted(target_visits.items())]),
                test=dict(successes=e['successes'],cases=len(e['cases']),failure_counts=dict(Counter(x['failure'] for x in e['cases'] if not x['success'])),details=e['cases']),
                goal_only_waypoint_absence_verified=no_waypoints,model_sha256=meta['model_sha256'],continuation=route)
            models.append(record);pair[mode]=record
        l=read(Path(routes.get(f'path_{seed}',{}).get('training_dir',root/f'rl_path_{seed}'))/'experiment/system0.json')
        r=read(Path(routes.get(f'goal_{seed}',{}).get('training_dir',root/f'rl_goal_{seed}'))/'experiment/system0.json')
        common=copy.deepcopy(r['config']);common['schema'].pop('reference_input')
        assert l['config']==common and l['training_recipe']==r['training_recipe']
        x=np.array([c['success'] for c in pair['path']['test']['details']],int)
        y=np.array([c['success'] for c in pair['goal']['test']['details']],int)
        differences.append(x-y)
        both=np.flatnonzero(x&y)
        paired.append(dict(training_seed=seed,path_successes=int(x.sum()),goal_successes=int(y.sum()),cases=len(test),
            difference_percentage_points=float((x-y).mean()*100),path_only_wins=int(((x==1)&(y==0)).sum()),
            goal_only_wins=int(((x==0)&(y==1)).sum()),both_success=int(len(both)),both_fail=int(((x==0)&(y==0)).sum()),
            mean_step_difference_on_common_successes=float(np.mean([pair['path']['test']['details'][i]['steps']-pair['goal']['test']['details'][i]['steps'] for i in both])) if len(both) else None))
    assert all(s==all_sources[0] for s in all_sources),'learner source versions changed across paired stages'
    assert all(s==all_worker_sources[0] for s in all_worker_sources),'worker source versions changed across paired stages'
    d=np.array(differences);target_means=d.mean(0)
    rng=np.random.default_rng(20261126);boot=target_means[rng.integers(0,len(test),(10000,len(test)))].mean(1)*100
    seed_draws=rng.integers(0,len(d),(10000,len(d)))
    target_draws=rng.integers(0,len(test),(10000,len(test)))
    joint_boot=d[seed_draws[:,:,None],target_draws[:,None,:]].mean((1,2))*100
    totals={mode:dict(successes=sum(m['test']['successes'] for m in models if m['mode']==mode),
        trials=sum(m['test']['cases'] for m in models if m['mode']==mode)) for mode in ['path','goal']}
    summary=dict(protocol=protocol,collection=read(root/'collection_audit.json'),pairing=read(root/'pairing_audit.json'),models=models,
        paired_results=paired,pooled=totals,difference_percentage_points=float(d.mean()*100),
        target_resampling_interval_percentage_points=np.percentile(boot,[2.5,97.5]).tolist(),
        seed_and_target_resampling_interval_percentage_points=np.percentile(joint_boot,[2.5,97.5]).tolist(),
        uncertainty_scope='targets resampled jointly across the two trained seeds; does not quantify unseen training-seed or real-world uncertainty',
        joint_resampling_caveat='only two observed training seeds; descriptive resampling range, not robust significance evidence',
        learner_sources_identical=True,worker_sources_identical=True,
        scope='incremental GT waypoint-preview value over shared goal/progress/history; not removal of all target information or visual System1 comparison')
    (root/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.font_manager import FontProperties
    font=FontProperties(fname='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')
    fig,axes=plt.subplots(2,2,figsize=(15,10),facecolor='#f6f8fb')
    colors={'path':'#297eb3','goal':'#d18a35'};width=.32;x=np.arange(len(protocol['model_seeds']))
    for ax,stage,title in [(axes[0,0],'bc_validation','BC阶段：8目标验证'),(axes[0,1],'test','最终RL：24目标无接管测试')]:
        for j,mode in enumerate(['path','goal']):
            selected=[m for m in models if m['mode']==mode]
            scores=[100*m[stage]['successes']/m[stage]['cases'] for m in selected]
            bars=ax.bar(x+(j-.5)*width,scores,width,color=colors[mode],label='有路径预览' if mode=='path' else '仅目标，无路径')
            for bar,m in zip(bars,selected):ax.text(bar.get_x()+bar.get_width()/2,bar.get_height()+2,f"{m[stage]['successes']}/{m[stage]['cases']}",ha='center',fontsize=11)
        ax.set_ylim(0,115);ax.set_xticks(x,[str(s) for s in protocol['model_seeds']]);ax.set_ylabel('成功率 / %',fontproperties=font)
        ax.set_title(title,fontproperties=font,fontsize=16);ax.legend(prop=font,loc='lower right');ax.grid(axis='y',alpha=.18)
    ax=axes[1,0]
    for j,mode in enumerate(['path','goal']):
        selected=[m for m in models if m['mode']==mode]
        initial=np.array([100*m['training']['initial_teacher_steps']/m['training']['steps'] for m in selected])
        reactive=np.array([100*m['training']['reactive_teacher_steps']/m['training']['steps'] for m in selected])
        ax.bar(x+(j-.5)*width,initial,width,color=colors[mode],alpha=.35)
        ax.bar(x+(j-.5)*width,reactive,width,bottom=initial,color=colors[mode])
        for pos,value in zip(x+(j-.5)*width,initial+reactive):ax.text(pos,value+2,f'{value:.1f}%',ha='center')
    ax.set_xticks(x,[str(s) for s in protocol['model_seeds']]);ax.set_ylim(0,110)
    ax.set_title('训练接管比例：浅色初始接管，深色后续接管',fontproperties=font,fontsize=14)
    ax.set_ylabel('交互步占比 / %',fontproperties=font);ax.grid(axis='y',alpha=.18)
    ax=axes[1,1];ax.axis('off')
    text=(f"最终配对差值：{summary['difference_percentage_points']:+.1f} 个百分点\n\n"
          f"路径组：{totals['path']['successes']}/{totals['path']['trials']}\n"
          f"无路径组：{totals['goal']['successes']}/{totals['goal']['trials']}\n\n"
          f"仅路径组成功：{sum(p['path_only_wins'] for p in paired)}\n"
          f"仅无路径组成功：{sum(p['goal_only_wins'] for p in paired)}\n\n"
          '两组共享目标、数据、网络和预算。\n只测GT路径预览，不代表视觉或真机效果。\n仅两个训练种子，逐种子结果同样重要。')
    ax.text(.04,.95,text,va='top',fontproperties=font,fontsize=14,linespacing=1.5)
    fig.suptitle('System1路径预览增益 · 同预算配对实验',fontproperties=font,fontsize=23)
    fig.tight_layout(rect=(0,0,1,.95));fig.savefig(root/'comparison.png',dpi=140);plt.close(fig)
    print(json.dumps(dict(pooled=totals,paired=paired,difference_percentage_points=summary['difference_percentage_points']),indent=2))


if __name__=='__main__':main()
