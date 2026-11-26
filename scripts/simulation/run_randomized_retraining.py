"""Bounded fresh-BC then assisted-SAC study with randomized target and starts.

Run --phase pilot first. Freeze both source trees before --phase study.
Every native stage must finish cleanly and every demonstration must succeed.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from omi_shapeforge.sim.process_supervisor import OwnedProcess,write_json


def read(path):return json.loads(Path(path).read_text())
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def audit_collection(run,prefix,plan_file,merge=False):
    expected={c['seed']:c for c in read(run/plan_file)};records=[];schema=config=None
    destination=run/'dataset'
    if merge:destination.mkdir(exist_ok=False)
    for shard in range(2):
        folder=run/f'{prefix}_{shard}';assert read(folder/'result.json')['complete']
        data=read(folder/'experiment/dataset.json')
        if schema is None:schema=data['schema'];config=data['config']
        assert schema==data['schema'] and config==data['config']
        resets={x['seed']:x for x in map(json.loads,(folder/'worker/reset_audit.jsonl').read_text().splitlines())}
        for row in data['episodes']:
            planned=expected[row['seed']];initial=row['initial_pose']
            assert row['split']==planned['split'] and row['socket_pose']==planned['socket_pose']
            assert initial['request']==planned['initial_pose'] and initial==resets[row['seed']]['initial_pose']
            assert initial['initial_box_overlap_mm']==0 and initial['position_error_mm']<.1 and initial['rotation_error_deg']<.05
            assert initial['initialization_solver']['physical_preparation_actions']==0
            assert row['teacher_requests']==row['steps']
            file=folder/'experiment'/row['file'];assert sha(file)==row['sha256']
            records.append(dict(row,file=os.path.relpath(file,destination)))
    assert set(expected)=={r['seed'] for r in records} and len(expected)==len(records)
    records.sort(key=lambda r:r['seed'])
    report=dict(episodes=len(records),successes=sum(r['success'] for r in records),
        failures=[r for r in records if not r['success']],all_hashes_and_actual_initial_poses_verified=True,
        splits={s:dict(episodes=sum(r['split']==s for r in records),successes=sum(r['split']==s and r['success'] for r in records),
                       steps=sum(r['steps'] for r in records if r['split']==s)) for s in ['train','val']})
    write_json(run/(prefix+'_audit.json'),report)
    if report['successes']!=len(records):raise RuntimeError('demonstration quality gate failed; failed episodes preserved; training not started')
    if merge:
        write_json(destination/'dataset.json',dict(schema=schema,config=config,episodes=records,
            provenance='all planned expert episodes passed; same source observations/actions for both conditions; only waypoint slots masked on goal-only read'))
        write_json(destination/'config.json',config)
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=Path,required=True);p.add_argument('--phase',choices=['pilot','study'],required=True)
    a=p.parse_args();run=a.run.resolve();protocol=read(run/'protocol.json')
    python='/data/shapeforge/runtime/envs/omi_sim_train/bin/python';transfer='/data/shapeforge/runtime/runs/staged_contact_20261123/robot_transfer'
    sdk='/data/shapeforge/runtime/baselines/omi_transfer_20261120_004618/omi_proj/local/vendor/optical_module_pu/source/OpticalModule_PU/Arm_control'
    events=[];children=[];complete=False;error=None
    def event(kind,**values):
        events.append(dict(event=kind,time_ns=time.time_ns(),**values));write_json(run/f'{a.phase}_events.json',events)
        print(kind,json.dumps(values),flush=True)
    def stop(sig,frame):raise KeyboardInterrupt(str(sig))
    for sig in (signal.SIGTERM,signal.SIGINT):signal.signal(sig,stop)
    def common(out,kind,options):
        return [python,'-u',str(ROOT/'scripts/simulation/run_hierarchical_insertion.py'),'--output',str(out),
            '--transfer',transfer,'--max-steps','900','--physics-substeps','5','--ik-backend','tianji','--tianji-sdk',sdk,
            '--socket-range-mm','5','--socket-yaw-deg','0','--initial-pose-reset','--timeout','7200','--',kind,
            '--system1','gt','--points','32','--spacing-mm','.5','--device','cuda',*options]
    def job(name,kind,command,physics=True):return dict(name=name,kind=kind,out=run/name,command=command,physics=physics)
    def run_jobs(jobs):
        write_json(run/(jobs[0]['kind']+'_commands.json'),[{**j,'out':str(j['out'])} for j in jobs])
        for start in range(0,len(jobs),2):
            active=[]
            for j in jobs[start:start+2]:
                event('start',job=j['name']);child=OwnedProcess(j['command'],directory=run,name=j['name'],cwd=ROOT)
                children.append(child);active.append((j,child))
                if j['physics']:
                    deadline=time.monotonic()+300
                    while not (j['out']/'worker.sock').exists():
                        if child.poll() is not None or time.monotonic()>deadline:raise RuntimeError(j['name']+' worker startup failed')
                        time.sleep(.25)
            last=0.;deadline=time.monotonic()+10800
            while any(c.poll() is None for _,c in active):
                if any(c.poll() not in (None,0) for _,c in active):raise RuntimeError('stage child failed')
                if time.monotonic()>deadline:raise TimeoutError('stage budget exceeded')
                if time.monotonic()-last>30:
                    progress={}
                    for j,c in active:
                        try:
                            if j['kind']=='bc':
                                rows=read(j['out']/'bc_history.json');progress[j['name']]=dict(updates=rows[-1]['bc_updates'])
                            elif j['kind']=='rl':
                                lines=(j['out']/'experiment.log').read_text().splitlines();progress[j['name']]=next((l for l in reversed(lines) if l.startswith('S0_PROGRESS')),'starting')
                            elif 'collect' in j['kind']:
                                rows=read(j['out']/'experiment/dataset.json')['episodes'];progress[j['name']]=dict(episodes=len(rows),successes=sum(r['success'] for r in rows))
                            elif j['physics']:
                                d=read(j['out']/'experiment/evaluation.json');progress[j['name']]=dict(cases=len(d['cases']),successes=d['successes'])
                            else:progress[j['name']]='running audit'
                        except (OSError,ValueError,KeyError,IndexError):progress[j['name']]='starting'
                    print('PROGRESS',json.dumps(progress),flush=True);write_json(run/f'{a.phase}_progress.json',dict(time_ns=time.time_ns(),jobs=progress));last=time.monotonic()
                time.sleep(.5)
            for j,c in active:
                assert c.poll()==0
                if j['physics']:assert read(j['out']/'result.json')['complete']
                event('complete',job=j['name'])
    def collect(prefix,plan_prefix):
        jobs=[]
        for i in range(2):
            name=f'{prefix}_{i}';plan=run/f'{plan_prefix}_{i}.json';cases=read(plan)
            command=common(run/name,'collect',['--episode-plan',str(plan),'--episodes',str(len(cases)),'--seed',str(cases[0]['seed'])])
            jobs.append(job(name,prefix,command))
        run_jobs(jobs)
    conditions=[dict(name=f'{mode}_{seed}',mode='path' if mode=='path' else 'goal-only',seed=seed)
                for seed in protocol['model_seeds'] for mode in ['path','goal']]
    def evaluate(prefix,source,plan_file):
        plan=run/plan_file;cases=read(plan);jobs=[]
        for c in conditions:
            name=f'{prefix}_{c["name"]}';model=run/f'{source}_{c["name"]}'
            model=model/'system0.zip' if source=='bc' else model/'experiment/system0.zip'
            command=common(run/name,'evaluate',['--model',str(model),'--reference-input',c['mode'],
                '--episode-plan',str(plan),'--episodes',str(len(cases)),'--seed',str(cases[0]['seed'])])
            jobs.append(job(name,prefix,command))
        run_jobs(jobs)
    try:
        if a.phase=='pilot':
            collect('pilot_collect','pilot');audit_collection(run,'pilot_collect','pilot_all.json')
            event('pilot_passed')
        else:
            assert read(run/'pilot_result.json')['complete'] and read(run/'pilot_collect_audit.json')['successes']==8
            collect('collect','collection');audit_collection(run,'collect','collection_all.json',merge=True);event('dataset_passed')
            jobs=[]
            for c in conditions:
                name=f'bc_{c["name"]}';command=[python,'-u',str(ROOT/'scripts/simulation/reconstruct_hierarchical_bc.py'),
                    '--template-config',str(run/'dataset/config.json'),'--dataset',str(run/'dataset'),'--output',str(run/name),
                    '--seed',str(c['seed']),'--bc-steps',str(protocol['bc']['updates_per_model']),'--bc-checkpoint-steps','5000',
                    '--bc-sampling','phase-balanced','--reference-input',c['mode'],'--reset-distribution',str(run/'reset_distribution.json'),
                    '--initial-policy-std','.02','--max-policy-std','.03','--actor-learning-rate','.00001','--intervention-bc-weight','10',
                    '--entropy-coef','auto_0.001','--target-entropy','-18','--learning-starts','0','--device','cuda']
                jobs.append(job(name,'bc',command,False))
            run_jobs(jobs);pairing=[]
            for seed in protocol['model_seeds']:
                left,right=run/f'bc_path_{seed}',run/f'bc_goal_{seed}'
                assert read(left/'initial_actor.json')['actor_sha256']==read(right/'initial_actor.json')['actor_sha256']
                assert read(left/'bc_sampling_audit.json')['index_sequence_sha256']==read(right/'bc_sampling_audit.json')['index_sequence_sha256']
                pairing.append(dict(seed=seed,initial_actor_equal=True,bc_sample_order_equal=True))
            write_json(run/'pairing_audit.json',pairing)
            evaluate('bcval','bc','validation.json')
            jobs=[]
            for c in conditions:
                name=f'rl_{c["name"]}';command=common(run/name,'train-s0',['--model',str(run/f'bc_{c["name"]}/system0.zip'),
                    '--reference-input',c['mode'],'--reset-distribution',str(run/'reset_distribution.json'),
                    '--intervention','scripted','--intervention-fraction','.5','--intervention-bc-weight','10',
                    '--initial-policy-std','.02','--max-policy-std','.03','--actor-learning-rate','.00001',
                    '--entropy-coef','auto_0.001','--target-entropy','-18','--bc-steps','0','--steps',str(protocol['online']['steps_per_model']),
                    '--learning-starts','0','--batch-size','32','--capacity','20000','--checkpoint-steps','5000','--seed',str(c['seed'])])
                jobs.append(job(name,'rl',command))
            run_jobs(jobs)
            evaluate('bctest','bc','test.json');evaluate('test','rl','test.json')
            jobs=[]
            for c in conditions:
                name=f'audit_{c["name"]}';command=[python,str(ROOT/'scripts/simulation/audit_hierarchical_intervention_run.py'),
                    '--experiment',str(run/f'rl_{c["name"]}/experiment')]
                jobs.append(job(name,'audit',command,False))
            run_jobs(jobs)
            run_jobs([job('summary','summary',[python,str(ROOT/'scripts/simulation/summarize_randomized_retraining.py'),'--run',str(run)],False)])
            event('all_stages_complete')
        complete=True
    except BaseException as exc:error=repr(exc);event('failed',error=error);raise
    finally:
        active=[c for c in children if c.poll() is None]
        for c in active:
            try:os.killpg(c.process.pid,signal.SIGTERM)
            except ProcessLookupError:pass
        deadline=time.monotonic()+90
        while any(c.poll() is None for c in active) and time.monotonic()<deadline:time.sleep(.25)
        for c in active:
            if c.poll() is None:c.stop()
        write_json(run/f'{a.phase}_result.json',dict(complete=complete,error=error,children=[c.record for c in children]))
    if not complete:raise SystemExit(1)


if __name__=='__main__':main()
