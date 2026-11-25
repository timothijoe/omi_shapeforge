import unittest
try:
    import numpy as np
    from omi_shapeforge.sim.wrist_wrench import WrenchAccumulator
except ImportError:
    np=None


@unittest.skipIf(np is None,'optional numpy required')
class WrenchTests(unittest.TestCase):
    def test_collider_swap_preserves_force_and_moment(self):
        a=WrenchAccumulator();b=WrenchAccumulator()
        a.add([0,2,0],[1,0,0],True);b.add([0,2,0],[-1,0,0],False)
        np.testing.assert_allclose(a.measure(np.eye(4),.1),[10,0,0,0,0,-20])
        np.testing.assert_allclose(a.measure(np.eye(4),.1),b.measure(np.eye(4),.1))

    def test_origin_shift_rotation_and_opposed_forces(self):
        a=WrenchAccumulator();a.add([0,2,0],[1,0,0])
        sensor=np.eye(4);sensor[:3,3]=[0,2,0];sensor[:3,:3]=[[0,-1,0],[1,0,0],[0,0,1]]
        np.testing.assert_allclose(a.measure(sensor,.1),[0,-10,0,0,0,0])
        a.add([0,-2,0],[-1,0,0])
        np.testing.assert_allclose(a.measure(np.eye(4),.1),[0,0,0,0,0,-40])
        a.clear();np.testing.assert_array_equal(a.measure(sensor,.1),np.zeros(6))

    def test_nonfinite_rejected(self):
        a=WrenchAccumulator()
        with self.assertRaises(ValueError):a.add([0,0,0],[float('nan'),0,0])
        with self.assertRaises(ValueError):a.measure(np.eye(4),0)
