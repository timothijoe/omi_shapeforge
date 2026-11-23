import json
from pathlib import Path
import unittest
try:
    import mujoco
    import numpy as np
except ImportError:
    mujoco=None

ROOT=Path('/data/omi_runtime/runs/wg_r10_om_r08_isaac_20261122')
SCENE=ROOT/'integration/robot_scene/scene.xml'


@unittest.skipIf(mujoco is None or not SCENE.exists(),'optional mounted WG-r10 scene required')
class WristBundleMountTests(unittest.TestCase):
    def setUp(self):
        self.m=mujoco.MjModel.from_xml_path(str(SCENE));self.d=mujoco.MjData(self.m)
        self.manifest=json.loads(SCENE.with_name('robot_manifest.json').read_text())
        self.kit=json.loads((ROOT/'inputs/tool/asset_manifest.json').read_text())
        self.d.qpos[:]=self.manifest['initial_qpos'];mujoco.mj_forward(self.m,self.d)
    def test_parts_materials_and_camera_parent(self):
        self.assertEqual(len(self.manifest['wrist_tool_bindings']),49)
        for i,part in enumerate(self.kit['parts']):
            geom=self.m.geom(f'wrist_tool_{i:03d}')
            if part['component'] in ('base','camera','camera_mount'):
                self.assertEqual(self.m.body(int(geom.bodyid[0])).name,'TCP_Link_L')
            np.testing.assert_allclose(geom.rgba,part.get('mujoco_rgba',part['color']),atol=1e-7)
        camera=self.m.camera('wrist_rgb');self.assertEqual(self.m.body(int(camera.bodyid[0])).name,'TCP_Link_L')
        visuals=[self.m.geom(i).name for i in range(self.m.ngeom) if self.m.geom_group[i]<3 and self.m.geom(i).name.startswith('sim_module_')]
        self.assertEqual(len(visuals),17);self.assertNotIn('sim_module_008_visual',visuals);self.assertNotIn('sim_module_010_visual',visuals)
        self.assertIn('sim_module_u_handle_visual',visuals)
    def test_jaws_move_without_moving_camera(self):
        cam=self.m.camera('wrist_rgb').id;before=self.d.cam_xpos[cam].copy();rotation=self.d.cam_xmat[cam].copy()
        for name in ('Arm_L10_Joint','Arm_L11_Joint'):self.d.joint(name).qpos[0]=.0193
        mujoco.mj_forward(self.m,self.d)
        np.testing.assert_allclose(self.d.cam_xpos[cam],before,atol=1e-12)
        np.testing.assert_allclose(self.d.cam_xmat[cam],rotation,atol=1e-12)
    def test_parked_right_arm_does_not_change_active_side(self):
        path=Path('/data/omi_runtime/runs/right_arm_park_20261122/robot_scene/robot_manifest.json')
        if not path.exists():self.skipTest('parked-arm candidate unavailable')
        parked=json.loads(path.read_text());before=self.d.xpos.copy();camera=self.d.cam_xmat.copy()
        self.d.qpos[:]=parked['initial_qpos'];mujoco.mj_forward(self.m,self.d)
        for body in ['TCP_Link_L','sim_module']:
            i=self.m.body(body).id;np.testing.assert_array_equal(self.d.xpos[i],before[i])
        np.testing.assert_array_equal(self.d.cam_xmat,camera)
        heights=[self.d.xpos[self.m.body(n).id,2] for n in ['Link1_R','Link3_R','Link5_R','TCP_Link_R']]
        self.assertLess(np.ptp(heights),1e-5)


if __name__=='__main__':unittest.main()
