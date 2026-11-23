"""Small real-URDF reach environment: 6D TCP increments -> DLS IK -> joint servos.

This is a software/kinematics milestone, not the contact insertion environment.
"""
import json
from pathlib import Path

import gymnasium as gym
import mujoco
import numpy as np


class RobotReachEnv(gym.Env):
    metadata = {"render_modes": ["rgb_array"], "render_fps": 10}

    def __init__(self, scene_dir, render_mode=None):
        super().__init__()
        if render_mode not in (None, "rgb_array"):
            raise ValueError("unsupported render mode")
        directory = Path(scene_dir)
        self.manifest = json.loads((directory / "robot_manifest.json").read_text())
        self.model = mujoco.MjModel.from_xml_path(str(directory / "scene.xml"))
        self.data = mujoco.MjData(self.model)
        self.ik_data = mujoco.MjData(self.model)
        self.ids = np.array([self.model.joint(f"Arm_L{i}_Joint").id for i in range(1, 8)])
        self.qids = self.model.jnt_qposadr[self.ids]
        self.dids = self.model.jnt_dofadr[self.ids]
        self.aids = np.array([self.model.actuator(f"servo_Arm_L{i}_Joint").id for i in range(1, 8)])
        self.site = self.model.site("urdf_tcp_L").id
        self.scale = np.array([.001 / np.sqrt(3)] * 3 + [np.pi / 180 / np.sqrt(3)] * 3)
        self.action_space = gym.spaces.Box(-1, 1, (6,), np.float32)
        self.observation_space = gym.spaces.Dict({"state": gym.spaces.Box(-np.inf, np.inf, (14,), np.float32),
            "tcp_pose": gym.spaces.Box(-np.inf, np.inf, (7,), np.float32),
            "goal_error": gym.spaces.Box(-np.inf, np.inf, (6,), np.float32)})
        self.render_mode, self._renderer = render_mode, None
        self._finished = True
        self.max_steps = 100

    @staticmethod
    def _rotation_error(current, target):
        return .5 * sum(np.cross(current[:, i], target[:, i]) for i in range(3))

    def _error(self):
        rotation = self.data.site_xmat[self.site].reshape(3, 3)
        return np.r_[self.goal_pos - self.data.site_xpos[self.site], self._rotation_error(rotation, self.goal_rot)]

    def _obs(self):
        quaternion = np.empty(4)
        mujoco.mju_mat2Quat(quaternion, self.data.site_xmat[self.site])
        return {"state": np.r_[self.data.qpos[self.qids], self.data.qvel[self.dids]].astype(np.float32),
                "tcp_pose": np.r_[self.data.site_xpos[self.site], quaternion].astype(np.float32),
                "goal_error": self._error().astype(np.float32)}

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        if options:
            raise ValueError("no reset options in robot reach MVP")
        mujoco.mj_resetData(self.model, self.data)
        self.data.qpos[:] = self.manifest["initial_qpos"]
        self.data.qpos[self.qids] += self.np_random.uniform(-.005, .005, 7)
        for actuator in range(self.model.nu):
            joint = self.model.actuator_trnid[actuator, 0]
            self.data.ctrl[actuator] = self.data.qpos[self.model.jnt_qposadr[joint]]
        mujoco.mj_forward(self.model, self.data)
        self.ik_data.qpos[:] = self.data.qpos
        self.ik_data.qpos[self.qids] += [.02, -.015, .01, 0, .01, 0, 0]
        mujoco.mj_forward(self.model, self.ik_data)
        self.goal_pos = self.ik_data.site_xpos[self.site].copy()
        self.goal_rot = self.ik_data.site_xmat[self.site].reshape(3, 3).copy()
        self.model.site_pos[self.model.site("reach_goal").id] = self.goal_pos
        mujoco.mj_forward(self.model, self.data)
        self._steps, self._finished = 0, False
        return self._obs(), {"contract": "marvin-urdf-tcp-reach-state-v0", "contacts_enabled": False}

    def step(self, action):
        if self._finished:
            raise RuntimeError("reset required")
        action = np.asarray(action, dtype=float)
        if action.shape != (6,) or not np.isfinite(action).all() or np.any(np.abs(action) > 1):
            raise ValueError("expected normalized 6D action")
        before = float(np.linalg.norm(self._error()[:3]))
        position_before = self.data.site_xpos[self.site].copy()
        target_pos = self.data.site_xpos[self.site] + action[:3] * self.scale[:3]
        current_q = np.empty(4)
        mujoco.mju_mat2Quat(current_q, self.data.site_xmat[self.site])
        delta = action[3:] * self.scale[3:]
        angle = np.linalg.norm(delta)
        dq = np.array([1., 0, 0, 0])
        if angle > 0:
            mujoco.mju_axisAngle2Quat(dq, delta / angle, angle)
        desired_q = np.empty(4)
        mujoco.mju_mulQuat(desired_q, dq, current_q)
        desired_r = np.empty(9)
        mujoco.mju_quat2Mat(desired_r, desired_q)
        desired_r = desired_r.reshape(3, 3)
        self.ik_data.qpos[:] = self.data.qpos
        for _ in range(12):
            mujoco.mj_forward(self.model, self.ik_data)
            error = np.r_[target_pos - self.ik_data.site_xpos[self.site],
                self._rotation_error(self.ik_data.site_xmat[self.site].reshape(3, 3), desired_r) * .1]
            jp, jr = np.zeros((3, self.model.nv)), np.zeros((3, self.model.nv))
            mujoco.mj_jacSite(self.model, self.ik_data, jp, jr, self.site)
            J = np.vstack([jp[:, self.dids], jr[:, self.dids] * .1])
            delta_q = J.T @ np.linalg.solve(J @ J.T + np.eye(6) * 1e-5, error)
            self.ik_data.qpos[self.qids] = np.clip(self.ik_data.qpos[self.qids] + np.clip(delta_q, -.03, .03),
                self.model.jnt_range[self.ids, 0], self.model.jnt_range[self.ids, 1])
        self.data.ctrl[self.aids] = self.ik_data.qpos[self.qids]
        self._advance_physics(round(.1 / self.model.opt.timestep))
        self._steps += 1
        error = self._error()
        success = np.linalg.norm(error[:3]) < .003 and np.linalg.norm(error[3:]) < .02
        truncated = self._steps >= self.max_steps and not success
        self._finished = bool(success or truncated)
        info = {"is_success": bool(success), "task": "urdf_tcp_small_reach_not_insertion",
                "tcp_error_m": float(np.linalg.norm(error[:3])), "rotation_error_rad_approx": float(np.linalg.norm(error[3:])),
                "requested_action": action.copy(), "joint_targets": self.data.ctrl[self.aids].copy(),
                "measured_tcp_delta_m": self.data.site_xpos[self.site].copy() - position_before,
                "contacts_enabled": False, "tcp_calibrated": False}
        return self._obs(), 20 * (before - info["tcp_error_m"]) - .001 + float(success), bool(success), bool(truncated), info

    def _advance_physics(self, count):
        for _ in range(count):
            mujoco.mj_step(self.model, self.data)

    def scripted_action(self):
        return np.clip(self._error() / self.scale, -1, 1).astype(np.float32)

    def render(self):
        if self.render_mode != "rgb_array":
            raise RuntimeError("rgb_array render mode required")
        if self._renderer is None:
            self._renderer = mujoco.Renderer(self.model, height=800, width=1000)
        camera = mujoco.MjvCamera()
        camera.lookat[:] = [.30, 0, .75]
        camera.distance, camera.azimuth, camera.elevation = 2.5, 135, -20
        self._renderer.update_scene(self.data, camera=camera)
        return self._renderer.render().copy()

    def close(self):
        if self._renderer is not None:
            self._renderer.close()
            self._renderer = None
