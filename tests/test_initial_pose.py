import copy
import unittest
try:
    import numpy as np
    from omi_shapeforge.sim.initial_pose import initial_tcp_target, validate_initial_pose
    from omi_shapeforge.sim.isaac_contact_kinematics import transform
except ImportError:
    np = None


@unittest.skipIf(np is None, 'optional numpy required')
class InitialPoseTests(unittest.TestCase):
    def fixture(self):
        m = dict(socket_to_world=dict(position_m=[.6, .2, .8], rotation=np.eye(3).tolist()),
                 tool_to_module=dict(position_m=[0., 0., 0.], rotation=np.eye(3).tolist()),
                 leading_tip_y_mm=-100., nominal_module_center_xz_mm=[0., 0.], mouth_y_mm=0.,
                 goal_tcp_rotation=np.eye(3).tolist())
        g = transform([0., .05, 0.], np.array([[0., 1., 0.], [-1., 0., 0.], [0., 0., 1.]]))
        spec = dict(gap_mm=10., lateral_mm=0., vertical_mm=0., pitch_deg=0., yaw_deg=0.)
        return m, g, spec

    def test_aligned_gap_and_target_manifest_preserved(self):
        m, g, spec = self.fixture(); original = copy.deepcopy(m)
        t, audit = initial_tcp_target(m, g, spec)
        np.testing.assert_allclose(t@np.array([0., -.1, 0., 1.]), [.6, .21, .8, 1.], atol=1e-12)
        self.assertEqual(m, original)

    def test_rotation_is_about_gripper_not_tcp_and_translation_uses_aligned_axes(self):
        m, g, spec = self.fixture(); base, _ = initial_tcp_target(m, g, spec)
        spec.update(pitch_deg=2., yaw_deg=-2., lateral_mm=2., vertical_mm=1.)
        tilted, audit = initial_tcp_target(m, g, spec)
        np.testing.assert_allclose((tilted@g)[:3, 3], (base@g)[:3, 3]+[.002, 0., .001], atol=1e-12)
        self.assertGreater(np.linalg.norm(tilted[:3, 3]-base[:3, 3]-[.002, 0., .001]), .001)
        relative=(base@g)[:3,:3].T@(tilted@g)[:3,:3]
        angles=np.rad2deg([np.arctan2(relative[1,0],relative[0,0]),np.arcsin(-relative[2,0]),np.arctan2(relative[2,1],relative[2,2])])
        np.testing.assert_allclose(angles,[-2.,2.,0.],atol=1e-10)

    def test_invalid_initial_pose_rejected(self):
        _, _, spec = self.fixture()
        for change in [dict(gap_mm=1.), dict(pitch_deg=float('nan')), dict(yaw_deg=10.), dict(lateral_mm=10.01), dict(extra=0.)]:
            with self.assertRaises(ValueError):validate_initial_pose(dict(spec, **change))
        for lateral in [-10.,10.]:self.assertEqual(validate_initial_pose(dict(spec,lateral_mm=lateral))['lateral_mm'],lateral)

    def test_far_reset_respects_solver_continuity_without_mutating_input(self):
        from omi_shapeforge.sim.initial_pose import solve_reset_ik
        from omi_shapeforge.sim.isaac_contact_kinematics import axis_rotation
        class Kin:
            def tcp(self,q):return q['pose']
        class Solver:
            def solve(self,q,target):
                if np.linalg.norm(target[:3,3]-q['pose'][:3,3])>.004:
                    raise RuntimeError('per-control continuity rejected')
                return {'pose':target.copy()}
        q={'pose':np.eye(4)};target=transform([-.03,.004,0.],axis_rotation(np.array([0.,0.,1.]),np.deg2rad(2.)))
        with self.assertRaisesRegex(RuntimeError,'continuity'):Solver().solve(q,target)
        solved,audit=solve_reset_ik(Solver(),Kin(),q,target)
        np.testing.assert_allclose(solved['pose'],target,atol=1e-12)
        np.testing.assert_array_equal(q['pose'],np.eye(4))
        self.assertGreater(audit['numerical_ik_stages'],1)
        self.assertEqual(audit['physical_preparation_actions'],0)


if __name__ == '__main__':unittest.main()
