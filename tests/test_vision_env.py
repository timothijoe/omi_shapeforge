"""Optional integration checks against a generated real-URDF optical scene."""
import importlib.util
import os
import unittest

SCENE = os.environ.get("OMI_VISION_SCENE")
AVAILABLE = SCENE and all(importlib.util.find_spec(x) for x in ("mujoco", "numpy", "gymnasium"))
if AVAILABLE:
    import numpy as np
    from omi_shapeforge.sim.vision_env import DualCameraPreinsertEnv


@unittest.skipUnless(AVAILABLE, "set OMI_VISION_SCENE in the simulation environment")
class VisionEnvironmentTests(unittest.TestCase):
    def setUp(self):
        self.env = DualCameraPreinsertEnv(SCENE)

    def tearDown(self):
        self.env.close()

    def test_causal_history_padding_and_reset(self):
        env = self.env
        obs, info = env.reset(seed=7)
        self.assertTrue(env.observation_space.contains(obs))
        np.testing.assert_array_equal(obs["history_mask"], [0] * 9 + [1])
        self.assertFalse(obs["camera_mask"][:-1].any())
        initial = {key: value.copy() for key, value in obs.items()}
        for _ in range(10):
            nxt, _, _, _, nxt_info = env.step(env.scripted_action())
            np.testing.assert_array_equal(nxt["rgb"][:-1], obs["rgb"][1:])
            np.testing.assert_array_equal(nxt["wrist_rgb"][:-1], obs["wrist_rgb"][1:])
            self.assertEqual(nxt_info["simulation_time_ns"] - info["simulation_time_ns"], 100_000_000)
            self.assertEqual(len(set(nxt_info["camera_time_ns"].values())), 1)
            self.assertFalse(nxt["state"].any())
            self.assertFalse(nxt["tactile"].any())
            obs, info = nxt, nxt_info
        self.assertTrue(obs["history_mask"].all())
        reset, _ = env.reset(seed=7)
        for key in initial:
            np.testing.assert_array_equal(initial[key], reset[key])

    def test_camera_attachment_rigid_module_and_actual_pixels_change(self):
        env = self.env
        first, _ = env.reset(seed=7)
        head = env.model.camera("head_rgb").id
        wrist = env.model.camera("wrist_rgb").id
        module = env.model.body("held_module").id
        socket = env.model.body("reference_socket").id

        def relative():
            r = env.data.site_xmat[env.site].reshape(3, 3)
            return r.T @ (env.data.xpos[module] - env.data.site_xpos[env.site])

        before_head, before_wrist = env.data.cam_xpos[head].copy(), env.data.cam_xpos[wrist].copy()
        before_socket, before_module = env.data.xpos[socket].copy(), relative()
        for _ in range(12):
            last, _, _, _, _ = env.step(env.scripted_action())
        np.testing.assert_allclose(before_head, env.data.cam_xpos[head], atol=1e-12)
        self.assertGreater(np.linalg.norm(env.data.cam_xpos[wrist] - before_wrist), .001)
        np.testing.assert_allclose(before_socket, env.data.xpos[socket], atol=1e-12)
        np.testing.assert_allclose(before_module, relative(), atol=1e-12)
        for key in ("rgb", "wrist_rgb"):
            self.assertGreater(np.count_nonzero(first[key][-1] != last[key][-1]), 100)

    def test_preinsert_success_timeout_and_invalid_action(self):
        env = self.env
        for seed in (7, 19):
            env.reset(seed=seed)
            for _ in range(env.max_steps):
                _, _, done, truncated, info = env.step(env.scripted_action())
                if done or truncated:
                    break
            self.assertTrue(done and info["is_success"])
            self.assertFalse(truncated)
            self.assertLess(info["tcp_error_m"], .003)
            with self.assertRaises(RuntimeError):
                env.step(np.zeros(6))
        env.reset(seed=7)
        stamp, frames = env.data.time, len(env.frames)
        for action in ([np.nan] * 6, [2.] * 6, [0.] * 7):
            with self.assertRaises(ValueError):
                env.step(action)
            self.assertEqual(env.data.time, stamp)
            self.assertEqual(len(env.frames), frames)
        env.max_steps = 1
        _, _, done, truncated, info = env.step(np.zeros(6))
        self.assertFalse(done or info["is_success"])
        self.assertTrue(truncated)
