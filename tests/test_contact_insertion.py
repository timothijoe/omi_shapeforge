"""Optional real asset checks; all source assets are read-only."""
import importlib.util
import json
import os
from pathlib import Path
import unittest

AVAILABLE=all(importlib.util.find_spec(k) for k in ('numpy','mujoco','gymnasium'))
SCENE=os.environ.get('OMI_CONTACT_SCENE')
ASSET=os.environ.get('OMI_CONTACT_ASSET')
if AVAILABLE:
    import mujoco
    import numpy as np
    from omi_shapeforge.sim.contact_env import ContactInsertionEnv


@unittest.skipUnless(AVAILABLE and SCENE,'contact scene and simulation environment required')
class ContactEnvironmentTests(unittest.TestCase):
    def test_timeout_not_success_and_invalid_action_preserves_state(self):
        env=ContactInsertionEnv(SCENE,max_steps=1)
        try:
            obs,info=env.reset(seed=9);before=env.data.qpos.copy();stamp=env.data.time
            self.assertTrue(env.observation_space.contains(obs));self.assertTrue(info['contacts_enabled'])
            with self.assertRaises(ValueError):env.step([float('nan')]*6)
            np.testing.assert_array_equal(before,env.data.qpos);self.assertEqual(stamp,env.data.time)
            _,_,done,truncated,info=env.step(np.zeros(6))
            self.assertFalse(done or info['is_success']);self.assertTrue(truncated)
            with self.assertRaises(RuntimeError):env.begin_withdrawal()
        finally:env.close()

    def test_reset_clears_history_and_preserves_fixed_attachment(self):
        env=ContactInsertionEnv(SCENE)
        try:
            first,_=env.reset(seed=3);env.step(np.zeros(6));second,_=env.reset(seed=3)
            for k in first:np.testing.assert_array_equal(first[k],second[k])
            np.testing.assert_array_equal(second['history_mask'],[0]*9+[1])
            rotation=env.data.site_xmat[env.site].reshape(3,3)
            relative=rotation.T@(env.data.xpos[env.module_id]-env.data.site_xpos[env.site])
            np.testing.assert_allclose(relative,env.manifest['tool_to_module']['position_m'],atol=1e-12)
        finally:env.close()

    @unittest.skipUnless(ASSET,'contact asset required')
    def test_full_allowed_pad_stroke_has_static_clearance(self):
        m=mujoco.MjModel.from_xml_path(str(Path(ASSET)/'scene.xml'));d=mujoco.MjData(m)
        static=[i for i in range(m.ngeom) if m.geom(i).name.startswith('sim_socket_') and '_collision_' in m.geom(i).name]
        for i in range(7):
            joint=m.joint(f'pad_slide_{i}').id;d.qpos[m.jnt_qposadr[joint]]=m.jnt_range[joint,1]
        mujoco.mj_forward(m,d)
        gaps=[]
        for i in range(7):
            g=m.geom(f'pad_contact_{i}').id
            gaps.extend(mujoco.mj_geomDistance(m,d,g,h,.001,np.zeros(6)) for h in static)
        self.assertGreater(min(gaps),.000025)
