"""Exercise new hierarchical ownership/history/replay around real contact recovery.

The proposer is a diagnostic controller, never a learned policy. A documented
gate bypass injects obstruction through ordinary actions before enabling the
same training Gate. No reset or teleport occurs during recovery.
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
sys.path[:0]=[str(ROOT/'src'),str(ROOT.parent/'omi_proj/src')]
from omi_shapeforge.sim.process_supervisor import OwnedProcess,write_json


def probe(a):
    import numpy as np
    from omi_hil_rl.training.isaac_client import IsaacClient
    from omi_hil_rl.training.isaac_intervention import Gate
    from omi_hil_rl.training.hierarchical_insertion.environment import HierarchicalEnv
    from omi_hil_rl.training.hierarchical_insertion.reference import ReferenceConfig
    from omi_hil_rl.training.hierarchical_insertion.intervention import ScriptedReplayBuffer
    from omi_shapeforge.sim.isaac_contact_approach import limit_approach
    m=json.loads((a.transfer/'transfer.json').read_text())['manifest']
    client=IsaacClient(a.output/'worker.sock')
    env=HierarchicalEnv(client,a.transfer,ReferenceConfig(points=32),contact='wrist-wrench',
                        intervention='scripted',trace=a.output/'hierarchy_trace.jsonl')
    replay=ScriptedReplayBuffer(2500,env.observation_space,env.action_space,device='cpu')
    axis=-np.array(m['socket_to_world']['rotation'])[:,1];side=np.array(m['socket_to_world']['rotation'])[:,0]
    outside=np.array(m['preinsert_tcp_position']);rotation=np.array(m['goal_tcp_rotation'])
    scale=np.array([.001/np.sqrt(3)]*3+[np.pi/180/np.sqrt(3)]*3)
    reports=[]
    class DiagnosticGate:
        enabled=False
        def __init__(self):self.real=Gate()
        def choose(self,worker,info,proposal):
            if not self.enabled:
                return proposal,'policy',dict(reasons=['diagnostic_obstruction_setup'],teacher=None,
                                              proposal_source='synthetic_probe_not_learned_policy')
            action,source,audit=self.real.choose(worker,info,proposal)
            audit['proposal_source']='synthetic_probe_not_learned_policy'
            return action,source,audit
    try:
        for i,offset in enumerate([1.,-1.]):
            obs,info=env.reset(seed=180000+i);gate=DiagnosticGate();env.gate=gate
            task_goal=np.array(info['task_goal_position']);previous=np.zeros(6);phase='offset_outside'
            rows=[];stages=set();blocked=None;handback=False
            for step in range(1000):
                if phase=='offset_outside':target=outside+side*offset/1000
                elif phase=='approach_offset':target=outside+axis*.004+side*offset/1000
                elif phase in ('push_offset','blocked_without_teacher'):
                    target=np.array(m['seated_tcp_position'])-axis*((m['shoulder_depth_mm']-3.)/1000)+side*offset/1000
                else:target=task_goal
                R=np.array(info['tcp_rotation'])
                error=np.r_[target-info['tcp_position'],.5*sum(np.cross(R[:,j],rotation[:,j]) for j in range(3))]
                desired=np.clip(error/scale,-.85,.85);proposal=previous+np.clip(desired-previous,-.3,.3)
                if phase=='push_offset':proposal=np.clip(proposal,-.05,.05)
                if phase=='blocked_without_teacher':proposal=np.zeros(6)
                if phase=='recover':
                    proposal,_=limit_approach(proposal,scale,axis,m['shoulder_depth_mm']-info['insertion_depth_mm'],'insert',minimum_mm=.05)
                before=obs;obs,reward,term,trunc,info=env.step(proposal.astype(np.float32))
                action=np.array(info['executed_action'],np.float32);previous=action
                np.testing.assert_array_equal(obs['history'].reshape(4,19)[-1,6:12],action)
                np.testing.assert_array_equal(info['task_goal_position'],task_goal)
                if gate.enabled:
                    replay.add({k:v[None] for k,v in before.items()},{k:v[None] for k,v in obs.items()},
                               action[None],np.array([reward]),np.array([term or trunc]),[dict(info,**{'TimeLimit.truncated':trunc and not term})])
                    if info['action_source']=='policy' and info.get('recovery_completed',0):handback=True
                rows.append(dict(step=step+1,phase=phase,source=info['action_source'],ownership_event=info.get('ownership_event'),
                    recovery_stage=info.get('recovery_stage'),depth_mm=info['insertion_depth_mm'],
                    proposed_action=proposal.tolist(),executed_action=action.tolist(),reward=reward,teacher_requests=info.get('teacher_requests',0)))
                stage=info.get('recovery_stage')
                if stage not in stages:
                    stages.add(stage);print('RECOVERY',i,stage,step+1,flush=True)
                if term or trunc:break
                if phase in ('offset_outside','approach_offset') and np.linalg.norm(target-info['tcp_position'])<.00008:
                    phase='approach_offset' if phase=='offset_outside' else 'push_offset';previous=np.zeros(6)
                elif phase=='push_offset' and info.get('recovery_required'):
                    blocked=step+1
                    assert info.get('teacher_requests',0)==0 and not info.get('recovery_active')
                    if a.recovery_delay_steps:
                        phase='blocked_without_teacher'
                    else:
                        gate.enabled=True;phase='recover';previous=np.zeros(6)
                elif phase=='blocked_without_teacher' and step+1>=blocked+a.recovery_delay_steps:
                    assert info.get('teacher_requests',0)==0 and not info.get('recovery_active')
                    gate.enabled=True;phase='recover';previous=np.zeros(6)
            passed=bool(info['is_success'] and handback and stages>={'retreat','align_outside','reinsert'})
            row=dict(id=i,offset_mm=offset,passed=passed,steps=len(rows),success=info['is_success'],failure=info.get('failure'),
                     blocked_step=blocked,handback=handback,stages=sorted(stages),
                     recovery_completed=info.get('recovery_completed',0),intervention_stats=info['intervention_stats'],
                     teacher_requests=info.get('teacher_requests',0),proposal_source='synthetic_probe_not_learned_policy')
            reports.append(row);write_json(a.output/f'case_{i:02d}.json',dict(summary=row,trace=rows))
            write_json(a.output/'report.json',dict(cases=reports,all_passed=all(r['passed'] for r in reports),replay=replay.counts(),
                recovery_delay_steps=a.recovery_delay_steps,
                scope='actual hierarchical recovery interface test using synthetic proposals; not training or learned-policy evaluation'))
            print('RESULT',json.dumps(row),flush=True)
        np.savez_compressed(a.output/'replay_audit.npz',actions=replay.actions[:replay.size()],
            proposed_actions=replay.proposed_actions[:replay.size()],scripted=replay.scripted[:replay.size()],
            rewards=replay.rewards[:replay.size()],dones=replay.dones[:replay.size()],
            episode_seeds=replay.episode_seeds[:replay.size()],episode_steps=replay.episode_steps[:replay.size()])
        if not all(r['passed'] for r in reports):raise RuntimeError('one or more recovery probe cases failed')
    finally:env.close()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['output','transfer','tianji-sdk']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--recovery-delay-steps',type=int,default=0,help='Diagnostic only; actual training responds at the next step')
    a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=False)
    worker=None;failed=False;error=None;env=dict(os.environ)
    for k in ['CONDA_PREFIX','CONDA_DEFAULT_ENV','PYTHONHOME','PYTHONPATH','LD_LIBRARY_PATH']:env.pop(k,None)
    for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:env[k]='1'
    def stop(signum,frame):raise KeyboardInterrupt(str(signum))
    previous={s:signal.signal(s,stop) for s in [signal.SIGINT,signal.SIGTERM]}
    try:
        worker=OwnedProcess(['/data/isaac-sim-5.1.0/python.sh','-u',str(ROOT/'scripts/simulation/isaac_rl_worker.py'),
            '--transfer',str(a.transfer),'--output',str(a.output/'worker'),'--socket',str(a.output/'worker.sock'),
            '--max-steps','1000','--physics-substeps','5','--ik-backend','tianji','--tianji-sdk',str(a.tianji_sdk),
            '--teacher-min-step-mm','.05','--target-overtravel-mm','.1','--entry-guidance','--wrist-wrench'],
            directory=a.output,name='worker',env=env,cwd=ROOT)
        deadline=time.monotonic()+240
        while not (a.output/'worker.sock').exists():
            if worker.poll() is not None:raise RuntimeError('worker exited before ready')
            if time.monotonic()>deadline:raise TimeoutError('worker startup')
            time.sleep(.2)
        probe(a)
    except BaseException as exc:failed=True;error=repr(exc);raise
    finally:
        if worker and worker.poll() is None:
            try:
                from omi_hil_rl.training.isaac_client import IsaacClient
                c=IsaacClient(a.output/'worker.sock');c.request('shutdown');c.close()
                if worker.wait(45):failed=True
            except BaseException:failed=True;worker.stop()
        write_json(a.output/'result.json',dict(complete=not failed,error=error,worker=worker.record if worker else None))
        for s,h in previous.items():signal.signal(s,h)


if __name__=='__main__':main()
