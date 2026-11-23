"""Versioned, explicit configuration for the small RL interface prototype."""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class InsertionConfig:
    channel_width_m: float = .019
    channel_height_m: float = .0096
    shaft_width_m: float = .01817410253
    shaft_height_m: float = .00783825293
    shaft_length_m: float = .05128169432
    head_height_m: float = .01044950355
    head_length_m: float = .018905
    timestep_s: float = .001
    control_period_s: float = .1
    translation_step_m: float = .001 / math.sqrt(3)
    rotation_step_rad: float = math.pi / 180 / math.sqrt(3)
    max_steps: int = 160
    reset_lateral_noise_m: float = .001
    success_lateral_m: float = .0002
    success_depth_m: float = .0005
    success_angle_rad: float = .01
    success_dwell_steps: int = 3
    failure_penetration_m: float = .0003

    def __post_init__(self):
        for key in ["channel_width_m", "channel_height_m", "shaft_width_m", "shaft_height_m",
                    "shaft_length_m", "head_height_m", "head_length_m", "timestep_s",
                    "control_period_s", "translation_step_m", "rotation_step_rad",
                    "success_lateral_m", "success_depth_m", "success_angle_rad", "failure_penetration_m"]:
            value = getattr(self, key)
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"{key} must be finite and positive")
        ticks = self.control_period_s / self.timestep_s
        if ticks < 1 or not math.isclose(ticks, round(ticks), abs_tol=1e-9):
            raise ValueError("control period must be an integer number of physics ticks")
        if type(self.max_steps) is not int or self.max_steps < 1:
            raise ValueError("max_steps must be a positive integer")
        if type(self.success_dwell_steps) is not int or self.success_dwell_steps < 1:
            raise ValueError("success_dwell_steps must be a positive integer")
        if not math.isfinite(self.reset_lateral_noise_m) or not 0 <= self.reset_lateral_noise_m <= .004:
            raise ValueError("reset noise must be in [0, .004] m")
        if self.channel_width_m <= self.shaft_width_m or self.channel_height_m <= self.shaft_height_m:
            raise ValueError("this prototype requires positive nominal shaft clearance")

    def contract(self):
        return {"schema_version": 1, "id": "shapeforge-insertion-state-v0",
                "action": {"shape": [6], "dtype": "float32", "bounds": [-1, 1],
                           "components": ["dx", "dy", "dz", "droll", "dpitch", "dyaw"],
                           "translation_scale_m": self.translation_step_m,
                           "rotation_scale_rad": self.rotation_step_rad,
                           "frame": "socket frame; inward is -Y",
                           "semantics": "bounded commanded increments, not measured motion"},
                "observation": {"state": [12], "target_pose": [6], "pose_error": [6]},
                "hz": 1 / self.control_period_s,
                "success": "proxy geometric alignment/depth, dwell and penetration check",
                "physics_scope": "six-axis servo fixture, primitive shaft/channel; no robot or flexible fingers",
                "not_compatible_with": ["7D joint-action reach checkpoints", "HIL camera/tactile history replay"],
                "physical_insertability_validated": False}
