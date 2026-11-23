"""Privileged alignment/insertion teacher for the new contact simulation asset."""
from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class ContactRuleConfig:
    lateral_tolerance_m: float = .00012
    rotation_tolerance_rad: float = .0015
    command_limit: float = .85
    slew_per_step: float = .3


class ContactInsertionTeacher:
    version="align-insert-contact-v1"
    def __init__(self,config=ContactRuleConfig()):
        self.config=config;self.reset()

    def reset(self):
        self.phase='align';self.previous=np.zeros(6)

    def act(self,env):
        if env._finished:raise RuntimeError('active contact episode required')
        err=env._error().copy()
        axis=-np.asarray(env.manifest['socket_to_world']['rotation'])[:,1]
        lateral=err[:3]-axis*(err[:3]@axis)
        if env.phase=='withdraw':self.phase='withdraw'
        elif np.linalg.norm(lateral)<self.config.lateral_tolerance_m and np.linalg.norm(err[3:])<self.config.rotation_tolerance_rad:self.phase='insert'
        elif np.linalg.norm(lateral)>.0003 or np.linalg.norm(err[3:])>.005:self.phase='align'
        delta=np.r_[lateral if self.phase=='align' else err[:3],err[3:]]
        desired=np.clip(delta/env.scale,-self.config.command_limit,self.config.command_limit)
        action=self.previous+np.clip(desired-self.previous,-self.config.slew_per_step,self.config.slew_per_step)
        self.previous=action.copy()
        return action.astype(np.float32),dict(controller=self.version,phase=self.phase,privileged_state=True,
            lateral_error_m=float(np.linalg.norm(lateral)),task=env.task_id)
