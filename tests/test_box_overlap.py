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

    def test_batched_axes_match_scalar_sat_for_random_and_near_parallel_boxes(self):
        def scalar(ca,a,ha,cb,b,hb):
            axes=[a[:,i] for i in range(3)]+[b[:,i] for i in range(3)]
            axes += [np.cross(a[:,i],b[:,j]) for i in range(3) for j in range(3)]
            axes=np.array([v/np.linalg.norm(v) for v in axes if np.linalg.norm(v)>1e-9])
            overlap=np.abs(axes@a)@ha+np.abs(axes@b)@hb-np.abs(axes@(cb-ca))
            return float(max(0.,np.min(overlap))*1000)
        rng=np.random.default_rng(24)
        for i in range(2000):
            a=np.linalg.qr(rng.normal(size=(3,3)))[0]
            if i%2:b=np.linalg.qr(rng.normal(size=(3,3)))[0]
            else:
                angle=[0.,1e-12,1e-9,1e-7][i//2%4];c,s=np.cos(angle),np.sin(angle)
                b=a@np.array([[c,-s,0],[s,c,0],[0,0,1]])
            ca=rng.uniform(-.1,.1,3);cb=ca+rng.uniform(-.004,.004,3)
            ha=rng.uniform(.001,.01,3);hb=rng.uniform(.001,.01,3)
            self.assertAlmostEqual(box_overlap_mm(ca,a,ha,cb,b,hb),scalar(ca,a,ha,cb,b,hb),places=10)


if __name__=='__main__':unittest.main()
