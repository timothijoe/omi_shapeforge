"""MuJoCo images and causal ten-frame observations for the OMI visual learner."""
from collections import deque

import gymnasium as gym
import mujoco
import numpy as np

from .robot_env import RobotReachEnv


class DualCameraPreinsertEnv(RobotReachEnv):
    """Keep truth in info/reward; policy receives two rendered cameras + padding."""

    task_id = "rigid-held-module-preinsert-v1"

    def __init__(self, scene_dir, render_mode=None, max_steps=100):
        super().__init__(scene_dir, render_mode)
        if self.manifest.get("task") != self.task_id:
            raise ValueError("build the dual-camera pre-insertion scene first")
        if type(max_steps) is not int or max_steps < 1:
            raise ValueError("max_steps must be a positive integer")
        self.max_steps = max_steps
        self.observation_space = gym.spaces.Dict({
            "rgb": gym.spaces.Box(0, 255, (10, 3, 128, 128), np.uint8),
            "wrist_rgb": gym.spaces.Box(0, 255, (10, 3, 128, 128), np.uint8),
            "tactile": gym.spaces.Box(-1e30, 1e30, (10, 10, 16, 24), np.float32),
            "state": gym.spaces.Box(-1e30, 1e30, (10, 14), np.float32),
            "camera_mask": gym.spaces.Box(0, 1, (10, 2), np.float32),
            "history_mask": gym.spaces.Box(0, 1, (10,), np.uint8),
        })
        self.frames = deque(maxlen=10)
        self._vision_renderer = None
        self._visual_options = mujoco.MjvOption()
        self._visual_options.geomgroup[3:] = 0  # Imported collision meshes are not RGB surfaces.
        self._capture_enabled = False

    def render_camera(self, name, *, segmentation=False):
        if name not in ("head_rgb", "wrist_rgb"):
            raise ValueError("unknown task camera")
        if self._vision_renderer is None:
            self._vision_renderer = mujoco.Renderer(self.model, height=128, width=128)
        renderer = self._vision_renderer
        if segmentation:
            renderer.enable_segmentation_rendering()
        try:
            renderer.update_scene(self.data, camera=name, scene_option=self._visual_options)
            return renderer.render().copy()
        finally:
            renderer.disable_segmentation_rendering()

    def _capture(self):
        return {"rgb": self.render_camera("head_rgb").transpose(2, 0, 1),
                "wrist_rgb": self.render_camera("wrist_rgb").transpose(2, 0, 1),
                "tactile": np.zeros((10, 16, 24), np.float32),
                "state": np.zeros(14, np.float32),
                "camera_mask": np.ones(2, np.float32)}

    def _obs(self):
        # Parent reset/step call this method. Capture exactly once after each step.
        if not self._capture_enabled:
            return {}
        frame = self._capture()
        self.frames.append(frame)
        missing = 10 - len(self.frames)
        obs = {key: np.stack([np.zeros_like(value)] * missing + [f[key] for f in self.frames])
               for key, value in frame.items()}
        obs["history_mask"] = np.array([0] * missing + [1] * len(self.frames), np.uint8)
        return obs

    def reset(self, *, seed=None, options=None):
        options = {} if options is None else dict(options)
        if set(options) - {"joint_offset"}:
            raise ValueError("unsupported vision reset option")
        offset = options.get("joint_offset")
        if offset is not None:
            offset = np.asarray(offset, dtype=float)
            if offset.shape != (7,) or not np.isfinite(offset).all() or np.any(np.abs(offset) > .15):
                raise ValueError("joint_offset must be seven finite initial offsets within 0.15 rad")
            initial = np.asarray(self.manifest["initial_qpos"])[self.qids] + offset
            if np.any(initial < self.model.jnt_range[self.ids, 0]) or np.any(initial > self.model.jnt_range[self.ids, 1]):
                raise ValueError("initial joint offset exceeds limits")
        self._capture_enabled = False
        super().reset(seed=seed)
        if offset is not None:
            # Only episode initialization may set state. All teacher commands
            # subsequently go through the same IK/servo/physics step as policy.
            self.data.qpos[self.qids] = initial
            self.data.ctrl[self.aids] = initial
        self.goal_pos = np.array(self.manifest["goal_tcp_position"])
        self.goal_rot = np.array(self.manifest["goal_tcp_rotation"])
        self.model.site_pos[self.model.site("reach_goal").id] = self.goal_pos
        mujoco.mj_forward(self.model, self.data)
        self.frames.clear()
        self._capture_enabled = True
        return self._obs(), self._info()

    def render_overview(self, width=640, height=480):
        """Presentation-only robot overview; never added to policy observations."""
        if not hasattr(self, "_overview_renderer") or self._overview_renderer is None:
            self._overview_renderer = mujoco.Renderer(self.model, height=height, width=width)
        camera = mujoco.MjvCamera()
        camera.lookat[:] = [.35, .05, .75]
        camera.distance, camera.azimuth, camera.elevation = 1.65, 130, -25
        self._overview_renderer.update_scene(self.data, camera=camera, scene_option=self._visual_options)
        return self._overview_renderer.render().copy()

    def _info(self):
        return dict(task=self.manifest["task"], contacts_enabled=False, tcp_calibrated=False,
                    padding=["state", "tactile"], simulation_time_ns=1 + round(self.data.time * 1e9),
                    camera_time_ns={key: 1 + round(self.data.time * 1e9) for key in ("head_rgb", "wrist_rgb")},
                    tcp_position_m=self.data.site_xpos[self.site].copy())

    def step(self, action):
        obs, reward, terminated, truncated, info = super().step(action)
        info.update(self._info())
        return obs, float(reward), terminated, truncated, info

    def render(self):
        return np.concatenate([self.render_camera(name) for name in ("head_rgb", "wrist_rgb")], axis=1)

    def close(self):
        if getattr(self, "_overview_renderer", None) is not None:
            self._overview_renderer.close()
            self._overview_renderer = None
        if self._vision_renderer is not None:
            self._vision_renderer.close()
            self._vision_renderer = None
        super().close()
