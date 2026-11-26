"""Restart handoff: check saved models by default; evaluate ONLY with explicit flag.

This entry point never collects demonstrations or trains. It understands the
documented paired continuation and does not invoke the old all-stage supervisor.
"""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import signal
import subprocess
import time


def read(path):return json.loads(Path(path).read_text())
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def preflight(run):
    bundle=read(run/'reboot_handoff/training_complete.json')
    assert bundle['training_complete']
    for filename,record in bundle['files'].items():
        p=Path(filename);assert p.is_file() and p.stat().st_size==record['bytes'] and sha(p)==record['sha256'],filename
    for name,digest in read(run/'input_hashes.json').items():assert sha(run/name)==digest,name
    frozen=read(run/'reboot_handoff/resume_source_freeze.json')
    for name,digest in frozen['files_sha256'].items():assert sha(Path(frozen['root'])/name)==digest,name
    versions=read(run/'environment_versions.json')
    for package,version in versions['packages'].items():
        assert importlib.metadata.version(package)==version,f'{package} version mismatch; use the recorded training environment'
    return bundle


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=Path,required=True)
    p.add_argument('--start-evaluation',action='store_true',help='Explicitly start the deferred heldout tests; default is file/environment checks only')
    p.add_argument('--output-root',type=Path,help='Use a new short directory if a previous test attempt is partial')
    a=p.parse_args();run=a.run.resolve();bundle=preflight(run)
    print(json.dumps(dict(preflight='passed',models=len(bundle['models']),evaluation_started=False)),flush=True)
    if not a.start_evaluation:return
    output=(a.output_root or run/'deferred_eval').resolve();output.mkdir(parents=True,exist_ok=True)
    code=Path(bundle['resume_code_root']);python='/data/shapeforge/runtime/envs/omi_sim_train/bin/python'
    launcher=code/'omi_shapeforge/scripts/simulation/run_hierarchical_insertion.py'
    sdk='/data/shapeforge/runtime/baselines/omi_transfer_20261120_004618/omi_proj/local/vendor/optical_module_pu/source/OpticalModule_PU/Arm_control'
    cases=read(run/'test.json');jobs=[];children=[];events=[];complete=False;error=None
    def check_result(job):
        folder=job['output'];receipt=read(folder/'result.json');evaluation=read(folder/'experiment/evaluation.json')
        assert receipt['complete'] and all(v['returncode']==0 for v in receipt['processes'].values())
        assert evaluation['source_model_sha256']==job['model_sha256'] and len(evaluation['cases'])==len(cases)
        for actual,wanted in zip(evaluation['cases'],cases):
            assert actual['seed']==wanted['seed'] and actual['socket_pose']==wanted['socket_pose']
            assert actual['initial_pose']['request']==wanted['initial_pose'] and actual['teacher_requests']==0
        return evaluation
    for stage in ['bc','rl']:
        for record in bundle['models']:
            folder=output/f"{stage}_{record['mode']}_{record['initialization_seed']}"
            if len(str(folder/'worker.sock').encode())>=104:raise ValueError('evaluation output path too long for Unix socket')
            model=Path(record[stage+'_model']);job=dict(stage=stage,mode=record['mode'],seed=record['initialization_seed'],output=folder,
                model=str(model),model_sha256=sha(model))
            if folder.exists():
                try:check_result(job);job['already_complete']=True
                except (OSError,ValueError,AssertionError):raise RuntimeError('Preserve partial output and choose a new --output-root: '+str(folder))
            jobs.append(job)
    (output/'launch.json').write_text(json.dumps(dict(explicit_start_flag=True,time_ns=time.time_ns(),pid=os.getpid(),pgid=os.getpgrp(),
        boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),jobs=[{**j,'output':str(j['output'])} for j in jobs]),indent=2))
    def stop(sig,frame):raise KeyboardInterrupt(str(sig))
    for sig in (signal.SIGTERM,signal.SIGINT):signal.signal(sig,stop)
    try:
        pending=[j for j in jobs if not j.get('already_complete')]
        for i in range(0,len(pending),2):
            active=[]
            for j in pending[i:i+2]:
                cmd=[python,'-u',str(launcher),'--output',str(j['output']),'--transfer',bundle['transfer'],'--max-steps','900',
                    '--physics-substeps','5','--ik-backend','tianji','--tianji-sdk',sdk,'--socket-range-mm','5','--socket-yaw-deg','0',
                    '--initial-pose-reset','--timeout','7200','--','evaluate','--system1','gt','--points','32','--spacing-mm','.5',
                    '--device','cuda','--model',j['model'],'--reference-input','path' if j['mode']=='path' else 'goal-only',
                    '--episode-plan',str(run/'test.json'),'--episodes',str(len(cases)),'--seed',str(cases[0]['seed'])]
                with (output/(j['output'].name+'.log')).open('w') as log:
                    child=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                children.append(child);active.append((j,child));events.append(dict(event='start',job=j['output'].name,pid=child.pid,time_ns=time.time_ns()))
                (output/'events.json').write_text(json.dumps(events,indent=2));deadline=time.monotonic()+300
                while not (j['output']/'worker.sock').exists():
                    if child.poll() is not None or time.monotonic()>deadline:raise RuntimeError('evaluation worker startup failed')
                    time.sleep(.25)
            last=0.
            while any(c.poll() is None for _,c in active):
                if any(c.poll() not in (None,0) for _,c in active):raise RuntimeError('evaluation child failed')
                if time.monotonic()-last>30:
                    progress={}
                    for j,c in active:
                        try:
                            e=read(j['output']/'experiment/evaluation.json');progress[j['output'].name]=dict(cases=len(e['cases']),successes=e['successes'])
                        except (OSError,ValueError):progress[j['output'].name]='starting'
                    print('PROGRESS',json.dumps(progress),flush=True);last=time.monotonic()
                time.sleep(.5)
            for j,c in active:
                assert c.returncode==0;check_result(j);events.append(dict(event='complete',job=j['output'].name,time_ns=time.time_ns()))
            (output/'events.json').write_text(json.dumps(events,indent=2))
        results=[]
        for j in jobs:
            e=check_result(j);results.append(dict(stage=j['stage'],mode=j['mode'],initialization_seed=j['seed'],
                successes=e['successes'],cases=len(e['cases']),details=e['cases'],model_sha256=j['model_sha256'],output=str(j['output'])))
        report=dict(complete=True,results=results,training_handoff=str(run/'reboot_handoff/training_complete.json'),
            scope='deferred policy-only heldout tests; no training or teacher; training source recovery fix documented in handoff')
        (output/'summary.json').write_text(json.dumps(report,indent=2)+'\n');complete=True
        print(json.dumps([{k:v for k,v in r.items() if k!='details'} for r in results],indent=2),flush=True)
    except BaseException as exc:error=repr(exc);raise
    finally:
        live=[c for c in children if c.poll() is None]
        for c in live:
            try:os.killpg(c.pid,signal.SIGTERM)
            except ProcessLookupError:pass
        for c in live:
            try:c.wait(timeout=120)
            except subprocess.TimeoutExpired:os.killpg(c.pid,signal.SIGKILL);c.wait()
        (output/'evaluation_result.json').write_text(json.dumps(dict(complete=complete,error=error),indent=2)+'\n')


if __name__=='__main__':main()
