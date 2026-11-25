import importlib.util
from pathlib import Path
import unittest

path=Path(__file__).resolve().parents[1]/'scripts/simulation/isaac_rl_worker.py'
spec=importlib.util.spec_from_file_location('isaac_worker_options',path)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class PhysicsStepOptionsTests(unittest.TestCase):
    def test_backend_validation_requires_native_gpu_solver_evidence(self):
        active=dict(gpu_mem_heap_solver=1024,gpu_mem_heap_simulation_articulation=512)
        module.validate_physics_backend('gpu',True,'GPU',active)
        module.validate_physics_backend('cpu',False,'MBP',{})
        for args in [('gpu',False,'GPU',active),('gpu',True,'MBP',active),('gpu',True,'GPU',{}),
                     ('gpu',True,'GPU',dict(gpu_mem_heap_solver=1024)),('cpu',False,'MBP',active)]:
            with self.subTest(args=args),self.assertRaises(RuntimeError):module.validate_physics_backend(*args)
        with self.assertRaises(ValueError):module.validate_physics_backend('other',False,'MBP',{})

    def test_explicit_counts_preserve_control_period_and_legacy_default(self):
        self.assertEqual(module.resolve_physics_dt(),.0002)
        self.assertEqual(module.resolve_physics_dt(.0001),.0001)
        for count in (5,20,100,500):
            self.assertAlmostEqual(module.resolve_physics_dt(substeps=count)*count,.1)

    def test_ambiguous_and_invalid_options_are_rejected(self):
        for args in [dict(dt=.001,substeps=20),dict(dt=.003),dict(dt=0),dict(dt=float('nan')),
                     dict(dt=float('inf')),dict(dt=.05),dict(substeps=7),dict(substeps=20.)]:
            with self.assertRaises(ValueError):module.resolve_physics_dt(**args)


if __name__=='__main__':unittest.main()
