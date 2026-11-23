import unittest
try:
    import numpy as np
    from omi_shapeforge.sim.isaac_contact_approach import limit_approach
except ImportError:
    np=None


@unittest.skipIf(np is None,'requires optional numpy')
class ApproachTests(unittest.TestCase):
    def test_near_seat_reduces_only_forward_translation(self):
        scale=np.array([.001/np.sqrt(3)]*3+[.01]*3)
        axis=np.array([1.,2.,3.]);axis/=np.linalg.norm(axis)
        action=np.array([.5,.5,.5,.1,-.2,.3])
        out,audit=limit_approach(action,scale,axis,.1,'insert')
        before=action[:3]*scale[:3];after=out[:3]*scale[:3]
        self.assertAlmostEqual(after@axis,.00002,places=10)
        np.testing.assert_allclose(before-axis*(before@axis),after-axis*(after@axis),atol=1e-10)
        np.testing.assert_allclose(out[3:],action[3:])
        self.assertTrue(audit['active'])
    def test_far_approach_and_withdrawal_preserve_action(self):
        a=np.array([.5,0,0,.2,0,0]);scale=np.ones(6)*.001
        for remaining,phase in [(3.,'insert'),(.1,'withdraw')]:
            out,audit=limit_approach(a,scale,[1,0,0],remaining,phase)
            np.testing.assert_allclose(out,a);self.assertFalse(audit['active'])
    def test_backward_recovery_is_not_slowed(self):
        out,_=limit_approach([-.7,0,0,0,0,0],np.ones(6)*.001,[1,0,0],-.1,'insert')
        self.assertAlmostEqual(float(out[0]),-.7,places=6)
    def test_explicit_candidate_minimum_does_not_change_legacy_default(self):
        action=[.8,0,0,.1,0,0];scale=np.ones(6)*.001
        old,_=limit_approach(action,scale,[1,0,0],0.,'insert')
        new,_=limit_approach(action,scale,[1,0,0],0.,'insert',minimum_mm=.05)
        self.assertAlmostEqual(float(old[0]),.01,places=6)
        self.assertAlmostEqual(float(new[0]),.05,places=6)
        self.assertEqual(old[3],new[3])


if __name__=='__main__':unittest.main()
