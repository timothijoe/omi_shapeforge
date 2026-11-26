"""Reconstruct a BC-only comparison from a saved contract, without physics.

The space-only environment refuses reset/step so this cannot accidentally
perform online RL. Original data/model files remain read-only.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import gymnasium as gym
import numpy as np
import torch

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT.parent/'omi_proj/src')]
from omi_hil_rl.training.hierarchical_insertion.cli import train_s0


class OfflineContractEnv(gym.Env):
    metadata={}
    def __init__(self,config,seed):
        self.config=config;self.schema=config['schema'];self.intervention='scripted';self.next_seed=seed
        self.observation_space=gym.spaces.Dict(dict(reference=gym.spaces.Box(-np.inf,np.inf,(self.schema['reference_points']*6+9,),np.float32),
            history=gym.spaces.Box(-np.inf,np.inf,(self.schema['history_slots']*19,),np.float32)))
        self.action_space=gym.spaces.Box(-1.,1.,(6,),np.float32)
    def reset(self,**kwargs):raise AssertionError('BC-only reconstruction must not reset physics')
    def step(self,action):raise AssertionError('BC-only reconstruction must not perform online transitions')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ['template-config','dataset','output']:p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--seed',type=int,default=200000);p.add_argument('--bc-steps',type=int,default=1000)
    p.add_argument('--bc-checkpoint-steps',type=int,default=0)
    p.add_argument('--reference-input',choices=['path','goal-only'],default='path')
    p.add_argument('--target-schedule',type=Path)
    p.add_argument('--reset-distribution',type=Path)
    p.add_argument('--bc-sampling',choices=['uniform','phase-balanced'],default='uniform')
    p.add_argument('--initial-policy-std',type=float,default=.03)
    p.add_argument('--max-policy-std',type=float)
    p.add_argument('--actor-learning-rate',type=float)
    p.add_argument('--intervention-bc-weight',type=float,default=1.)
    p.add_argument('--entropy-coef',default='auto_0.01')
    p.add_argument('--target-entropy',type=float,default=-12.)
    p.add_argument('--learning-starts',type=int,default=64)
    p.add_argument('--device',choices=['cpu','cuda'],default='cuda');a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=False);torch.set_num_threads(2)
    config=json.loads(a.template_config.read_text())
    if a.reference_input=='goal-only':config['schema']['reference_input']='goal-only-zero-waypoints-v1'
    else:config['schema'].pop('reference_input',None)
    config['intervention']=dict(version='hierarchical-scripted-takeover-v1',mode='scripted',gate='isaac_intervention.Gate',
        source='privileged rule; not human',initial_alignment=True,hold_through_recovery=True,evaluation='policy only')
    if a.target_schedule:config['target_schedule']=dict(version='seed-modulo-target-list-v1',poses=json.loads(a.target_schedule.read_text()))
    if a.reset_distribution:
        if a.target_schedule:p.error('choose a reset distribution or target schedule')
        from omi_hil_rl.training.hierarchical_insertion.randomization import validate_reset_distribution
        config['reset_distribution']=validate_reset_distribution(json.loads(a.reset_distribution.read_text()))
    env=OfflineContractEnv(config,a.seed)
    args=SimpleNamespace(output=a.output,steps=0,bc_steps=a.bc_steps,model=None,demos=a.dataset,device=a.device,seed=a.seed,
        capacity=20000,learning_starts=a.learning_starts,batch_size=32,intervention_fraction=.5,intervention_bc_weight=a.intervention_bc_weight,
        initial_policy_std=a.initial_policy_std,entropy_coef=a.entropy_coef,target_entropy=a.target_entropy,
        bc_checkpoint_steps=a.bc_checkpoint_steps,bc_sampling=a.bc_sampling,
        max_policy_std=a.max_policy_std,actor_learning_rate=a.actor_learning_rate)
    (a.output/'config.json').write_text(json.dumps(config,indent=2)+'\n')
    train_s0(args,env)
    report=dict(scope='new BC-only reconstruction, not a recovered original checkpoint; no physics or RL',
        arguments={k:str(v) if isinstance(v,Path) else v for k,v in vars(a).items()},
        template_sha256=hashlib.sha256(a.template_config.read_bytes()).hexdigest(),
        dataset_sha256=hashlib.sha256((a.dataset/'dataset.json').read_bytes()).hexdigest())
    (a.output/'reconstruction.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
