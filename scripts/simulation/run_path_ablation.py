"""Matched GT-waypoint versus goal-only System0 experiment after collection.

Uses two isolated processes at most; paired models share data, budgets, target
order, network size and seeds. All outputs are append-only stage directories.
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
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def merge_collection(run):
    target=run/'dataset'
    if target.exists():raise FileExistsError('dataset already exists; use a fresh study directory')
    target.mkdir();expected={r['seed']:r for r in read(run/'collection_all.json')}
    records=[];schema=config=None
    for shard in range(2):
        source=run/f'collect_{shard}'
        receipt=read(source/'result.json')
        if not receipt['complete']:raise RuntimeError(f'collection {shard} incomplete')
        meta=read(source/'experiment/dataset.json')
        if schema is None:schema=meta['schema'];config=meta['config']
        if meta['schema']!=schema or meta['config']!=config:raise ValueError('collection contracts differ')
        for row in meta['episodes']:
            planned=expected[row['seed']]
            if row['split']!=planned['split'] or row['socket_pose']!=planned['socket_pose'] or not row['success']:
                raise ValueError('missing/failed/wrong collection target')
            file=source/'experiment'/row['file']
            if digest(file)!=row['sha256']:raise ValueError('collection hash mismatch')
            records.append(dict(row,file=os.path.relpath(file,target)))
    if len(records)!=len(expected) or len({r['seed'] for r in records})!=len(expected):raise ValueError('collection coverage mismatch')
    records.sort(key=lambda r:r['seed'])
    write_json(target/'dataset.json',dict(schema=schema,config=config,episodes=records,
        provenance='same recorded expert trajectories for both observation conditions; goal-only masking is on read'))
    write_json(target/'config.json',config)
    write_json(run/'collection_audit.json',dict(episodes=len(records),successes=len(records),
        splits={s:dict(episodes=sum(r['split']==s for r in records),steps=sum(r['steps'] for r in records if r['split']==s)) for s in ['train','val']},
        all_hashes_verified=True,all_planned_targets_present=True))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=Path,required=True);a=p.parse_args();run=a.run.resolve()
    protocol=read(run/'protocol.json');python='/data/shapeforge/runtime/envs/omi_sim_train/bin/python'
    transfer='/data/shapeforge/runtime/runs/staged_contact_20261123/robot_transfer'
    sdk='/data/shapeforge/runtime/baselines/omi_transfer_20261120_004618/omi_proj/local/vendor/optical_module_pu/source/OpticalModule_PU/Arm_control'
    merge_collection(run)
    conditions=[dict(name=f'{mode}_{seed}',mode='path' if mode=='path' else 'goal-only',seed=seed)
                for seed in protocol['model_seeds'] for mode in ['path','goal']]
    children=[];events=[];failed=False;error=None
    def event(kind,**details):
        events.append(dict(event=kind,time_ns=time.time_ns(),**details));write_json(run/'events.json',events)
        print(kind,json.dumps(details),flush=True)
    def stop(signum,frame):raise KeyboardInterrupt(str(signum))
    previous={s:signal.signal(s,stop) for s in [signal.SIGTERM,signal.SIGINT]}
    def common(out,command,options):
        return [python,'-u',str(ROOT/'scripts/simulation/run_hierarchical_insertion.py'),'--output',str(out),'--transfer',transfer,
                '--max-steps','900','--physics-substeps','5','--ik-backend','tianji','--tianji-sdk',sdk,
                '--socket-range-mm','3','--socket-yaw-deg','0','--timeout','7200','--',command,
                '--system1','gt','--points','32','--spacing-mm','.5','--device','cuda',*options]
    def ready(job,child):
        if not job.get('physics'):return
        deadline=time.monotonic()+300
        while not (job['out']/'worker.sock').exists():
            if child.poll() is not None:raise RuntimeError(f"{job['name']} exited before worker ready")
            if time.monotonic()>deadline:raise TimeoutError(job['name'])
            time.sleep(.25)
    def progress(job):
        try:
            if job['kind']=='bc':
                r=read(job['out']/'bc_history.json');return dict(updates=r[-1]['bc_updates'],val_mse=r[-1]['val']['action_mse'])
            if job['kind']=='rl':
                log=(job['out']/'experiment.log').read_text().splitlines()
                return next((s for s in reversed(log) if s.startswith('S0_PROGRESS')),'starting')
            r=read(job['out']/'experiment/evaluation.json');return dict(cases=len(r['cases']),successes=r['successes'])
        except (OSError,ValueError,KeyError):return 'starting'
    def run_jobs(jobs):
        write_json(run/(jobs[0]['kind']+'_commands.json'),[{k:str(v) if isinstance(v,Path) else v for k,v in j.items()} for j in jobs])
        for start in range(0,len(jobs),2):
            active=[]
            for job in jobs[start:start+2]:
                event('start',job=job['name'])
                child=OwnedProcess(job['command'],directory=run,name=job['name'],cwd=ROOT);children.append(child);active.append((job,child));ready(job,child)
            last=0.;deadline=time.monotonic()+10800
            while any(c.poll() is None for _,c in active):
                if any(c.poll() not in (None,0) for _,c in active):raise RuntimeError('stage child failed')
                if time.monotonic()>deadline:raise TimeoutError('stage budget')
                if time.monotonic()-last>30:
                    print('PROGRESS',json.dumps({j['name']:progress(j) for j,c in active}),flush=True);last=time.monotonic()
                time.sleep(.5)
            for job,child in active:
                if child.poll()!=0:raise RuntimeError(job['name']+' failed')
                if job.get('physics') and not read(job['out']/'result.json')['complete']:raise RuntimeError('native phase failed')
                event('complete',job=job['name'])
    def evaluation_jobs(prefix,model_prefix,plan_name):
        rows=read(run/(plan_name+'.json'));jobs=[]
        for c in conditions:
            out=run/(prefix+'_'+c['name']);model=run/(model_prefix+'_'+c['name'])
            model=model/'system0.zip' if model_prefix=='bc' else model/'experiment/system0.zip'
            command=common(out,'evaluate',['--model',str(model),'--reference-input',c['mode'],
                '--episode-plan',str(run/(plan_name+'.json')),'--episodes',str(len(rows)),'--seed',str(rows[0]['seed'])])
            jobs.append(dict(name=prefix+'_'+c['name'],out=out,kind=prefix,physics=True,command=command))
        return jobs
    try:
        jobs=[]
        for c in conditions:
            out=run/('bc_'+c['name'])
            command=[python,'-u',str(ROOT/'scripts/simulation/reconstruct_hierarchical_bc.py'),
                '--template-config',str(run/'dataset/config.json'),'--dataset',str(run/'dataset'),'--output',str(out),
                '--seed',str(c['seed']),'--bc-steps','20000','--bc-checkpoint-steps','5000','--bc-sampling','phase-balanced',
                '--reference-input',c['mode'],'--target-schedule',str(run/'train_targets.json'),
                '--initial-policy-std','.02','--max-policy-std','.03','--actor-learning-rate','.00001',
                '--intervention-bc-weight','10','--entropy-coef','auto_0.001','--target-entropy','-18','--learning-starts','0','--device','cuda']
            jobs.append(dict(name='bc_'+c['name'],out=out,kind='bc',physics=False,command=command))
        run_jobs(jobs)
        fairness=[]
        for seed in protocol['model_seeds']:
            left,right=run/f'bc_path_{seed}',run/f'bc_goal_{seed}'
            init_equal=read(left/'initial_actor.json')['actor_sha256']==read(right/'initial_actor.json')['actor_sha256']
            samples_equal=read(left/'bc_sampling_audit.json')['index_sequence_sha256']==read(right/'bc_sampling_audit.json')['index_sequence_sha256']
            if not init_equal or not samples_equal:raise RuntimeError('paired initialization/sampling mismatch')
            fairness.append(dict(seed=seed,initial_actor_equal=True,bc_sample_order_equal=True))
        write_json(run/'pairing_audit.json',fairness)
        run_jobs(evaluation_jobs('bcval','bc','validation'))
        jobs=[]
        for c in conditions:
            out=run/('rl_'+c['name'])
            command=common(out,'train-s0',['--model',str(run/('bc_'+c['name'])/'system0.zip'),
                '--reference-input',c['mode'],'--target-schedule',str(run/'train_targets.json'),
                '--intervention','scripted','--intervention-fraction','.5','--intervention-bc-weight','10',
                '--initial-policy-std','.02','--max-policy-std','.03','--actor-learning-rate','.00001',
                '--entropy-coef','auto_0.001','--target-entropy','-18','--bc-steps','0','--steps','12000',
                '--learning-starts','0','--batch-size','32','--capacity','20000','--checkpoint-steps','3000','--seed',str(c['seed'])])
            jobs.append(dict(name='rl_'+c['name'],out=out,kind='rl',physics=True,command=command))
        run_jobs(jobs)
        run_jobs(evaluation_jobs('test','rl','test'))
        event('all_stages_complete')
    except BaseException as exc:
        failed=True;error=repr(exc);event('failed',error=error);raise
    finally:
        live=[c for c in children if c.poll() is None]
        for c in live:
            try:os.killpg(c.process.pid,signal.SIGTERM)
            except ProcessLookupError:pass
        deadline=time.monotonic()+90
        while any(c.poll() is None for c in live) and time.monotonic()<deadline:time.sleep(.25)
        for c in live:
            if c.poll() is None:c.stop()
        write_json(run/'pipeline_result.json',dict(complete=not failed,error=error,children=[c.record for c in children]))
        for s,h in previous.items():signal.signal(s,h)


if __name__=='__main__':main()
