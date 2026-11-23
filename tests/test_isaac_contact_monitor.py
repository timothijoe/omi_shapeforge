"""Regress actual probe failures without needing a Kit GUI or PhysX runtime."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

try:
    import numpy
    import scipy
except ImportError:
    numpy = scipy = None


@unittest.skipIf(numpy is None or scipy is None, 'NumPy/SciPy environment required')
class ContactMonitorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pxr = types.ModuleType('pxr')
        pxr.Usd = pxr.UsdGeom = pxr.UsdPhysics = object()
        pxr.PhysicsSchemaTools = types.SimpleNamespace(intToSdfPath=lambda value: value)
        omni = types.ModuleType('omni')
        omni.__path__ = []
        physx = types.ModuleType('omni.physx')
        physx.get_physx_simulation_interface = lambda: types.SimpleNamespace(
            subscribe_contact_report_events=lambda callback: object())
        omni.physx = physx
        path = Path(__file__).resolve().parents[1]/'src/omi_shapeforge/sim/isaac_contact_runtime.py'
        spec = importlib.util.spec_from_file_location('omi_shapeforge.sim._monitor_regression', path)
        module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {'pxr': pxr, 'omni': omni, 'omni.physx': physx}):
            spec.loader.exec_module(module)
        cls.Monitor = module.ContactMonitor

    def contact(self, monitor, first, second, impulse=(0., .001, 0.)):
        header = types.SimpleNamespace(collider0='/World/'+first, collider1='/World/'+second,
                                       num_contact_data=1, contact_data_offset=0)
        point = types.SimpleNamespace(separation=0., impulse=impulse)
        monitor.callback([header], [point])

    def test_new_shoulder_accepts_bottom_and_side_not_only_top(self):
        monitor = self.Monitor(.0002, ['sim_module_smooth_shoulder', 'sim_socket_smooth_'])
        for face in ('bottom', 'left', 'right', 'top'):
            with self.subTest(face=face):
                monitor.clear()
                monitor.start_substep()
                self.contact(monitor, 'sim_module_smooth_shoulder', 'sim_socket_smooth_'+face)
                self.assertTrue(monitor.last['shoulder'])
        monitor.clear()
        self.contact(monitor, 'sim_module_smooth_shaft', 'sim_socket_smooth_bottom')
        self.assertFalse(monitor.last['shoulder'])

    def test_first_contact_before_explicit_substep_initialization(self):
        monitor = self.Monitor(.0002)
        self.contact(monitor, 'sim_module_006_collision_000', 'sim_socket_008_collision_000')
        self.assertAlmostEqual(monitor.last['force_N'], 5.)
        self.assertTrue(monitor.last['shoulder'])

    def test_legacy_pair_and_last_substep_semantics_remain(self):
        monitor = self.Monitor(.0002)
        self.contact(monitor, 'sim_module_006_collision_000', 'sim_socket_008_collision_000')
        monitor.start_substep()
        self.assertFalse(monitor.last['shoulder'])
        self.assertTrue(monitor.shoulder)  # interval history is separate
        self.contact(monitor, 'sim_module_smooth_shoulder', 'sim_socket_smooth_top')
        self.assertFalse(monitor.last['shoulder'])

    def test_control_interval_mean_keeps_short_contact_impulse(self):
        monitor=self.Monitor(.0002)
        monitor.start_substep()
        self.contact(monitor,'sim_module_smooth_shaft','sim_socket_smooth_top')
        monitor.start_substep()  # next physical step has no contact report
        self.assertEqual(monitor.last['force_N'],0.)
        self.assertAlmostEqual(monitor.peak_force,5.)
        self.assertAlmostEqual(monitor.module_impulse/(monitor.sample_count*monitor.dt),2.5)


if __name__ == '__main__':
    unittest.main()
