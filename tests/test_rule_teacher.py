"""Verify the teacher acts through commands and has meaningful phase behavior."""
import importlib.util
import os
import unittest
from types import SimpleNamespace

AVAILABLE = importlib.util.find_spec("numpy") is not None
if AVAILABLE:
    import numpy as np
    from omi_shapeforge.sim.rule_teacher import PreinsertRuleTeacher, RuleConfig


@unittest.skipUnless(AVAILABLE, "optional simulation numpy dependency")
class RuleTeacherTests(unittest.TestCase):
    def test_align_before_axial_advance_and_bound_command_slew(self):
        error = np.array([.02, .01, 0, 0, 0, .1])
        env = SimpleNamespace(_finished=False, _error=lambda: error,
            manifest={"socket_to_world": {"rotation": [[0, -1, 0], [1, 0, 0], [0, 0, 1]]}},
            scale=np.array([.001/np.sqrt(3)]*3 + [np.pi/180/np.sqrt(3)]*3))
        teacher = PreinsertRuleTeacher()
        previous = np.zeros(6)
        for _ in range(4):
            action, info = teacher.act(env)
            self.assertEqual(info["phase"], "align")
            self.assertEqual(action[0], 0)
            self.assertLessEqual(abs(action).max(), .850001)
            self.assertLessEqual(abs(action-previous).max(), .350001)
            previous = action
        error[:] = [.02, 0, 0, 0, 0, 0]
        action, info = teacher.act(env)
        self.assertEqual(info["phase"], "approach")
        self.assertGreater(action[0], 0)
        teacher.reset()
        error[:] = [.02, .01, 0, 0, 0, .1]
        again, _ = teacher.act(env)
        self.assertAlmostEqual(float(again[1]), .35, places=6)
        env._finished = True
        with self.assertRaises(RuntimeError):
            teacher.act(env)
        with self.assertRaises(ValueError):
            RuleConfig(command_limit=2)

    @unittest.skipUnless(os.environ.get("OMI_VISION_SCENE") and importlib.util.find_spec("mujoco"), "real scene required")
    def test_teacher_does_not_modify_state_and_reaches_from_perturbed_initializations(self):
        from omi_shapeforge.sim.vision_env import DualCameraPreinsertEnv
        env = DualCameraPreinsertEnv(os.environ["OMI_VISION_SCENE"], max_steps=180)
        try:
            for seed in (100, 103, 113):
                offset = np.random.default_rng(seed).uniform(-.015, .015, 7)
                env.reset(seed=seed, options={"joint_offset": offset})
                controller = PreinsertRuleTeacher()
                for _ in range(env.max_steps):
                    qpos, stamp = env.data.qpos.copy(), env.data.time
                    action, _ = controller.act(env)
                    np.testing.assert_array_equal(qpos, env.data.qpos)
                    self.assertEqual(stamp, env.data.time)
                    obs, _, done, truncated, info = env.step(action)
                    self.assertFalse(obs["state"].any() or obs["tactile"].any())
                    if done or truncated:
                        break
                self.assertTrue(done and info["is_success"])
                self.assertFalse(truncated)
            stamp = env.data.time
            with self.assertRaises(ValueError):
                env.reset(options={"joint_offset": [float("nan")] * 7})
            self.assertEqual(stamp, env.data.time)
        finally:
            env.close()
