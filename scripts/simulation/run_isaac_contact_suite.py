"""Run bounded, isolated Isaac regression cases and preserve every exit status."""
import argparse
import datetime
import json
import os
from pathlib import Path
import signal
import subprocess
import time


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--transfer-root',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--isaac-root',type=Path,default=Path('/data/isaac-sim-5.1.0'))
    p.add_argument('--cases',nargs='+',default=['normal','half_step','locked','x_plus','x_minus','yaw_plus','yaw_minus'])
    p.add_argument('--timeout',type=float,default=600.)
    p.add_argument('--solver',choices=('TGS','PGS'),default='PGS')
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    cases={'normal':[],'half_step':['--dt','.0001'],'locked':['--locked'],
        'x_plus':['--lateral-mm','1'],'x_minus':['--lateral-mm','-1'],
        'yaw_plus':['--yaw-deg','2'],'yaw_minus':['--yaw-deg','-2'],
        'robot_7':['--seed','7'],'robot_19':['--seed','19'],'robot_41':['--seed','41'],
        'robot_video':['--seed','7','--render']}
    if set(a.cases)-cases.keys():p.error('unknown case')
    env=dict(os.environ)
    for key in ['CONDA_PREFIX','CONDA_DEFAULT_ENV','PYTHONHOME','PYTHONPATH','LD_LIBRARY_PATH']:env.pop(key,None)
    rows=[];script=Path(__file__).with_name('run_isaac_contact.py').resolve()
    for name in a.cases:
        transfer=a.transfer_root/('robot_transfer' if name.startswith('robot_') else 'local_transfer')
        out=a.output/name
        command=[str(a.isaac_root/'python.sh'),'-u',str(script),'--isaac-root',str(a.isaac_root),
                 '--transfer',str(transfer),'--output',str(out),'--solver',a.solver,*cases[name]]
        start=time.monotonic();print('START',name,flush=True);timed_out=False;interrupted=False
        with (a.output/f'{name}.log').open('w') as log:
            process=subprocess.Popen(command,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            try:code=process.wait(timeout=a.timeout)
            except (subprocess.TimeoutExpired,KeyboardInterrupt) as exc:
                interrupted=isinstance(exc,KeyboardInterrupt);timed_out=not interrupted
                os.killpg(process.pid,signal.SIGTERM)
                try:code=process.wait(timeout=10)
                except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);code=process.wait()
        result=json.loads((out/'report.json').read_text()) if (out/'report.json').exists() else None
        row=dict(case=name,command=command,returncode=code,timed_out=timed_out,cancelled=interrupted,
            elapsed_seconds=time.monotonic()-start,accepted=bool(code==0 and result and result.get('accepted')),
            report=str(out/'report.json') if result else None)
        rows.append(row);print('FINISH',json.dumps(row),flush=True)
        (a.output/'suite.json').write_text(json.dumps(dict(cases=rows,requested_cases=a.cases,complete=len(rows)==len(a.cases),
            all_passed=len(rows)==len(a.cases) and all(r['accepted'] for r in rows),
            finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()),indent=2)+'\n')
        if interrupted:raise SystemExit(130)
    if not all(r['accepted'] for r in rows):raise SystemExit(1)


if __name__=='__main__':main()
