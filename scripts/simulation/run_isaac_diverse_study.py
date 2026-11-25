"""Fifty diverse trajectories, BC validation gate, and independent held-out tests."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from omi_shapeforge.sim.process_supervisor import OwnedProcess,write_json


def scenarios(split, start, counts, *, retries=3):
    slots=[];number=0
    for kind,count in counts:
        for j in range(count):
            x=z=0.
            if kind=='alignment':
                magnitude=[.3,.6,.9,.45][j//4] if split=='training' else [.375,.75][j%2]
                sign=1 if (j//2)%2==0 else -1
                if j%2:x=sign*magnitude
                else:z=sign*magnitude
            elif kind=='recovery':x=(1 if j%2==0 else -1)*([.9,.95,1.05,1.1][j//2] if split=='training' else 1.)
            candidates=[dict(id=f'{split}_{kind}_{start+number+a*100000}',seed=start+number+a*100000,
                split=split,kind=kind,x_mm=x,z_mm=z) for a in range(retries)]
            slots.append(dict(candidates=candidates));number+=1
    return slots


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--workers',type=int,default=4)
    p.add_argument('--physics-device',choices=['cpu','gpu'],default='cpu')
    p.add_argument('--ik-backend',choices=['dls','tianji'],default='dls')
    p.add_argument('--tianji-sdk',type=Path)
    p.add_argument('--tianji-config',type=Path)
    p.add_argument('--keep-preview-viewport',action='store_true',help='Use legacy preview rendering for historical execution contracts')
    p.add_argument('--render-subframes',type=int,choices=[1,2],default=2)
    p.add_argument('--async-recording',action='store_true',help='Overlap durable demonstration recording with subsequent control steps')
    p.add_argument('--physics-substeps',type=int,choices=[5,20,100,500],default=20,
                   help='Explicit new-run physics recipe; use 500 to reproduce the original fine-step study')
    a=p.parse_args()
    if a.ik_backend=='tianji' and a.tianji_sdk is None:p.error('--tianji-sdk required for native IK')
    if a.ik_backend=='dls' and (a.tianji_sdk is not None or a.tianji_config is not None):p.error('SDK options require --ik-backend tianji')
    if not 1<=a.workers<=4:p.error('one to four workers supported')
    a.output.mkdir(parents=True,exist_ok=False);out=a.output.resolve();study=out/'study'
    python='/data/omi_runtime/envs/omi_sim_train/bin/python'
    transfer='/data/omi_runtime/runs/staged_contact_20261123/robot_transfer'
    pretrained='/data/omi_runtime/baselines/omi_transfer_20261120_004618/omi_proj/local/pretrained/serl_resnet10/backbone.pt'
    training=scenarios('training',20000,[('normal',16),('alignment',16),('recovery',8)])
    validation=scenarios('validation',40000,[('normal',4),('alignment',4),('recovery',2)])
    testing=scenarios('test',60000,[('normal',4),('alignment',2),('recovery',2)],retries=1)
    write_json(out/'collection_plan.json',dict(slots=training+validation))
    write_json(out/'validation_plan.json',dict(slots=[dict(candidates=[s['candidates'][0]]) for s in validation]))
    write_json(out/'test_plan.json',dict(slots=testing))
    write_json(out/'protocol.json',dict(version='diverse-50-v2-fast',demonstrations=50,training=40,validation=10,
        groups=dict(normal=20,alignment=20,recovery=10),max_attempts_per_slot=3,max_steps=900,
        worker_count=a.workers,physics_substeps=a.physics_substeps,physics_dt=.1/a.physics_substeps,
        physics_device=a.physics_device,
        ik_backend=a.ik_backend,tianji_sdk=str(a.tianji_sdk.resolve()) if a.tianji_sdk else None,
        keep_preview_viewport=a.keep_preview_viewport,
        render_subframes=a.render_subframes,async_recording=a.async_recording,
        tianji_config=str(a.tianji_config.resolve()) if a.tianji_config else None,
        bc_updates=12000,bc_gate=dict(validation_successes=8,recovery_successes=1),
        held_out_tests=8,rl_episodes_if_gate_passes=6,
        scope='scripted setup through normal actions; setup excluded from supervision; fixed task target; one reset per trajectory'))
    snapshot=out/'source_snapshot';snapshot.mkdir();hashes={}
    sources=[Path(__file__),ROOT/'src/omi_shapeforge/sim/process_supervisor.py',ROOT/'src/omi_shapeforge/sim/async_episode_spool.py']
    for package in ['training','hil']:sources+=list((ROOT.parent/'omi_proj/src/omi_hil_rl'/package).glob('*.py'))
    for f in sources:
        relative=str(f.relative_to(ROOT.parent/'omi_proj/src')) if f.is_relative_to(ROOT.parent/'omi_proj/src') else f.name
        target=snapshot/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,target)
        hashes[str(f)]=hashlib.sha256(f.read_bytes()).hexdigest()
    write_json(out/'source_hashes.json',hashes)
    env=dict(os.environ)
    for k in ('CONDA_PREFIX','CONDA_DEFAULT_ENV','PYTHONHOME','PYTHONPATH','LD_LIBRARY_PATH'):env.pop(k,None)
    for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):env[k]='1'
    learn=dict(env,PYTHONPATH=str(ROOT.parent/'omi_proj/src')+':'+str(ROOT/'src'))
    workers={};children=[];events=[];failed=False;rl_run=False
    def event(name,**detail):
        events.append(dict(event=name,time_ns=time.time_ns(),**detail));write_json(out/'events.json',events)
        print(name,json.dumps(detail),flush=True)
    def interrupt(signum,frame):
        event('signal',signum=signum);raise KeyboardInterrupt
    for sig in (signal.SIGTERM,signal.SIGINT):signal.signal(sig,interrupt)
    def spawn(command,name,environment=learn):
        child=OwnedProcess(command,directory=out,name=name,env=environment,cwd=ROOT.parent/'omi_proj');children.append(child);return child
    def stage(name,options):
        event('stage_start',stage=name)
        child=spawn([python,'-u','-m','omi_hil_rl.training.isaac_rule_feedback',*options,'--run',str(study)],name)
        wait_all([child],name)
    def wait_all(group,name,timeout=18000):
        deadline=time.monotonic()+timeout;last=0
        while any(c.poll() is None for c in group):
            if any(c.poll() not in (None,0) for c in group):raise RuntimeError(name+' child failed')
            if time.monotonic()>deadline:raise TimeoutError(name)
            if time.monotonic()-last>30:
                reports=list((study/('demonstrations' if name=='collect' else name)/'cases').glob('*/report.json'))
                successes=sum(json.loads(p.read_text())['success'] for p in reports)
                print('HEARTBEAT',name,'jobs',sum(c.poll() is not None for c in group),'/',len(group),
                      'successful_cases',successes,'attempts',len(reports),flush=True);last=time.monotonic()
            time.sleep(1)
        if any(c.poll()!=0 for c in group):raise RuntimeError(name+' child failed')
        event('stage_complete',stage=name)
    def start_workers(prefix,indices):
        ik_options=['--ik-backend',a.ik_backend,'--physics-device',a.physics_device,'--render-subframes',str(a.render_subframes)]
        if a.tianji_sdk:ik_options+=['--tianji-sdk',str(a.tianji_sdk.resolve())]
        if a.tianji_config:ik_options+=['--tianji-config',str(a.tianji_config.resolve())]
        if a.keep_preview_viewport:ik_options+=['--keep-preview-viewport']
        for i in indices:
            sock=out/f'w{i}.sock'
            w=spawn(['/data/isaac-sim-5.1.0/python.sh','-u',str(ROOT/'scripts/simulation/isaac_rl_worker.py'),
                '--transfer',transfer,'--output',str(out/f'{prefix}_worker{i}'),'--socket',str(sock),
                '--max-steps','900','--physics-substeps',str(a.physics_substeps),
                '--teacher-min-step-mm','.05','--target-overtravel-mm','.1','--entry-guidance',*ik_options],f'{prefix}_worker{i}',env)
            workers[i]=w;deadline=time.monotonic()+180
            while not sock.exists():
                if w.poll() is not None or time.monotonic()>deadline:raise RuntimeError('worker startup failure')
                time.sleep(.5)
            if (study/'contract.json').exists():
                metadata=json.loads((out/f'{prefix}_worker{i}/worker_metadata.json').read_text())
                assert metadata['execution_config']==json.loads((study/'contract.json').read_text())['execution_config']
            event('worker_ready',worker=i,prefix=prefix)
    def stop_workers(prefix,indices=None):
        for i in list(workers) if indices is None else list(indices):
            w=workers.pop(i)
            if w.poll() is None:
                code="from omi_hil_rl.training.isaac_client import IsaacClient;import sys;c=IsaacClient(sys.argv[1]);print(c.request('shutdown')[0]);c.close()"
                q=spawn([python,'-c',code,str(out/f'w{i}.sock')],f'shutdown_{prefix}_{i}')
                if q.wait(45)!=0:raise RuntimeError('shutdown RPC failed')
                if w.wait(60)!=0:raise RuntimeError('worker exit failed')
            else:raise RuntimeError('worker exited before requested shutdown')
    def scenario_stage(name,plan,checkpoint=None):
        output=study/('demonstrations' if checkpoint is None else name)
        group=[]
        for i in range(a.workers):
            cmd=[python,'-u','-m','omi_hil_rl.training.isaac_diverse_demonstrations','--run',str(study),
                '--socket',str(out/f'w{i}.sock'),'--plan',str(out/plan),'--shard',str(i),'--shards',str(a.workers)]
            if checkpoint:cmd+=['--evaluate',str(checkpoint),'--output',str(output)]
            elif a.async_recording:cmd+=['--async-recording']
            group.append(spawn(cmd,f'{name}_{i}'))
        wait_all(group,name)
        shards=[json.loads((output/'shards'/f'{i}.json').read_text()) for i in range(a.workers)]
        contract=json.loads((study/'contract.json').read_text());assert all(s['contract']==contract for s in shards)
        attempts=[r for s in shards for r in s['attempts']];episodes=[r for s in shards for r in s['episodes']]
        if checkpoint:
            report=dict(cases=attempts,successes=sum(c['success'] for c in attempts),total=len(attempts),
                teacher_enabled=False,scripted_setup=True,checkpoint_sha256=hashlib.sha256(checkpoint.read_bytes()).hexdigest())
            write_json(output/'report.json',report)
            if not all(c['initialization_valid'] for c in attempts):raise RuntimeError('evaluation setup failed; do not score as a policy failure')
            return report
        assert len(episodes)==50
        assert {split:sum(e['split']==split for e in episodes) for split in ['training','validation']}==dict(training=40,validation=10)
        assert len({e['episode'] for e in episodes})==50
        write_json(output/'dataset.json',dict(version='shapeforge-scripted-demonstrations-v2',contract=contract,
            episodes=episodes,attempts=attempts,source='privileged scripted expert suffix; setup prefix excluded; no human actions'))
    try:
        start_workers('collection',range(a.workers))
        stage('init',['init','--socket',str(out/'w0.sock'),'--transfer',transfer,'--pretrained',pretrained,'--max-steps','900','--preset','diverse-50'])
        scenario_stage('collect','collection_plan.json')
        stop_workers('collection')
        stage('bc',['bc'])
        start_workers('evaluation',range(a.workers))
        validation_report=scenario_stage('validation_bc','validation_plan.json',study/'bc/actor.pt')
        recovery_successes=sum(c['success'] for c in validation_report['cases'] if c['kind']=='recovery')
        rl_run=validation_report['successes']>=8 and recovery_successes>=1
        write_json(out/'bc_gate.json',dict(passed=rl_run,validation_successes=validation_report['successes'],recovery_successes=recovery_successes,
            decision_before_held_out_evaluation=True,criterion='at least 8/10 validation scenarios and 1/2 recovery scenarios'))
        scenario_stage('evaluation_bc','test_plan.json',study/'bc/actor.pt')
        if rl_run:
            stop_workers('evaluation_idle',range(1,a.workers))
            stage('rl',['rl','--episodes','3']);stage('resume_rl',['rl','--episodes','6','--resume'])
            start_workers('evaluation_rl',range(1,a.workers))
            scenario_stage('evaluation_rl','test_plan.json',study/'rl/actor.pt')
        stop_workers('evaluation_final')
    except BaseException as exc:
        failed=True;event('failure',error=repr(exc))
    finally:
        for sig in (signal.SIGTERM,signal.SIGINT):signal.signal(sig,signal.SIG_DFL)
        # Normal shutdown above records each ACK/exit; failed work is stopped and retained.
        for child in children:child.stop()
        write_json(out/'pipeline_receipts.json',dict(complete=not failed,rl_executed=rl_run and not failed,
            processes={p.name:json.loads(p.read_text()) for p in out.glob('*_process.json')}))
        event('finished',complete=not failed,rl_executed=rl_run and not failed)
    if failed:raise SystemExit(1)


if __name__=='__main__':main()
