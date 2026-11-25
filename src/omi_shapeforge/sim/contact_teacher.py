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

    def act(self,env,*,goal_pos=None,goal_rot=None,motion_mode=None):
        if env._finished:raise RuntimeError('active contact episode required')
        err=env._error().copy()
        if goal_pos is not None or goal_rot is not None:
            if hasattr(env,'goal_error'):
                err=env.goal_error(goal_pos,goal_rot)
            else:
                tcp=env.tcp()
                if goal_pos is not None:err[:3]=np.asarray(goal_pos)-tcp[:3,3]
                if goal_rot is not None:err[3:]=env.rotation_error(tcp[:3,:3],goal_rot)
        axis=-np.asarray(env.manifest['socket_to_world']['rotation'])[:,1]
        lateral=err[:3]-axis*(err[:3]@axis)
        if (motion_mode or env.phase)=='withdraw':self.phase='withdraw'
        elif np.linalg.norm(lateral)<self.config.lateral_tolerance_m and np.linalg.norm(err[3:])<self.config.rotation_tolerance_rad:self.phase='insert'
        elif np.linalg.norm(lateral)>.0003 or np.linalg.norm(err[3:])>.005:self.phase='align'
        delta=np.r_[lateral if self.phase=='align' else err[:3],err[3:]]
        movable='episode_socket_pose' in env.manifest
        if movable:
            # Clipping a long axial error in world XYZ destroys its direction
            # once the slot is rotated. Keep axial/lateral components separate
            # in the socket basis, including the slew limiter.
            socket=np.asarray(env.manifest['socket_to_world']['rotation'])
            basis=np.column_stack((axis,socket[:,0],socket[:,2]))
            local=np.r_[basis.T@delta[:3],basis.T@delta[3:]]
            previous=np.r_[basis.T@self.previous[:3],basis.T@self.previous[3:]]
            desired=np.clip(local/env.scale,-self.config.command_limit,self.config.command_limit)
            command=previous+np.clip(desired-previous,-self.config.slew_per_step,self.config.slew_per_step)
            action=np.r_[basis@command[:3],basis@command[3:]]
        else:
            desired=np.clip(delta/env.scale,-self.config.command_limit,self.config.command_limit)
            action=self.previous+np.clip(desired-self.previous,-self.config.slew_per_step,self.config.slew_per_step)
        self.previous=action.copy()
        return action.astype(np.float32),dict(controller='align-insert-socket-frame-v2' if movable else self.version,phase=self.phase,privileged_state=True,
            lateral_error_m=float(np.linalg.norm(lateral)),task=env.task_id)
