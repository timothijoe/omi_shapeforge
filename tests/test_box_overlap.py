import unittest
try:
    import numpy as np
    from omi_shapeforge.sim.box_overlap import box_overlap_mm
except ImportError:
    np=None


@unittest.skipIf(np is None,'optional numpy required')
class BoxOverlapTests(unittest.TestCase):
    def test_touch_separation_and_known_overlap(self):
        r=np.eye(3);half=np.array([.001]*3);origin=np.zeros(3)
        self.assertEqual(box_overlap_mm(origin,r,half,np.array([.002,0,0]),r,half),0.)
        self.assertEqual(box_overlap_mm(origin,r,half,np.array([.003,0,0]),r,half),0.)
        self.assertAlmostEqual(box_overlap_mm(origin,r,half,np.array([.0019,0,0]),r,half),.1)

    def test_rotated_corner_separation(self):
        r=np.array([[2**-.5,-2**-.5,0],[2**-.5,2**-.5,0],[0,0,1.]])
        h=np.array([.001]*3)
        self.assertEqual(box_overlap_mm(np.zeros(3),np.eye(3),h,np.array([.0025,0,0]),r,h),0.)
        self.assertGreater(box_overlap_mm(np.zeros(3),np.eye(3),h,np.array([.0023,0,0]),r,h),0.)


if __name__=='__main__':unittest.main()
