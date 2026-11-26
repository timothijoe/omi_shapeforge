"""Physically prepare distant, misaligned starts and probe frozen System1.

Preparation is ordinary IK/PhysX control. Predictions are recorded, not executed.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'src'), str(ROOT.parent/'omi_proj/src')]
from omi_shapeforge.sim.process_supervisor import OwnedProcess, write_json

CASES = [dict(distance_mm=40., lateral_mm=-15., vertical_mm=10., rotation_deg=[6.,0.,-9.]),
         dict(distance_mm=65., lateral_mm=20., vertical_mm=15., rotation_deg=[-8.,0.,12.]),
         dict(distance_mm=90., lateral_mm=-25., vertical_mm=-12., rotation_deg=[9.,0.,-15.])]


def probe(a):
    import numpy as np
    import torch
    from omi_hil_rl.training.isaac_client import IsaacClient
    from omi_hil_rl.training.hierarchical_insertion.reference import pose, tcp_pose, socket_pose, log_rotation, exp_rotation
    from omi_hil_rl.training.hierarchical_insertion.system1 import VisualPredictor, image_input
    from render_system1_paths import references
    torch.set_num_threads(2)
    packet=json.loads((a.transfer/'transfer.json').read_text());m=packet['manifest']
    digest=hashlib.sha256((a.transfer/'transfer.json').read_bytes()).hexdigest()
    predictor=VisualPredictor(a.checkpoint,digest)
    c=IsaacClient(a.output/'worker.sock',digest)
    tip=(pose(m['tool_to_module']['position_m'],m['tool_to_module']['rotation']) @ np.array([0,m['leading_tip_y_mm']/1000,0,1]))[:3]
    baseR=np.array(m['goal_tcp_rotation'])
    scale=np.array([.001/np.sqrt(3)]*3+[np.pi/180/np.sqrt(3)]*3)
    images=[];predictions=[];truths=[];paths=[];records=[]
    try:
        cases=json.loads(a.cases_json.read_text()) if a.cases_json else CASES
        write_json(a.output/'requested_cases.json',cases)
        for idx,spec in enumerate(cases):
            seed=a.seed_start+idx
            assert seed not in predictor.used_seeds
            obs,info=c.reset(seed);socket=socket_pose(info,m);R=socket[:3,:3]
            cx,cz=m['nominal_module_center_xz_mm'];mouth=m['mouth_y_mm']
            wanted_tip=socket@np.array([(cx+spec['lateral_mm'])/1000,(mouth+spec['distance_mm'])/1000,(cz+spec['vertical_mm'])/1000,1])
            goalR=R@exp_rotation(np.deg2rad(spec['rotation_deg']))@R.T@baseR
            target=wanted_tip[:3]-goalR@tip
            retract_tip=socket@np.array([cx/1000,(mouth+spec['distance_mm']+30)/1000,cz/1000,1])
            retract=retract_tip[:3]-baseR@tip
            trace=[];previous=np.zeros(6)
            for phase,pos,rot in [('retract',retract,baseR),('offset_and_turn',target,goalR)]:
                reached=False
                for step in range(900):
                    cur=tcp_pose(info)
                    err=np.r_[pos-cur[:3,3],log_rotation(rot@cur[:3,:3].T)]
                    if np.linalg.norm(err[:3])<.00008 and np.linalg.norm(err[3:])<.0007:
                        reached=True;break
                    desired=np.clip(err/scale,-.85,.85)
                    action=(previous+np.clip(desired-previous,-.15,.15)).astype(np.float32);previous=action
                    obs,_,term,trunc,info=c.step(action)
                    trace.append(dict(phase=phase,action=action.tolist(),tcp_position=info['tcp_position'],tcp_rotation=info['tcp_rotation'],depth_mm=info['insertion_depth_mm']))
                    if step%100==0:print('PREPARE',idx,phase,step,float(np.linalg.norm(err[:3])*1000),flush=True)
                    if term or trunc:break
                if not reached:
                    write_json(a.output/f'failed_{idx:02d}.json',dict(spec=spec,info=info,trace=trace))
                    raise RuntimeError(f'preparation failed at {idx} {phase}: {info.get("failure")}')
            for _ in range(4):
                obs,_,term,trunc,info=c.step(np.zeros(6,np.float32))
                if term or trunc:raise RuntimeError('terminated during hold')
            current=tcp_pose(info);gt=np.linalg.inv(current)@socket_pose(info,m)
            pred=np.linalg.inv(current)@predictor(obs,current)
            pp,_=references(m,pred,np.r_[tip,1]);gp,_=references(m,gt,np.r_[tip,1])
            e=float(np.linalg.norm(pred[:3,3]-gt[:3,3])*1000)
            angle=float(np.rad2deg(np.linalg.norm(log_rotation(gt[:3,:3].T@pred[:3,:3]))))
            actual_tip=np.linalg.inv(socket)@current@np.r_[tip,1]
            item=dict(id=idx,seed=seed,name=spec.get('name',f'case_{idx:02d}'),requested_lateral_mm=spec['lateral_mm'],requested_vertical_mm=spec['vertical_mm'],
                      requested_distance_mm=spec['distance_mm'],requested_rotation_vector_deg=spec['rotation_deg'],
                      target_tcp_m=target.tolist(),actual_tcp_m=current[:3,3].tolist(),actual_tcp_rotation=current[:3,:3].tolist(),
                      setup_position_error_mm=float(np.linalg.norm(current[:3,3]-target)*1000),
                      setup_rotation_error_deg=float(np.rad2deg(np.linalg.norm(log_rotation(goalR@current[:3,:3].T)))),
                      actual_tip_socket_mm=(actual_tip[:3]*1000).tolist(),actual_depth_mm=info['insertion_depth_mm'],
                      actual_angular_offset_deg=float(np.rad2deg(np.linalg.norm(log_rotation(baseR.T@current[:3,:3])))),
                      translation_error_mm=e,rotation_error_deg=angle,
                      preview_tip_error_mm=float(np.linalg.norm(pp-gp,axis=1).mean()*1000),
                      teacher_requests=info.get('teacher_requests',0),prediction_executed=False,preparation_steps=len(trace))
            records.append(item);images.append(image_input(obs));predictions.append(pred);truths.append(gt);paths.append(pp)
            write_json(a.output/f'case_{idx:02d}.json',dict(summary=item,setup_trace=trace,held_info=info))
            np.savez_compressed(a.output/'samples.npz',images=np.stack(images),predicted_socket=np.stack(predictions),target_socket=np.stack(truths),predicted_tip_path=np.stack(paths))
            write_json(a.output/'report.json',dict(cases=records,checkpoint=str(a.checkpoint),checkpoint_sha256=predictor.checkpoint_sha256,
                       mean_translation_error_mm=float(np.mean([r['translation_error_mm'] for r in records])),
                       max_translation_error_mm=max(r['translation_error_mm'] for r in records),scope='distant misaligned frozen-model probes; predictions not executed'))
            print('CASE',json.dumps(item),flush=True)
    finally:c.close()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['output','checkpoint','transfer','tianji-sdk']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--cases-json',type=Path,help='Explicit list of start poses; original defaults preserved')
    p.add_argument('--seed-start',type=int,default=140000)
    a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=False)
    sock=a.output/'worker.sock'
    if len(str(sock))>=104:raise ValueError('socket path too long')
    env=dict(os.environ)
    for k in ['CONDA_PREFIX','CONDA_DEFAULT_ENV','PYTHONHOME','PYTHONPATH','LD_LIBRARY_PATH']:env.pop(k,None)
    for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:env[k]='1'
    worker=None;failed=False;error=None;previous={}
    def stop(signum,frame):raise KeyboardInterrupt(str(signum))
    for sig in [signal.SIGINT,signal.SIGTERM]:previous[sig]=signal.signal(sig,stop)
    try:
        worker=OwnedProcess(['/data/isaac-sim-5.1.0/python.sh','-u',str(ROOT/'scripts/simulation/isaac_rl_worker.py'),
            '--transfer',str(a.transfer.resolve()),'--output',str(a.output/'worker'),'--socket',str(sock),
            '--max-steps','1900','--physics-substeps','5','--ik-backend','tianji','--tianji-sdk',str(a.tianji_sdk.resolve()),
            '--teacher-min-step-mm','.05','--target-overtravel-mm','.1'],directory=a.output,name='worker',env=env,cwd=ROOT)
        deadline=time.monotonic()+240
        while not sock.exists():
            if worker.poll() is not None:raise RuntimeError('worker exited')
            if time.monotonic()>deadline:raise TimeoutError('worker startup')
            time.sleep(.2)
        probe(a)
    except BaseException as exc:failed=True;error=repr(exc);raise
    finally:
        if worker and worker.poll() is None:
            try:
                from omi_hil_rl.training.isaac_client import IsaacClient
                c=IsaacClient(sock);c.request('shutdown');c.close();code=worker.wait(45)
                if code:failed=True
            except BaseException:failed=True;worker.stop()
        write_json(a.output/'result.json',dict(complete=not failed,error=error,worker=worker.record if worker else None))
        for sig,handler in previous.items():signal.signal(sig,handler)


if __name__=='__main__':main()
