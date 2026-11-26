import unittest
try:
    import numpy as np
    from omi_shapeforge.sim.pose_correction import gripper_pose_errors
    from omi_shapeforge.sim.isaac_contact_kinematics import axis_rotation
except ImportError:np=None


@unittest.skipIf(np is None,'optional numpy required')
class PoseCorrectionTests(unittest.TestCase):
    def test_forward_travel_is_not_mistaken_for_lateral_error(self):
        aligned=np.eye(4);aligned[:3,:3]=axis_rotation(np.array([0.,0.,1.]),.02)
        a=dict(tcp_from_gripper=np.eye(4).tolist(),aligned_gripper=aligned.tolist())
        for distance in [0.,.04,.09]:
            row=dict(tcp_position=[distance,0.,0.],tcp_rotation=aligned[:3,:3].tolist())
            e=gripper_pose_errors(row,a,[1.,0.,0.])
            self.assertAlmostEqual(e['lateral_mm'],0.,places=9)
            self.assertAlmostEqual(e['vertical_mm'],0.,places=9)

    def test_signed_offsets_and_orientation_at_initial_pose(self):
        aligned=np.eye(4);aligned[:3,:3]=axis_rotation(np.array([0.,0.,1.]),.02)
        r=aligned[:3,:3]@axis_rotation(np.array([0.,0.,1.]),np.deg2rad(5.))@axis_rotation(np.array([0.,1.,0.]),np.deg2rad(-5.))
        row=dict(tcp_position=(aligned[:3,:3]@np.array([0.,.01,-.002])).tolist(),tcp_rotation=r.tolist())
        a=dict(tcp_from_gripper=np.eye(4).tolist(),aligned_gripper=aligned.tolist())
        e=gripper_pose_errors(row,a,[1.,0.,0.])
        np.testing.assert_allclose([e['lateral_mm'],e['vertical_mm'],e['pitch_deg'],e['yaw_deg']],[10.,-2.,-5.,5.],atol=1e-10)


if __name__=='__main__':unittest.main()
