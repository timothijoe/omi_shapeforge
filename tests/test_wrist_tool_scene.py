"""Optional integration checks for camera attachment and visible jaw kinematics."""
import importlib.util
import os
import unittest

SCENE=os.environ.get('OMI_WRIST_TOOL_SCENE')
AVAILABLE=all(importlib.util.find_spec(x) for x in ('numpy','mujoco','gymnasium'))
if AVAILABLE:
    import numpy as np
    import mujoco
    from omi_shapeforge.sim.contact_env import ContactInsertionEnv


@unittest.skipUnless(AVAILABLE and SCENE,'mounted wrist-tool scene required')
class WristToolSceneTests(unittest.TestCase):
    def test_optical_origin_and_policy_camera_images(self):
        env=ContactInsertionEnv(SCENE)
        try:
            obs,_=env.reset(seed=7,options={'joint_offset':np.zeros(7)})
            tcp=env.model.body('TCP_Link_L').id;R=env.data.xmat[tcp].reshape(3,3)
            cam=env.model.camera('wrist_rgb').id
            local=R.T@(env.data.cam_xpos[cam]-env.data.xpos[tcp])
            np.testing.assert_allclose(local,env.manifest['cameras']['wrist_rgb']['optical_position_m'],atol=1e-10)
            for name,key in [('head_rgb','rgb'),('wrist_rgb','wrist_rgb')]:
                im=env.render_camera(name);np.testing.assert_array_equal(im.transpose(2,0,1),obs[key][-1])
                ids=env.render_camera(name,segmentation=True)[:,:,0]
                for prefix in ('sim_module_','sim_socket_'):
                    valid=[i for i in range(env.model.ngeom) if env.model.geom(i).name.startswith(prefix)]
                    self.assertGreater(np.isin(ids,valid).sum(),0,(name,prefix))
            self.assertFalse(obs['state'].any() or obs['tactile'].any())
        finally:env.close()

    def test_jaw_motion_closes_symmetrically_without_moving_camera(self):
        env=ContactInsertionEnv(SCENE)
        try:
            env.reset(seed=7,options={'joint_offset':np.zeros(7)})
            tcp=env.model.body('TCP_Link_L').id;R=env.data.xmat[tcp].reshape(3,3)
            ids=[env.model.body(name).id for name in ['Arm_L10_Link','Arm_L11_Link']]
            initial=[env.data.xpos[i].copy() for i in ids]
            cam=env.model.camera('wrist_rgb').id;camera_start=env.data.cam_xpos[cam].copy()
            for name in ['Arm_L10_Joint','Arm_L11_Joint']:
                q=env.model.jnt_qposadr[env.model.joint(name).id];env.data.qpos[q]+=.001
            mujoco.mj_forward(env.model,env.data)
            shifts=[R.T@(env.data.xpos[i]-p) for i,p in zip(ids,initial)]
            np.testing.assert_allclose(shifts,[[0,.001,0],[0,-.001,0]],atol=3e-8)
            np.testing.assert_allclose(env.data.cam_xpos[cam],camera_start,atol=1e-12)
        finally:env.close()
