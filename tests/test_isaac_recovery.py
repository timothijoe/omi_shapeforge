import unittest
from types import SimpleNamespace

try:
    import numpy as np
    from omi_shapeforge.sim.isaac_recovery import StagedRecoveryTeacher, RecoveryConfig
except ImportError:
    np = None


class FakeEnv:
    def __init__(self):
        self.pose = np.eye(4)
        self.pose[:3, 3] = [0, .001, 0]
        self.goal_pos = np.array([.0514, 0, 0])
        self.goal_rot = np.eye(3)
        self.scale = np.array([.001 / np.sqrt(3)] * 3 + [.01] * 3)
        self.manifest = dict(socket_to_world=dict(rotation=[[0, -1, 0], [1, 0, 0], [0, 0, 1]]),
                             preinsert_tcp_position=[-.005, 0, 0], shoulder_depth_mm=51.3)
        self.phase = 'insert'
        self.task_id = 'test-insert'
        self._finished = False
        self.contact_assessment = SimpleNamespace(config=SimpleNamespace(entry_complete_mm=5.))

    def tcp(self):
        return self.pose.copy()

    @staticmethod
    def rotation_error(current, target):
        return .5 * sum(np.cross(current[:, i], target[:, i]) for i in range(3))

    def _error(self):
        return np.r_[self.goal_pos - self.pose[:3, 3], self.rotation_error(self.pose[:3, :3], self.goal_rot)]


def measurement(**changes):
    row = dict(insertion_depth_mm=0., lateral_error_mm=1., alignment_angle_rad=0.,
               recovery_required=True, entry_qualified=False, failed=False, is_success=False)
    row.update(changes)
    return row


