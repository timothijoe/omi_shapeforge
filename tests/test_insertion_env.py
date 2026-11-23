"""Behavioral checks for the optional physical interface fixture."""
import importlib.util
import unittest

AVAILABLE = all(importlib.util.find_spec(name) is not None for name in ("numpy", "gymnasium", "mujoco"))
if AVAILABLE:
    import numpy as np
    from omi_shapeforge.sim.config import InsertionConfig
    from omi_shapeforge.sim.insertion_env import SimpleInsertionEnv


@unittest.skipUnless(AVAILABLE, "optional simulation environment required")
class InsertionEnvironmentTests(unittest.TestCase):
    def test_scripted_nominal_insertion_succeeds_from_perturbed_reset(self):
        env = SimpleInsertionEnv()
        try:
            obs, _ = env.reset(seed=3)
            self.assertTrue(env.observation_space.contains(obs))
            for _ in range(env.config.max_steps):
                obs, _, done, truncated, info = env.step(env.scripted_action())
                if done or truncated:
                    break
            self.assertTrue(info["is_success"], info)
            self.assertTrue(done)
            self.assertFalse(truncated)
            self.assertLess(abs(info["depth_m"] - env.config.shaft_length_m), env.config.success_depth_m)
            with self.assertRaises(RuntimeError):
                env.step(np.zeros(6))
        finally:
            env.close()

    def test_lateral_wall_collision_cannot_count_as_success(self):
        env = SimpleInsertionEnv()
        try:
            env.reset(seed=0, options={"initial_pose": [.003, .005, 0, 0, 0, 0]})
            contacts = 0
            for _ in range(env.config.max_steps):
                _, _, done, truncated, info = env.step(np.array([0, -1, 0, 0, 0, 0]))
                contacts = max(contacts, info["contact_count"])
                self.assertFalse(info["is_success"])
                if done or truncated:
                    break
            self.assertIn(info["reason"], ("penetration_limit", "timeout"))
            self.assertTrue(done or truncated)
            self.assertGreater(contacts, 0)
            self.assertLess(info["depth_m"], env.config.shaft_length_m - env.config.success_depth_m)
        finally:
            env.close()

    def test_timeout_is_truncation_not_success(self):
        env = SimpleInsertionEnv(InsertionConfig(max_steps=1))
        try:
            env.reset(seed=0)
            _, _, done, truncated, info = env.step(np.zeros(6))
            self.assertFalse(done)
            self.assertTrue(truncated)
            self.assertFalse(info["is_success"])
        finally:
            env.close()

    def test_seed_repeatability_and_rejected_action_has_no_side_effect(self):
        env = SimpleInsertionEnv()
        try:
            first, _ = env.reset(seed=41)
            env.step(np.zeros(6))
            second, _ = env.reset(seed=41)
            np.testing.assert_array_equal(first["state"], second["state"])
            time = env.data.time
            with self.assertRaises(ValueError):
                env.step([np.nan, 0, 0, 0, 0, 0])
            self.assertEqual(time, env.data.time)
            np.testing.assert_array_equal(second["state"], env._obs()["state"])
        finally:
            env.close()


if __name__ == "__main__":
    unittest.main()
