import unittest
try:
    import numpy as np
    from omi_shapeforge.sim.wrist_fisheye import FACES,maps,reproject,inverse_theta
except ImportError:
    np=None


@unittest.skipIf(np is None,'optional numpy required')
class FisheyeTests(unittest.TestCase):
    def test_distorted_radius_round_trip(self):
        theta=np.linspace(0,1.8,100);d=np.array([-.02727618848,-.0038809502,-.0024510944,.0027821863]);t=theta**2
        radius=theta*(1+d[0]*t+d[1]*t**2+d[2]*t**3+d[3]*t**4)
        np.testing.assert_allclose(inverse_theta(radius,d),theta,atol=1e-12)
    def test_cubemap_handedness_and_direction_sampling(self):
        for r in FACES:
            np.testing.assert_allclose(r.T@r,np.eye(3));self.assertAlmostEqual(np.linalg.det(r),1.)
        N=128;yy,xx=np.indices((N,N));local=np.stack([(xx-(N-1)/2)/(N/2),(yy-(N-1)/2)/(N/2),np.ones((N,N))],axis=-1)
        local/=np.linalg.norm(local,axis=-1,keepdims=True)
        faces=[np.rint((local@r.T+1)*127.5).astype(np.uint8) for r in FACES]
        projection=dict(K=[[55,0,80],[0,56,45],[0,0,1]],D=[0,0,0,0],image_size=[160,90])
        image=reproject(faces,maps(projection,N));y,x=np.indices((90,160));xn=(x-80)/55;yn=(y-45)/56;theta=np.hypot(xn,yn)
        factor=np.sin(theta)/np.maximum(theta,1e-12);direction=np.stack([xn*factor,yn*factor,np.cos(theta)],axis=-1)
        expected=np.rint((direction+1)*127.5).astype(np.uint8)
        self.assertLessEqual(np.max(abs(image.astype(float)-expected)),1.)


if __name__=='__main__':unittest.main()