@unittest.skipIf(np is None, 'requires optional numpy')
class RecoveryTests(unittest.TestCase):
    def test_retreat_align_reenter_preserves_task_goal_and_requires_qualification(self):
        env = FakeEnv(); teacher = StagedRecoveryTeacher(); goal = env.goal_pos.copy()
        action, audit = teacher.act(env, measurement(), minimum_mm=.05)
        self.assertLess(action[0], 0)
        self.assertAlmostEqual(float(action[1]), 0)
        self.assertEqual(audit['recovery_stage'], 'retreat')
        np.testing.assert_allclose(audit['control_goal_position'], [-.005, .001, 0])
        env.pose[:3, 3] = [-.004, .001, 0]
        teacher.observe(env, measurement(insertion_depth_mm=-4, recovery_required=False))
        self.assertEqual(teacher.stage, 'retreat')
        env.pose[:3, 3] = [-.005, .001, 0]
        teacher.observe(env, measurement(insertion_depth_mm=-5, recovery_required=False))
        self.assertEqual(teacher.stage, 'align_outside')
        action, _ = teacher.act(env, measurement(recovery_required=False), minimum_mm=.05)
        self.assertLess(action[1], 0)
        env.pose[:3, 3] = [-.005, 0, 0]
        teacher.observe(env, measurement(insertion_depth_mm=-5, lateral_error_mm=0, recovery_required=False))
        self.assertEqual(teacher.stage, 'reinsert')
        for qualified, depth in [(False, 4), (False, 5), (True, 4)]:
            teacher.observe(env, measurement(insertion_depth_mm=depth, lateral_error_mm=0,
                                            entry_qualified=qualified, recovery_required=False))
            self.assertTrue(teacher.active)
        teacher.observe(env, measurement(insertion_depth_mm=5, lateral_error_mm=0,
                                        entry_qualified=True, recovery_required=False))
        self.assertFalse(teacher.active)
        self.assertEqual(teacher.completed, 1)
        np.testing.assert_array_equal(env.goal_pos, goal)
        self.assertEqual(env.phase, 'insert')
        self.assertFalse(env._finished)

    def test_queries_do_not_advance_phase_timeout(self):
        env = FakeEnv(); teacher = StagedRecoveryTeacher(RecoveryConfig(phase_max_steps=2))
        for _ in range(5):teacher.act(env, measurement(), minimum_mm=.05)
        self.assertEqual(teacher.phase_steps, 0)
        teacher.observe(env, measurement()); teacher.observe(env, measurement())
        self.assertEqual(teacher.failure, 'recovery_phase_timeout')
        with self.assertRaisesRegex(RuntimeError, 'timeout'):teacher.act(env, measurement(), minimum_mm=.05)

    def test_repeated_blockage_exhausts_budget_without_reset(self):
        env = FakeEnv(); teacher = StagedRecoveryTeacher(RecoveryConfig(max_attempts=1))
        teacher.act(env, measurement(), minimum_mm=.05)
        teacher._transition('reinsert')
        teacher.observe(env, measurement())
        self.assertEqual(teacher.failure, 'recovery_attempt_budget')
        self.assertEqual(teacher.attempts, 1)
        teacher.reset()
        self.assertEqual(teacher.attempts, 0)
        self.assertIsNone(teacher.failure)

    def test_new_blockage_after_two_completed_recoveries_fails_on_real_step(self):
        env=FakeEnv();teacher=StagedRecoveryTeacher(RecoveryConfig(strict_entry=True))
        teacher.attempts=teacher.completed=2;teacher.stage='idle'
        before=env.pose.copy();goal=env.goal_pos.copy()
        teacher.observe(env,measurement(insertion_depth_mm=5.832,entry_qualified=True,recovery_required=True),
                        executed_action=[.1,0,0,0,0,0])
        self.assertEqual(teacher.failure,'recovery_attempt_budget')
        self.assertEqual(teacher.stage,'failed');self.assertEqual(teacher.attempts,2)
        np.testing.assert_array_equal(env.pose,before);np.testing.assert_array_equal(env.goal_pos,goal)

    def test_exhausted_budget_does_not_fail_idle_without_a_new_recovery_need(self):
        env=FakeEnv();teacher=StagedRecoveryTeacher(RecoveryConfig(strict_entry=True));teacher.attempts=2
        teacher.observe(env,measurement(insertion_depth_mm=10.,entry_qualified=True,recovery_required=False))
        self.assertIsNone(teacher.failure);self.assertEqual(teacher.stage,'idle')
        teacher.observe(env,measurement(insertion_depth_mm=6.,entry_qualified=False,recovery_required=False))
        self.assertEqual(teacher.failure,'recovery_attempt_budget')

    def test_success_or_existing_failure_is_not_overridden_by_exhausted_budget(self):
        for field in ('is_success','failed'):
            teacher=StagedRecoveryTeacher(RecoveryConfig(strict_entry=True));teacher.attempts=2
            teacher.observe(FakeEnv(),measurement(**{field:True}))
            self.assertIsNone(teacher.failure)

    def test_failed_measurement_cannot_be_rescued(self):
        env = FakeEnv(); teacher = StagedRecoveryTeacher()
        with self.assertRaises(RuntimeError):teacher.act(env, measurement(failed=True), minimum_mm=.05)
        self.assertFalse(teacher.active)
        self.assertEqual(teacher.attempts, 0)

    def test_retreat_holds_measured_rotation(self):
        env = FakeEnv(); angle = .004
        env.pose[:3, :3] = [[np.cos(angle), -np.sin(angle), 0], [np.sin(angle), np.cos(angle), 0], [0, 0, 1]]
        teacher = StagedRecoveryTeacher()
        action, _ = teacher.act(env, measurement(), minimum_mm=.05)
        np.testing.assert_array_equal(action[3:], 0)

    def test_executed_policy_action_is_slew_origin_but_retreat_discards_forward_slew(self):
        env = FakeEnv(); env.pose[1, 3] = 0
        teacher = StagedRecoveryTeacher()
        teacher.observe(env, measurement(recovery_required=False), executed_action=[.5, 0, 0, 0, 0, 0])
        action, _ = teacher.act(env, measurement(recovery_required=False), minimum_mm=.05)
        self.assertAlmostEqual(float(action[0]), .8, places=6)
        action, _ = teacher.act(env, measurement(), minimum_mm=.05)
        self.assertLess(action[0], 0)

    def test_strict_entry_blocks_forward_slew_and_recovers_missed_window(self):
        env=FakeEnv();env.pose[1,3]=.00011
        teacher=StagedRecoveryTeacher(RecoveryConfig(strict_entry=True))
        action,audit=teacher.act(env,measurement(recovery_required=False,lateral_error_mm=.11),minimum_mm=.05)
        self.assertLessEqual(action[0],0.)
        self.assertTrue(audit['entry_forward_inhibited'])
        action,audit=teacher.act(env,measurement(recovery_required=False,insertion_depth_mm=5.2),minimum_mm=.05)
        self.assertEqual(audit['recovery_stage'],'retreat')
        self.assertTrue(audit['missed_entry_qualification'])


if __name__ == '__main__':unittest.main()
