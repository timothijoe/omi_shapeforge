"""Set TIANJI_SDK_DIR to run the native offline suite; never opens a robot."""
import copy
import os
from pathlib import Path
import unittest
from unittest.mock import patch

try:
    import numpy as np
    from omi_shapeforge.sim.tianji_ik import TianjiIK, IKError, ARM_NAMES, pose_error, rigid
except ImportError:
    np = None


def packet():
    # Independent URDF excerpt, metres and wxyz; not generated from SDK DH.
    poses = [([0, .2005, 1.121], [.7071067811865475, -.7071067811865475, 0, 0]),
        ([0, 0, 0], [.7071052811843601, .707108281185553, 0, 0]),
        ([0, .287, 0], [.7071052811843601, -.707108281185553, 0, 0]),
        ([.018, 0, 0], [-2.59734103282963e-6, 2.5973510328336063e-6, -.7071082811807827, .7071052811795897]),
        ([.018, -.314, 0], [-2.59734103282963e-6, 2.5973510328336063e-6, -.7071082811807827, .7071052811795897]),
        ([0, 0, 0], [.499997999998, .499999999998, -.499999999998, .500001999998]),
        ([0, 0, 0], [.499997999998, .499999999998, -.499999999998, .500001999998]),
        ([0, -.095, 0], [.499997999998, .499999999998, -.499999999998, .500001999998])]
    bodies = [dict(id=0, parent=0, position=[0, 0, 0], quaternion=[1, 0, 0, 0])]
    bodies += [dict(id=i, parent=i-1, position=p, quaternion=r) for i, (p, r) in enumerate(poses, 1)]
    limits = [(-3.1067, 3.1067), (-2.0944, 2.0944), (-3.1067, 3.1067), (-2.5307, 1.0472),
              (-3.1067, 3.1067), (-1.0472, 1.0472), (-1.5708, 1.5708)]
    joints = [dict(name=n, body=i+1, kind=3, axis=[0, 0, 1], position=[0, 0, 0],
                   limits=limits[i], qpos_index=i) for i, n in enumerate(ARM_NAMES)]
    return dict(bodies=bodies, joints=joints, sites=[dict(name='urdf_tcp_L', body=8,
        position=[0, 0, 0], quaternion=[1, 0, 0, 0])],
        initial_qpos=[.7968954353, -.640552137, .0714754983, -1.7313613283, -.8857004549, -.5971272877, 1.0245174681])


@unittest.skipIf(np is None, 'optional numpy required')
class PoseTests(unittest.TestCase):
    def test_malformed_targets_rejected(self):
        for invalid in [np.zeros((4, 4)), np.eye(3), np.eye(4)*float('nan'), np.diag([-1, 1, 1, 1])]:
            with self.assertRaises(ValueError):rigid(invalid)


@unittest.skipUnless(np is not None and os.environ.get('TIANJI_SDK_DIR'), 'optional local Tianji math SDK required')
class NativeIKTests(unittest.TestCase):
    def setUp(self):
        self.p = packet()
        self.k = TianjiIK(self.p, os.environ['TIANJI_SDK_DIR'])

    def test_independent_fk_and_500_targets(self):
        self.assertEqual(self.k.validation['samples'], 66)
        rng = np.random.default_rng(12)
        original = dict(self.k.initial)
        for _ in range(500):
            q = dict(original)
            q.update(zip(ARM_NAMES, self.p['initial_qpos']+rng.uniform(-.04, .04, 7)))
            desired = dict(q)
            desired.update({n:q[n]+rng.uniform(-.001, .001) for n in ARM_NAMES})
            target = self.k.kin.tcp(desired)
            before = dict(q)
            solution = self.k.solve(q, target)
            error = pose_error(self.k.kin.tcp(solution), target)
            self.assertLess(error[0], 1e-5)
            self.assertLess(error[1], 1e-4)
            self.assertEqual(q, before)
        self.assertEqual(self.k.initial, original)
        self.assertNotIn('libMarvinSDK', Path('/proc/self/maps').read_text())

    def test_fixed_world_mount_and_nonidentity_tcp(self):
        self.p['bodies'][1]['position'][0] += .2
        self.p['sites'][0].update(position=[.03, -.02, .04], quaternion=[.5, .5, -.5, .5])
        k = TianjiIK(self.p, os.environ['TIANJI_SDK_DIR'])
        target = k.kin.tcp(k.initial);target[0, 3] += .0002
        solution = k.solve(k.initial, target)
        self.assertLess(pose_error(k.kin.tcp(solution), target)[0], 1e-5)
        # Switching adapters must restore the appropriate global SDK math slot.
        self.k.solve(self.k.initial, self.k.kin.tcp(self.k.initial))

    def test_wrong_axis_or_link_length_fails_startup(self):
        p = copy.deepcopy(self.p);p['joints'][1]['axis'] = [0, 0, -1]
        with self.assertRaises(ValueError):TianjiIK(p, os.environ['TIANJI_SDK_DIR'])
        p = copy.deepcopy(self.p);p['bodies'][3]['position'][1] += .001
        with self.assertRaisesRegex(IKError, 'FK mismatch'):TianjiIK(p, os.environ['TIANJI_SDK_DIR'])

    def test_unreachable_and_invalid_reference(self):
        target = np.eye(4);target[:3, 3] = [10, 10, 10]
        with self.assertRaises(IKError):self.k.solve(self.k.initial, target)
        q = dict(self.k.initial);q[ARM_NAMES[0]] = float('nan')
        with self.assertRaises(IKError):self.k.solve(q, np.eye(4))

    def test_vendor_flags_jump_limits_and_backcheck_are_not_ignored(self):
        target = self.k.kin.tcp(self.k.initial)
        for defect in ['false', 'unreachable', 'limitflag', 'singular', 'nan', 'jointlimit', 'jump', 'residual']:
            def fake(serial, pointer):
                sp = pointer._obj
                for i, n in enumerate(ARM_NAMES):sp.m_Output_RetJoint.data[i] = np.rad2deg(self.k.initial[n])
                if defect == 'unreachable':sp.m_Output_IsOutRange = True
                if defect == 'limitflag':sp.m_Output_IsJntExd = True
                if defect == 'singular':sp.m_Output_IsDeg[3] = True
                if defect == 'nan':sp.m_Output_RetJoint.data[0] = float('nan')
                if defect == 'jointlimit':sp.m_Output_RetJoint.data[0] = 190
                if defect == 'jump':sp.m_Output_RetJoint.data[0] += 10
                if defect == 'residual':sp.m_Output_RetJoint.data[0] += 1
                return defect != 'false'
            with self.subTest(defect=defect), patch.object(self.k.sdk.kine, 'FX_Robot_Kine_IK', fake):
                with self.assertRaises(IKError):self.k.solve(self.k.initial, target)


if __name__ == '__main__':unittest.main()
