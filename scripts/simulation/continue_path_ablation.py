"""Continue the interrupted second paired seed, retaining equal model budgets.

The original run is preserved. Both conditions restart from their 3000-step
checkpoint with a common new episode seed. Only retained transitions are counted.
"""
import json
import os
from pathlib import Path
import signal
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from omi_shapeforge.sim.process_supervisor import OwnedProcess,write_json


def read(p):return json.loads(Path(p).read_text())


def main():
    run=Path(sys.argv[1]).resolve();python='/data/shapeforge/runtime/envs/omi_sim_train/bin/python'
    transfer='/data/shapeforge/runtime/runs/staged_contact_20261123/robot_transfer'
    sdk='/data/shapeforge/runtime/baselines/omi_transfer_20261120_004618/omi_proj/local/vendor/optical_module_pu/source/OpticalModule_PU/Arm_control'
    children=[];failed=False;error=None;routes={};events=[]
    def event(kind,**data):
        events.append(dict(event=kind,time_ns=time.time_ns(),**data));write_json(run/'continuation_events.json',events)
        print(kind,json.dumps(data),flush=True)
    def stop(signum,frame):raise KeyboardInterrupt(str(signum))
    previous={s:signal.signal(s,stop) for s in [signal.SIGINT,signal.SIGTERM]}
    def command(out,kind,options):
        return [python,'-u',str(ROOT/'scripts/simulation/run_hierarchical_insertion.py'),'--output',str(out),'--transfer',transfer,
            '--max-steps','900','--physics-substeps','5','--ik-backend','tianji','--tianji-sdk',sdk,
            '--socket-range-mm','3','--socket-yaw-deg','0','--timeout','7200','--',kind,
            '--system1','gt','--points','32','--spacing-mm','.5','--device','cuda',*options]
    def batch(jobs):
        active=[]
        for name,out,cmd in jobs:
            event('start',job=name,output=str(out))
            child=OwnedProcess(cmd,directory=run,name=name,cwd=ROOT);children.append(child);active.append((name,out,child))
            deadline=time.monotonic()+300
            while not (out/'worker.sock').exists():
                if child.poll() is not None or time.monotonic()>deadline:raise RuntimeError('worker startup failed: '+name)
                time.sleep(.25)
        last=0.
        while any(c.poll() is None for _,_,c in active):
            if any(c.poll() not in (None,0) for _,_,c in active):raise RuntimeError('continuation child failed')
            if time.monotonic()-last>30:
                progress={}
                for name,out,c in active:
                    try:
                        e=out/'experiment/evaluation.json'
                        if e.exists():
                            r=read(e);progress[name]=dict(cases=len(r['cases']),successes=r['successes'])
                        else:
                            lines=(out/'experiment.log').read_text().splitlines()
                            progress[name]=next((s for s in reversed(lines) if s.startswith('S0_PROGRESS')),'starting')
                    except (OSError,ValueError):progress[name]='starting'
                print('PROGRESS',json.dumps(progress),flush=True);last=time.monotonic()
            time.sleep(.5)
        for name,out,c in active:
            if c.poll()!=0 or not read(out/'result.json')['complete']:raise RuntimeError(name+' failed')
            event('complete',job=name)
    try:
        for mode in ['path','goal']:
            first=run/f'rl_{mode}_340000'
            assert read(first/'result.json')['complete']
            routes[f'{mode}_340000']=dict(training_dir=str(first),trace_files=[str(first/'experiment/trace.jsonl')],resumed=False)
        jobs=[]
        for mode in ['path','goal']:
            old=run/f'rl_{mode}_341000';checkpoint=old/'experiment/checkpoints/step_00003000/system0.zip'
            assert read(checkpoint.with_suffix('.json'))['num_timesteps']==3000
            prefix=run/f'{mode}_341000_retained_3000.jsonl';count=0
            with prefix.open('x') as dest:
                for line in (old/'experiment/trace.jsonl').read_text().splitlines():
                    row=json.loads(line);dest.write(line+'\n')
                    if row['event']=='step':count+=1
                    if count==3000:break
            assert count==3000
            out=run/f'rl_{mode}_341000_resume'
            routes[f'{mode}_341000']=dict(training_dir=str(out),trace_files=[str(prefix),str(out/'experiment/trace.jsonl')],
                resumed=True,checkpoint_step=3000,resume_episode_seed=342000,initialization_seed=341000,
                interrupted_directory=str(old),note='checkpoint precedes its next gradient update; resumed models have 11999 online gradient updates')
            opts=['--model',str(checkpoint),'--reference-input','path' if mode=='path' else 'goal-only',
                '--target-schedule',str(run/'train_targets.json'),'--intervention','scripted','--intervention-fraction','.5',
                '--intervention-bc-weight','10','--initial-policy-std','.02','--max-policy-std','.03',
                '--actor-learning-rate','.00001','--entropy-coef','auto_0.001','--target-entropy','-18',
                '--bc-steps','0','--steps','9000','--learning-starts','0','--batch-size','32','--capacity','20000',
                '--checkpoint-steps','3000','--seed','342000']
            jobs.append(('continued_'+mode+'_341000',out,command(out,'train-s0',opts)))
        write_json(run/'routes.json',routes)
        write_json(run/'continuation_protocol.json',dict(reason='original supervisor received SIGTERM; cause unconfirmed',
            retained_training_steps_per_condition=3000,new_steps_per_condition=9000,final_steps_per_model=12000,
            shared_new_episode_seed=342000,old_uncheckpointed_branches_not_counted=True,routes=routes))
        batch(jobs)
        for seed in [340000,341000]:
            jobs=[]
            for mode in ['path','goal']:
                out=run/f'test_{mode}_{seed}'
                model=Path(routes[f'{mode}_{seed}']['training_dir'])/'experiment/system0.zip'
                opts=['--model',str(model),'--reference-input','path' if mode=='path' else 'goal-only',
                      '--episode-plan',str(run/'test.json'),'--episodes','24','--seed','330000']
                jobs.append(('continued_test_'+mode+'_'+str(seed),out,command(out,'evaluate',opts)))
            batch(jobs)
        event('all_remaining_stages_complete')
    except BaseException as exc:failed=True;error=repr(exc);event('failed',error=error);raise
    finally:
        active=[c for c in children if c.poll() is None]
        for c in active:
            try:os.killpg(c.process.pid,signal.SIGTERM)
            except ProcessLookupError:pass
        deadline=time.monotonic()+90
        while any(c.poll() is None for c in active) and time.monotonic()<deadline:time.sleep(.25)
        for c in active:
            if c.poll() is None:c.stop()
        write_json(run/'continuation_result.json',dict(complete=not failed,error=error,children=[c.record for c in children]))
        for s,h in previous.items():signal.signal(s,h)


if __name__=='__main__':main()
