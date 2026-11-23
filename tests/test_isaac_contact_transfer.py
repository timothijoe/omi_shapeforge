"""Cross-check independent FK against the source engine on nontrivial chains."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

try:
    import mujoco
    import numpy as np
    from omi_shapeforge.sim.isaac_contact_kinematics import Kinematics
except ImportError:
    mujoco=None


@unittest.skipIf(mujoco is None,'requires optional simulation dependencies')
class TransferTests(unittest.TestCase):
    def test_non_axis_aligned_fixed_and_moving_chain(self):
        path=Path(__file__).parents[1]/'scripts/simulation/export_isaac_contact.py'
        spec=importlib.util.spec_from_file_location('contact_export',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        xml='''<mujoco><compiler angle="radian"/><worldbody>
          <body name="base" pos=".2 -.3 .4" euler=".3 -.4 .2">
            <body name="arm" pos=".1 .2 .3" euler="-.2 .1 .5">
              <joint name="hinge" type="hinge" axis="1 2 3" pos=".02 -.01 .03"/>
              <geom type="sphere" size=".03" mass="1"/>
              <body name="fixed" pos=".02 .03 .04" euler=".4 .2 -.1">
                <body name="slider" pos="-.01 .02 .03">
                  <joint name="slide" type="slide" axis="2 -1 3"/>
                  <geom type="sphere" size=".02" mass=".1"/>
                  <site name="urdf_tcp_L" pos=".03 .04 -.01" euler=".2 .3 .1"/>
                </body>
              </body>
            </body>
          </body></worldbody></mujoco>'''
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'scene.xml';source.write_text(xml)
            module.export(source,root/'packet')
            packet=json.loads((root/'packet/transfer.json').read_text())
            kin=Kinematics(packet);m=mujoco.MjModel.from_xml_path(str(source));d=mujoco.MjData(m)
            for angle,slide in [(0.,0.),(.5,.012),(-.7,-.006)]:
                d.qpos[:]=[angle,slide];mujoco.mj_forward(m,d)
                result=kin.tcp(dict(hinge=angle,slide=slide))
                np.testing.assert_allclose(result[:3,3],d.site_xpos[0],atol=1e-12)
                np.testing.assert_allclose(result[:3,:3],d.site_xmat[0].reshape(3,3),atol=1e-12)
            with self.assertRaises(FileExistsError):module.export(source,root/'packet')


if __name__=='__main__':unittest.main()
