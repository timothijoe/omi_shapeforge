"""Evaluate frozen paired policies on explicit offset/tilted initial poses."""
import json
import os
from pathlib import Path
import signal
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from omi_shapeforge.sim.process_supervisor import OwnedProcess,write_json


def main():
    run=Path(sys.argv[1]).resolve();protocol=json.loads((run/'protocol.json').read_text())
    python='/data/shapeforge/runtime/envs/omi_sim_train/bin/python'
    transfer='/data/shapeforge/runtime/runs/staged_contact_20261123/robot_transfer'
    sdk='/data/shapeforge/runtime/baselines/omi_transfer_20261120_004618/omi_proj/local/vendor/optical_module_pu/source/OpticalModule_PU/Arm_control'
    children=[];complete=False;error=None
    def stop(sig,frame):raise KeyboardInterrupt(str(sig))
    for sig in (signal.SIGTERM,signal.SIGINT):signal.signal(sig,stop)
    try:
        for mode,model in protocol['models'].items():
            out=run/mode
            command=[python,'-u',str(ROOT/'scripts/simulation/run_hierarchical_insertion.py'),
                '--output',str(out),'--transfer',transfer,'--max-steps','900','--physics-substeps','5',
                '--ik-backend','tianji','--tianji-sdk',sdk,'--socket-range-mm','3','--socket-yaw-deg','0',
                '--initial-pose-reset','--timeout','7200','--','evaluate','--system1','gt','--points','32',
                '--spacing-mm','.5','--device','cuda','--model',model,'--reference-input','path' if mode=='path' else 'goal-only',
                '--episode-plan',str(run/'cases.json'),'--episodes',str(len(protocol['cases'])),'--seed',str(protocol['cases'][0]['seed'])]
            child=OwnedProcess(command,directory=run,name=mode,cwd=ROOT);children.append((mode,out,child))
            print('START',mode,flush=True);deadline=time.monotonic()+300
            while not (out/'worker.sock').exists():
                if child.poll() is not None or time.monotonic()>deadline:raise RuntimeError(mode+' startup failed')
                time.sleep(.25)
        last=0.
        while any(c.poll() is None for _,_,c in children):
            if any(c.poll() not in (None,0) for _,_,c in children):raise RuntimeError('evaluation child failed')
            if time.monotonic()-last>30:
                progress={}
                for mode,out,c in children:
                    path=out/'experiment/evaluation.json'
                    if path.exists():
                        data=json.loads(path.read_text());progress[mode]={'cases':len(data['cases']),'successes':data['successes']}
                print('PROGRESS',json.dumps(progress),flush=True);last=time.monotonic()
            time.sleep(.5)
        for mode,out,c in children:
            assert c.poll()==0 and json.loads((out/'result.json').read_text())['complete']
        complete=True
    except BaseException as exc:error=repr(exc);raise
    finally:
        active=[c for _,_,c in children if c.poll() is None]
        for c in active:
            try:os.killpg(c.process.pid,signal.SIGTERM)
            except ProcessLookupError:pass
        deadline=time.monotonic()+90
        while any(c.poll() is None for c in active) and time.monotonic()<deadline:time.sleep(.25)
        for c in active:
            if c.poll() is None:c.stop()
        write_json(run/'result.json',dict(complete=complete,error=error,children=[c.record for _,_,c in children]))


if __name__=='__main__':main()
