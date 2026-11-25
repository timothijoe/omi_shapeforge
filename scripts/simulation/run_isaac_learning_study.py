"""Bounded staged-contact BC/RL trial with durable per-process receipts."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from omi_shapeforge.sim.process_supervisor import OwnedProcess, write_json


class Interrupted(BaseException):
    def __init__(self, signum):self.signum = signum


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--transfer', type=Path, required=True)
    parser.add_argument('--pretrained', type=Path, required=True)
    parser.add_argument('--python', type=Path, default=Path('/data/omi_runtime/envs/omi_sim_train/bin/python'))
    parser.add_argument('--isaac-python', type=Path, default=Path('/data/isaac-sim-5.1.0/python.sh'))
    parser.add_argument('--max-steps', type=int, default=900)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    out = args.output.resolve(); study = out / 'study'; sock = out / 'worker.sock'
    stages = [('init', ['init', '--socket', str(sock), '--transfer', str(args.transfer.resolve()),
                       '--pretrained', str(args.pretrained.resolve()), '--max-steps', str(args.max_steps), '--preset', 'staged-retrain']),
              ('collect', ['collect']), ('bc', ['bc']), ('evaluate_bc', ['evaluate', '--kind', 'bc']),
              ('rl', ['rl', '--episodes', '2']), ('resume_rl', ['rl', '--episodes', '3', '--resume']),
              ('evaluate_rl', ['evaluate', '--kind', 'rl'])]
    protocol = dict(version='staged-retraining-pilot-v1', stages=stages,
                    training_targets=2, validation_targets=1, held_out_seeds=[1700,1701],
                    rl_episodes=3, max_steps=args.max_steps, bc_updates=3000,
                    critic_warmup=128, updates_per_episode=256,
                    no_test_based_selection=True, no_human_feedback=True,
                    comparison='BC/RL share evaluation states; RL has additional online data; no equal-data attribution',
                    transfer_sha256=hashlib.sha256((args.transfer/'transfer.json').read_bytes()).hexdigest())
    write_json(out/'protocol.json', protocol)
    snapshot=out/'source_snapshot';snapshot.mkdir()
    sources=[Path(__file__), ROOT/'src/omi_shapeforge/sim/process_supervisor.py']
    learning=ROOT.parent/'omi_proj/src/omi_hil_rl'
    sources += list((learning/'training').glob('*.py')) + list((learning/'hil').glob('*.py'))
    hashes={}
    for path in sources:
        relative = str(path.relative_to(learning)) if path.is_relative_to(learning) else path.name
        target=snapshot/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target)
        hashes[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
    write_json(out/'source_hashes.json', hashes)
    env=dict(os.environ)
    for key in ('CONDA_PREFIX','CONDA_DEFAULT_ENV','PYTHONHOME','PYTHONPATH','LD_LIBRARY_PATH'):env.pop(key,None)
    for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):env[key]='1'
    learn_env=dict(env, PYTHONPATH=str(ROOT.parent/'omi_proj/src')+':'+str(ROOT/'src'))
    events=[];worker=None;active=None;failed=False;interruption=None
    def event(kind, **fields):
        events.append(dict(event=kind,time_ns=time.time_ns(),**fields))
        write_json(out/'events.json', events)
    def stop(signum, frame):
        event('signal_received',signal=signum,pid=os.getpid(),pgid=os.getpgrp())
        raise Interrupted(signum)
    previous={sig:signal.signal(sig,stop) for sig in (signal.SIGTERM,signal.SIGINT)}
    try:
        event('started',pid=os.getpid(),pgid=os.getpgrp())
        worker=OwnedProcess([str(args.isaac_python),'-u',str(ROOT/'scripts/simulation/isaac_rl_worker.py'),
            '--transfer',str(args.transfer.resolve()),'--output',str(out/'worker'),'--socket',str(sock),
            '--max-steps',str(args.max_steps),'--teacher-min-step-mm','.05','--target-overtravel-mm','.1'],
            directory=out,name='worker',env=env,cwd=ROOT)
        deadline=time.monotonic()+180
        while not sock.exists():
            if worker.poll() is not None:raise RuntimeError('worker exited before ready')
            if time.monotonic()>deadline:raise TimeoutError('worker startup')
            time.sleep(.5)
        event('worker_ready')
        for name, options in stages:
            event('stage_start',stage=name)
            active=OwnedProcess([str(args.python),'-u','-m','omi_hil_rl.training.isaac_rule_feedback',
                *options,'--run',str(study)],directory=out,name=name,env=learn_env,cwd=ROOT.parent/'omi_proj')
            code=active.wait(14400)
            event('stage_exit',stage=name,returncode=code)
            active=None
            if code:raise RuntimeError(f'{name} exited {code}; preserve outputs and stop')
    except Interrupted as exc:
        interruption=exc.signum;failed=True
    except BaseException as exc:
        failed=True;event('failure',error=repr(exc))
    finally:
        # A second signal keeps its default meaning; first cancellation attempts
        # bounded orderly cleanup while children have independently owned groups.
        for sig in previous:signal.signal(sig,signal.SIG_DFL)
        if active is not None:active.stop()
        if worker is not None and worker.poll() is None:
            shutdown_code = "from omi_hil_rl.training.isaac_client import IsaacClient; import sys; c=IsaacClient(sys.argv[1]); print(c.request('shutdown')[0],flush=True); c.close()"
            try:
                shutdown=OwnedProcess([str(args.python),'-u','-c',shutdown_code,str(sock)],
                    directory=out,name='shutdown',env=learn_env,cwd=ROOT)
                code=shutdown.wait(45)
                event('shutdown_rpc_exit',returncode=code)
                if code:failed=True
                code=worker.wait(60)
                event('worker_exit',returncode=code)
                if code:failed=True
            except BaseException as exc:
                failed=True;event('shutdown_failure',error=repr(exc));worker.stop()
        elif worker is not None:
            failed=True;event('worker_already_exited',returncode=worker.poll())
        receipts={p.name:json.loads(p.read_text()) for p in out.glob('*_process.json')}
        result=dict(complete=not failed,interrupted_signal=interruption,processes=receipts)
        write_json(out/'pipeline_receipts.json',result)
        event('finished',complete=not failed)
        for sig,handler in previous.items():signal.signal(sig,handler)
        print(json.dumps(dict(complete=not failed,output=str(out),interrupted_signal=interruption)),flush=True)
    if failed:raise SystemExit(128+interruption if interruption else 1)


if __name__=='__main__':main()
