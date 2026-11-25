"""Privileged recovery subgoals; never modify the insertion task or reset physics."""
from dataclasses import asdict, dataclass
import numpy as np

from .contact_teacher import ContactInsertionTeacher
from .isaac_contact_approach import limit_approach


@dataclass(frozen=True)
class RecoveryConfig:
    version: str = 'retreat-align-reenter-v1'
    max_attempts: int = 2
    phase_max_steps: int = 450
    waypoint_tolerance_mm: float = .08
    strict_entry: bool = False

    def __post_init__(self):
        if any(type(v) is not int or v < 1 for v in (self.max_attempts, self.phase_max_steps)):
            raise ValueError('positive integer recovery budgets required')
        if not 0 < self.waypoint_tolerance_mm < 1:
            raise ValueError('outside waypoint tolerance must be below 1 mm')


class StagedRecoveryTeacher:
    def __init__(self, config=RecoveryConfig()):
        self.config = config
        self.teacher = ContactInsertionTeacher()
        self.reset()

    def reset(self):
        self.teacher.reset()
        self.stage = 'idle'
        self.attempts = self.completed = self.phase_steps = 0
        self.failure = None
        self.retreat_goal = self.retreat_rotation = None

    @property
    def active(self):
        return self.stage in ('retreat', 'align_outside', 'reinsert')

    def status(self):
        return dict(recovery_active=self.active, recovery_stage=self.stage,
                    recovery_attempts=self.attempts, recovery_completed=self.completed,
                    recovery_phase_steps=self.phase_steps, recovery_failure=self.failure)

    def _transition(self, stage):
        self.stage = stage
        self.phase_steps = 0
        # No stale forward slew when backing out of a blocked entrance.
        self.teacher.reset()

    def _start(self, env):
        if self.attempts >= self.config.max_attempts:
            self.failure = 'recovery_attempt_budget'
            self._transition('failed')
            return
        axis = -np.asarray(env.manifest['socket_to_world']['rotation'])[:, 1]
        tcp = env.tcp()
        outside = np.asarray(env.manifest['preinsert_tcp_position'])
        delta = tcp[:3, 3] - outside
        # Preserve measured lateral displacement and orientation during retreat.
        self.retreat_goal = outside + delta - axis * (delta @ axis)
        self.retreat_rotation = tcp[:3, :3].copy()
        self.attempts += 1
        self._transition('retreat')

    def observe(self, env, measurement, *, executed_action=None):
        """Advance only after a real control step, never from repeated queries."""
        if executed_action is not None:
            self.teacher.previous = np.asarray(executed_action).copy()
        if not self.active or measurement.get('failed') or measurement.get('is_success'):
            return
        self.phase_steps += 1
        position = env.tcp()[:3, 3]
        outside = np.asarray(env.manifest['preinsert_tcp_position'])
        tolerance = self.config.waypoint_tolerance_mm / 1000
        if self.stage == 'retreat':
            if (measurement['insertion_depth_mm'] < 0 and
                    np.linalg.norm(position - self.retreat_goal) < tolerance):
                self._transition('align_outside')
        elif self.stage == 'align_outside':
            if (measurement['insertion_depth_mm'] < 0 and
                    np.linalg.norm(position - outside) < tolerance and
                    measurement['alignment_angle_rad'] < self.teacher.config.rotation_tolerance_rad):
                self._transition('reinsert')
        elif self.stage == 'reinsert':
            if measurement.get('recovery_required'):
                self._start(env)
            elif (measurement.get('entry_qualified') and
                  measurement['insertion_depth_mm'] >= env.contact_assessment.config.entry_complete_mm and
                  measurement['lateral_error_mm'] < .12 and
                  measurement['alignment_angle_rad'] < .0015):
                self.completed += 1
                self._transition('idle')
        if self.active and self.phase_steps >= self.config.phase_max_steps:
            self.failure = 'recovery_phase_timeout'
            self._transition('failed')

    def act(self, env, measurement, *, minimum_mm):
        if env._finished or measurement.get('failed') or measurement.get('terminated') or measurement.get('truncated'):
            raise RuntimeError('active nonfailed episode required')
        if not env.contact_assessment:
            raise ValueError('staged assessment required for recovery')
        missed_entry = (self.config.strict_entry and not measurement.get('entry_qualified') and
                        measurement['insertion_depth_mm'] >= env.contact_assessment.config.entry_complete_mm)
        if self.stage == 'idle' and (measurement.get('recovery_required') or missed_entry):
            self._start(env)
        if self.failure:
            raise RuntimeError(self.failure)
        goal, rotation, mode = env.goal_pos, env.goal_rot, 'insert'
        if self.stage == 'retreat':
            goal, rotation, mode = self.retreat_goal, self.retreat_rotation, 'withdraw'
        elif self.stage == 'align_outside':
            goal, mode = np.asarray(env.manifest['preinsert_tcp_position']), 'withdraw'
        action, audit = self.teacher.act(env, goal_pos=goal, goal_rot=rotation, motion_mode=mode)
        axis = -np.asarray(env.manifest['socket_to_world']['rotation'])[:, 1]
        action, limit = limit_approach(action, env.scale, axis,
            env.manifest['shoulder_depth_mm'] - measurement['insertion_depth_mm'], mode, minimum_mm=minimum_mm)
        inhibit = (self.config.strict_entry and not measurement.get('entry_qualified') and mode == 'insert' and
                   (measurement['lateral_error_mm'] >= .10 or measurement['alignment_angle_rad'] >= .0015))
        if inhibit:
            delta = action[:3] * env.scale[:3]
            action[:3] = (delta - axis * max(0., float(delta @ axis))) / env.scale[:3]
        audit.update(self.status(), approach=limit, recovery_config=asdict(self.config),
                     entry_forward_inhibited=bool(inhibit), missed_entry_qualification=bool(missed_entry),
                     task_goal_position=np.asarray(env.goal_pos).tolist(),
                     control_goal_position=np.asarray(goal).tolist(), control_motion_mode=mode)
        return action, audit
