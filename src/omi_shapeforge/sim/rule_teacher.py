"""Privileged finite-state teacher for the contact-disabled preinsert task.

Uses simulation TCP/socket truth to generate bounded *commands*. It never
writes qpos, advances physics, supplies observations, or overrides success.
"""
from dataclasses import asdict, dataclass

import numpy as np


@dataclass(frozen=True)
class RuleConfig:
    lateral_tolerance_m: float = .0015
    rotation_tolerance_rad: float = .015
    gain: float = .8
    command_limit: float = .85
    slew_per_step: float = .35

    def __post_init__(self):
        if not all(np.isfinite(v) and v > 0 for v in asdict(self).values()):
            raise ValueError("rule settings must be finite and positive")
        if self.command_limit > 1 or self.slew_per_step > 2:
            raise ValueError("rule command bounds exceed the normalized action contract")


class PreinsertRuleTeacher:
    version = "align-approach-preinsert-v1"

    def __init__(self, config=RuleConfig()):
        self.config = config
        self.reset()

    def reset(self):
        self.phase = "align"
        self.previous = np.zeros(6)

    def act(self, env):
        if env._finished:
            raise RuntimeError("teacher requires an active episode")
        error = env._error().copy()
        axis = -np.asarray(env.manifest["socket_to_world"]["rotation"])[:, 1]
        axial = float(error[:3] @ axis)
        lateral = error[:3] - axis * axial
        lateral_norm, angle = float(np.linalg.norm(lateral)), float(np.linalg.norm(error[3:]))
        cfg = self.config
        if self.phase == "align" and lateral_norm < cfg.lateral_tolerance_m and angle < cfg.rotation_tolerance_rad:
            self.phase = "approach"
        elif self.phase == "approach" and (lateral_norm > cfg.lateral_tolerance_m * 2 or angle > cfg.rotation_tolerance_rad * 2):
            self.phase = "align"
        desired = np.r_[lateral if self.phase == "align" else error[:3], error[3:]]
        desired = np.clip(cfg.gain * desired / env.scale, -cfg.command_limit, cfg.command_limit)
        action = self.previous + np.clip(desired - self.previous, -cfg.slew_per_step, cfg.slew_per_step)
        self.previous = action.copy()
        return action.astype(np.float32), dict(
            controller=self.version, phase=self.phase, privileged_state=True,
            axial_error_m=axial, lateral_error_m=lateral_norm, rotation_error_rad_approx=angle,
            task="preinsert only; no contact insertion")
