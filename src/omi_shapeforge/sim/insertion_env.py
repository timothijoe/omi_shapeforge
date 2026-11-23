"""State-only Gymnasium insertion fixture; does not import hardware transports."""
import gymnasium as gym
import mujoco
import numpy as np

from .config import InsertionConfig
from .scene import make_scene


class SimpleInsertionEnv(gym.Env):
    metadata = {"render_modes": ["rgb_array"], "render_fps": 10}

    def __init__(self, config=None, render_mode=None):
        super().__init__()
        self.config = config or InsertionConfig()
        self.render_mode = render_mode
        if render_mode not in (None, "rgb_array"):
            raise ValueError("unsupported render_mode")
        self.scene_xml = make_scene(self.config)
        self.model = mujoco.MjModel.from_xml_string(self.scene_xml)
        self.data = mujoco.MjData(self.model)
        self.action_space = gym.spaces.Box(-1., 1., (6,), np.float32)
        self.observation_space = gym.spaces.Dict({
            "state": gym.spaces.Box(-np.inf, np.inf, (12,), np.float32),
            "target_pose": gym.spaces.Box(-np.inf, np.inf, (6,), np.float32),
            "pose_error": gym.spaces.Box(-np.inf, np.inf, (6,), np.float32)})
        self.goal = np.array([0, -self.config.shaft_length_m + .00015, 0, 0, 0, 0], dtype=float)
        self.scale = np.array([self.config.translation_step_m] * 3 + [self.config.rotation_step_rad] * 3)
        self._renderer = None
        self._finished = True
        self._steps = 0
        self._dwell = 0
        self._command = np.zeros(6)

    def _obs(self):
        if not np.isfinite(self.data.qpos).all() or not np.isfinite(self.data.qvel).all():
            raise RuntimeError("nonfinite physics state")
        return {"state": np.r_[self.data.qpos, self.data.qvel].astype(np.float32),
                "target_pose": self.goal.astype(np.float32).copy(),
                "pose_error": (self.goal - self.data.qpos).astype(np.float32)}

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        mujoco.mj_resetData(self.model, self.data)
        q = np.zeros(6)
        q[1] = .005
        q[[0, 2]] = self.np_random.uniform(-self.config.reset_lateral_noise_m,
                                           self.config.reset_lateral_noise_m, 2)
        if options:
            if set(options) != {"initial_pose"}:
                raise ValueError("only initial_pose reset option is supported")
            q = np.asarray(options["initial_pose"], dtype=float)
            if q.shape != (6,) or not np.isfinite(q).all() or np.any(q < self.model.jnt_range[:, 0]) or np.any(q > self.model.jnt_range[:, 1]):
                raise ValueError("invalid initial pose")
        self.data.qpos[:] = q
        self.data.ctrl[:] = q
        self._command = q.copy()
        self._steps, self._dwell, self._finished = 0, 0, False
        mujoco.mj_forward(self.model, self.data)
        return self._obs(), {"contract": self.config.contract(), "model_kind": "cartesian_proxy_v0"}

    def _error(self):
        difference = self.goal - self.data.qpos
        return float(np.linalg.norm(np.r_[difference[:3], difference[3:] * .02]))

    def step(self, action):
        if self._finished:
            raise RuntimeError("reset required before stepping")
        requested = np.asarray(action, dtype=float)
        if requested.shape != (6,) or not np.isfinite(requested).all() or np.any(np.abs(requested) > 1):
            raise ValueError("action must contain six finite values within [-1, 1]")
        before_q = self.data.qpos.copy()
        error_before = self._error()
        target = np.clip(self._command + requested * self.scale,
                         self.model.jnt_range[:, 0], self.model.jnt_range[:, 1])
        executed = (target - self._command) / self.scale
        self._command = target
        self.data.ctrl[:] = target
        max_penetration = 0.
        max_contacts = 0
        for _ in range(round(self.config.control_period_s / self.config.timestep_s)):
            mujoco.mj_step(self.model, self.data)
            max_contacts = max(max_contacts, self.data.ncon)
            if self.data.ncon:
                max_penetration = max(max_penetration, max(0., -float(np.min(self.data.contact.dist))))
        self._steps += 1
        q = self.data.qpos
        aligned = (np.max(np.abs(q[[0, 2]])) <= self.config.success_lateral_m
                   and np.max(np.abs(q[3:])) <= self.config.success_angle_rad)
        depth_ok = abs(-q[1] - self.config.shaft_length_m) <= self.config.success_depth_m
        settled = np.linalg.norm(self.data.qvel[:3]) < .005
        failure = max_penetration > self.config.failure_penetration_m
        self._dwell = self._dwell + 1 if aligned and depth_ok and settled and not failure else 0
        success = self._dwell >= self.config.success_dwell_steps
        terminated = success or failure
        truncated = self._steps >= self.config.max_steps and not terminated
        self._finished = terminated or truncated
        reward = 50 * (error_before - self._error()) - .001 + float(success) - float(failure)
        info = {"is_success": bool(success), "episode_success": bool(success),
                "reason": "proxy_success" if success else "penetration_limit" if failure else "timeout" if truncated else "active",
                "policy_action": requested.astype(np.float32), "executed_action": executed.astype(np.float32),
                "commanded_pose": target.copy(), "measured_pose_delta": q.copy() - before_q,
                "action_source": "policy", "depth_m": float(-q[1]),
                "lateral_error_m": float(np.linalg.norm(q[[0, 2]])),
                "max_penetration_m": max_penetration, "contact_count": int(max_contacts),
                "model_kind": "cartesian_proxy_v0", "physical_insertion_verified": False}
        return self._obs(), float(reward), bool(terminated), bool(truncated), info

    def scripted_action(self):
        """Oracle fixture controller for plumbing tests, never a learned policy."""
        return np.clip((self.goal - self._command) / self.scale, -1, 1).astype(np.float32)

    def render(self):
        if self.render_mode != "rgb_array":
            raise RuntimeError("construct with render_mode='rgb_array'")
        if self._renderer is None:
            self._renderer = mujoco.Renderer(self.model, height=600, width=800)
        self._renderer.update_scene(self.data, camera="overview")
        return self._renderer.render().copy()

    def close(self):
        if self._renderer is not None:
            self._renderer.close()
            self._renderer = None
