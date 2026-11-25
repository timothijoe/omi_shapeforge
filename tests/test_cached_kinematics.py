import copy
import unittest
try:
    import numpy as np
    from omi_shapeforge.sim.isaac_contact_kinematics import Kinematics,local_pose
except ImportError:np=None


@unittest.skipIf(np is None,'optional numpy required')
class CachedKinematicsTests(unittest.TestCase):
    def packet(self):
        return dict(bodies=[dict(id=0,parent=-1,position=[0,0,0],quaternion=[1,0,0,0]),
            dict(id=1,parent=0,position=[.3,.2,.1],quaternion=[.5,.5,.5,.5]),
            dict(id=2,parent=1,position=[.1,0,.2],quaternion=[1,0,0,0]),
            dict(id=3,parent=2,position=[0,.05,0],quaternion=[1,0,0,0]),
            dict(id=4,parent=1,position=[0,-.2,0],quaternion=[1,0,0,0])],
            joints=[dict(name='arm',body=2,kind=3,axis=[0,0,2],position=[.01,.02,0]),
                    dict(name='slide',body=3,kind=2,axis=[0,2,0],position=[0,0,0]),
                    dict(name='unrelated',body=4,kind=3,axis=[1,0,0],position=[0,0,0])],
            sites=[dict(name='urdf_tcp_L',body=3,position=[.03,0,.02],quaternion=[.5,.5,-.5,.5])])

    def test_cached_tcp_equals_full_tree_for_rotations_slides_and_fixed_frames(self):
        packet=self.packet();kin=Kinematics(packet);rng=np.random.default_rng(3)
        for _ in range(200):
            q=dict(arm=float(rng.uniform(-3,3)),slide=float(rng.uniform(-.1,.1)),unrelated=float(rng.uniform(-3,3)))
            reference=kin.frames(q)[3]@local_pose(packet['sites'][0])
            np.testing.assert_array_equal(kin.tcp(q),reference)
        self.assertEqual(len(kin._tcp_chain),3)

    def test_results_do_not_alias_cached_matrices_and_new_transfer_rebuilds_cache(self):
        packet=self.packet();kin=Kinematics(packet);q=dict(arm=.3,slide=.02,unrelated=.5)
        first=kin.tcp(q);expected=first.copy();first[:]=999
        np.testing.assert_array_equal(kin.tcp(q),expected)
        changed=copy.deepcopy(packet);changed['sites'][0]['position'][0]+=.1
        new=Kinematics(changed)
        np.testing.assert_array_equal(new.tcp(q),new.frames(q)[3]@local_pose(changed['sites'][0]))
        self.assertGreater(float(np.linalg.norm(new.tcp(q)-expected)),.09)

    def test_full_frame_api_remains_available_without_a_tcp_site(self):
        packet=self.packet();packet['sites']=[];kin=Kinematics(packet)
        self.assertEqual(len(kin.frames(dict(arm=0.,slide=0.,unrelated=0.))),5)
        with self.assertRaises(KeyError):kin.tcp({})


if __name__=='__main__':unittest.main()
