"""Launch an isolated System1/System0 experiment with opt-in Isaac observations."""
import argparse
import json
import os
from pathlib import Path
import signal
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from omi_shapeforge.sim.process_supervisor import OwnedProcess, write_json


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--transfer',type=Path,required=True)
    p.add_argument('--python',type=Path,default=Path('/data/shapeforge/runtime/envs/omi_sim_train/bin/python'))
    p.add_argument('--isaac-python',type=Path,default=Path('/data/isaac-sim-5.1.0/python.sh'))
    p.add_argument('--max-steps',type=int,default=900)
    p.add_argument('--physics-substeps',type=int,choices=[5,20,100,500],default=20)
    p.add_argument('--ik-backend',choices=['dls','tianji'],default='dls')
    p.add_argument('--tianji-sdk',type=Path)
    p.add_argument('--socket-range-mm',type=float,default=0.)
    p.add_argument('--socket-yaw-deg',type=float,default=0.)
    p.add_argument('--initial-pose-reset',action='store_true',help='Enable explicit evaluation start-pose overrides')
    p.add_argument('--wrist-offset-m',type=float,nargs=3,default=[0.,0.,0.])
    p.add_argument('--disable-wrist-wrench',action='store_true',help='Legacy-worker comparison; pair with --contact none')
    p.add_argument('--timeout',type=float,default=7200.)
    p.add_argument('experiment',nargs=argparse.REMAINDER)
    a=p.parse_args()
    experiment=a.experiment[1:] if a.experiment[:1]==['--'] else a.experiment
    if not experiment or experiment[0] not in ('collect','train-s0','evaluate','evaluate-rule'):p.error('after -- specify collect, train-s0, evaluate or evaluate-rule and its options')
    if any(x.split('=')[0] in ('--output','--socket','--transfer') for x in experiment):p.error('launcher owns output, socket and transfer')
    if a.max_steps<1 or a.timeout<=0:p.error('positive horizons required')
    if a.ik_backend=='tianji' and not a.tianji_sdk:p.error('native IK requires SDK path')
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    sock=out/'worker.sock'
    if len(str(sock).encode())>=104:p.error('output path too long for Unix socket')
    worker_env=dict(os.environ)
    for k in ('CONDA_PREFIX','CONDA_DEFAULT_ENV','PYTHONHOME','PYTHONPATH','LD_LIBRARY_PATH'):worker_env.pop(k,None)
    for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):worker_env[k]='1'
    learner_env=dict(worker_env,PYTHONPATH=str(ROOT.parent/'omi_proj/src')+':'+str(ROOT/'src'))
    command=[str(a.isaac_python),'-u',str(ROOT/'scripts/simulation/isaac_rl_worker.py'),'--transfer',str(a.transfer.resolve()),
        '--output',str(out/'worker'),'--socket',str(sock),'--max-steps',str(a.max_steps),
        '--physics-substeps',str(a.physics_substeps),'--ik-backend',a.ik_backend,
        '--teacher-min-step-mm','.05','--target-overtravel-mm','.1','--entry-guidance',
        '--socket-pose-range-mm',str(a.socket_range_mm),'--socket-yaw-range-deg',str(a.socket_yaw_deg)]
    if a.tianji_sdk:command+=['--tianji-sdk',str(a.tianji_sdk.resolve())]
    if a.initial_pose_reset:command+=['--initial-pose-reset']
    if not a.disable_wrist_wrench:command+=['--wrist-wrench','--wrist-offset-m',*[str(x) for x in a.wrist_offset_m]]
    # Preserve the exact new sources along with the worker's own source snapshot.
    import shutil,hashlib
    snapshot=out/'hierarchical_sources';snapshot.mkdir()
    source=ROOT.parent/'omi_proj/src/omi_hil_rl/training/hierarchical_insertion'
    files=[Path(__file__),*source.glob('*.py'),
           *[source.parent/n for n in ('isaac_intervention.py','executed_action_sac.py','hil_replay.py')]]
    for f in files:shutil.copy2(f,snapshot/f.name)
    write_json(out/'source_hashes.json',{str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in files})
    worker=learner=None;failed=False;error=None
    def interrupt(signum,frame):raise KeyboardInterrupt(f'signal {signum}')
    previous={s:signal.signal(s,interrupt) for s in (signal.SIGINT,signal.SIGTERM)}
    try:
        worker=OwnedProcess(command,directory=out,name='worker',env=worker_env,cwd=ROOT)
        deadline=time.monotonic()+240
        while not sock.exists():
            if worker.poll() is not None:raise RuntimeError('worker exited before ready')
            if time.monotonic()>deadline:raise TimeoutError('worker startup')
            time.sleep(.2)
        learner=OwnedProcess([str(a.python),'-u','-m','omi_hil_rl.training.hierarchical_insertion.cli',*experiment,
            '--output',str(out/'experiment'),'--socket',str(sock),'--transfer',str(a.transfer.resolve())],
            directory=out,name='experiment',env=learner_env,cwd=ROOT.parent/'omi_proj')
        deadline=time.monotonic()+a.timeout
        while learner.poll() is None:
            if time.monotonic()>deadline:raise TimeoutError('experiment budget')
            time.sleep(.2)
        if learner.poll()!=0:raise RuntimeError('experiment failed; inspect experiment.log')
    except BaseException as exc:
        failed=True;error=repr(exc)
    finally:
        if learner and learner.poll() is None:learner.stop()
        if worker and worker.poll() is None:
            code="from omi_hil_rl.training.isaac_client import IsaacClient; import sys; c=IsaacClient(sys.argv[1]); c.request('shutdown'); c.close()"
            shutdown=OwnedProcess([str(a.python),'-c',code,str(sock)],directory=out,name='shutdown',env=learner_env,cwd=ROOT)
            try:
                if shutdown.wait(30)!=0:failed=True
                if worker.wait(45)!=0:failed=True
            except BaseException as exc:
                failed=True;error=error or repr(exc);shutdown.stop();worker.stop()
        elif worker:failed=True
        for s,h in previous.items():signal.signal(s,h)
        write_json(out/'result.json',dict(complete=not failed,error=error,
            processes={f.name:json.loads(f.read_text()) for f in out.glob('*_process.json')},
            scope='isolated simulation experiment; see evaluation for policy results'))
    print(json.dumps(dict(complete=not failed,output=str(out),error=error)),flush=True)
    if failed:raise SystemExit(1)


if __name__=='__main__':main()
