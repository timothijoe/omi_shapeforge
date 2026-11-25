import copy
import unittest
try:
    import numpy as np
    from omi_shapeforge.sim.socket_pose import SocketPoseRange,relocate_socket_manifest
    from omi_shapeforge.sim.isaac_contact_kinematics import transform
except ImportError:np=None


@unittest.skipIf(np is None,'optional numpy required')
class SocketPoseTests(unittest.TestCase):
    def test_rotated_slot_clipping_does_not_remove_lateral_correction(self):
        from omi_shapeforge.sim.contact_teacher import ContactInsertionTeacher
        class Env:
            _finished=False;phase='insert';task_id='test'
            scale=np.array([.001/np.sqrt(3)]*3+[np.pi/180/np.sqrt(3)]*3)
            def __init__(self,yaw):
                a=np.deg2rad(yaw);c,s=np.cos(a),np.sin(a)
                self.r=np.array([[c,-s,0],[s,c,0],[0,0,1.]])
                self.manifest=dict(socket_to_world=dict(rotation=(self.r@np.array([[0,-1,0],[1,0,0],[0,0,1.]])).tolist()),episode_socket_pose={})
            def _error(self):return np.r_[self.r@np.array([.05,.00019,0]),[0,0,0]]
        base,turned=Env(0),Env(-.2)
        a,b=ContactInsertionTeacher(),ContactInsertionTeacher();a.phase=b.phase='insert'
        for _ in range(5):
            x,_=a.act(base);y,_=b.act(turned)
            np.testing.assert_allclose(y[:3],turned.r@x[:3],atol=1e-7,rtol=0)
        axis=-np.asarray(turned.manifest['socket_to_world']['rotation'])[:,1]
        translation=y[:3]*turned.scale[:3]
        transverse=translation-axis*(translation@axis)
        self.assertGreater(np.linalg.norm(transverse),.00018)

    def test_bounds_and_seeded_sampling(self):
        config=SocketPoseRange()
        self.assertEqual(config.resolve(4),config.resolve(4))
        self.assertNotEqual(config.resolve(4),config.resolve(5))
        for pose in [dict(dx_mm=.6,dy_mm=0,yaw_deg=0),dict(dx_mm=0,dy_mm=0,yaw_deg=float('nan')),dict(dx_mm=0)]:
            with self.assertRaises(ValueError):config.resolve(0,pose)

    def test_socket_local_targets_invariant_robot_tool_and_thresholds_unchanged(self):
        nominal=dict(socket_to_world=dict(position_m=[.65,.2,.8],rotation=np.eye(3).tolist()),
            goal_tcp_position=[.4,.201,.802],preinsert_tcp_position=[.34,.201,.802],
            seated_tcp_position=[.399,.201,.802],goal_tcp_rotation=np.eye(3).tolist(),
            tool_to_module={'position':[.1,.2,.3]},shoulder_depth_mm=51.28)
        original=copy.deepcopy(nominal)
        pose=dict(dx_mm=.5,dy_mm=-.5,yaw_deg=.2)
        moved,g=relocate_socket_manifest(nominal,pose)
        old=transform(nominal['socket_to_world']['position_m'],np.eye(3))
        new=transform(moved['socket_to_world']['position_m'],np.asarray(moved['socket_to_world']['rotation']))
        np.testing.assert_allclose(new[:3,3],[.6505,.1995,.8],atol=1e-14)
        for key in ['goal_tcp_position','preinsert_tcp_position','seated_tcp_position']:
            a=transform(nominal[key],np.eye(3));b=transform(moved[key],np.asarray(moved['goal_tcp_rotation']))
            np.testing.assert_allclose(np.linalg.inv(old)@a,np.linalg.inv(new)@b,atol=1e-14)
            np.testing.assert_allclose(g@a,b,atol=1e-14)
        self.assertEqual(nominal,original)
        self.assertEqual(moved['tool_to_module'],nominal['tool_to_module'])
        self.assertEqual(moved['shoulder_depth_mm'],nominal['shoulder_depth_mm'])
        zero,z=relocate_socket_manifest(nominal,dict(dx_mm=0,dy_mm=0,yaw_deg=0))
        np.testing.assert_array_equal(z,np.eye(4))
        self.assertEqual(zero['seated_tcp_position'],nominal['seated_tcp_position'])


if __name__=='__main__':unittest.main()
