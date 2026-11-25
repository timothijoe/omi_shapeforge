import importlib.util
from pathlib import Path
import sys
import unittest
from copy import deepcopy

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('asset_contract_worker',ROOT/'scripts/simulation/isaac_rl_worker.py')
worker=importlib.util.module_from_spec(spec);spec.loader.exec_module(worker)


class AssetContractTests(unittest.TestCase):
    def setUp(self):
        self.legacy={'manifest':{'wrist_tool_asset':'WG-DAIMON-OBS-r10','module_visual_asset':{'asset_id':'OM-001/V4 r08'}}}
        self.updated={'manifest':{'wrist_tool_asset':'WG-DAIMON-LOGO-r15','module_visual_asset':{'asset_id':'OM-001/V4 r08'},
                      'asset_contract':'wva01-gc01-free-grasp-v1','grasp_contract':{'version':'isaac-gc01-free-module-v1'}},
                      'free_bodies':['sim_module']}

    def test_old_and_new_execution_contracts_cannot_be_silently_interchanged(self):
        worker.validate_asset_contract(self.legacy,'legacy-r10')
        worker.validate_asset_contract(self.updated,'wva01-gc01-free-grasp-v1')
        for packet,mode in [(self.legacy,'wva01-gc01-free-grasp-v1'),(self.updated,'legacy-r10')]:
            with self.assertRaises(ValueError):worker.validate_asset_contract(packet,mode)

    def test_new_label_with_old_fixed_topology_is_rejected(self):
        altered=deepcopy(self.updated);altered['free_bodies']=[]
        with self.assertRaises(ValueError):worker.validate_asset_contract(altered,'wva01-gc01-free-grasp-v1')

    def test_wrong_module_and_unknown_contract_are_rejected(self):
        altered=deepcopy(self.updated);altered['manifest']['module_visual_asset']['asset_id']='OM-001/V4 r05'
        with self.assertRaises(ValueError):worker.validate_asset_contract(altered,'wva01-gc01-free-grasp-v1')
        with self.assertRaises(ValueError):worker.validate_asset_contract(self.updated,'unregistered')

    def test_visual_fixture_cannot_be_misrepresented_as_free_contact_grasp(self):
        fixture=deepcopy(self.updated)
        fixture['free_bodies']=[]
        fixture['manifest'].pop('grasp_contract')
        fixture['manifest']['asset_contract']='wva01-closed-reference-fixture-v1'
        fixture['manifest']['grasp_reference']={'scope':'closed pose reference only'}
        worker.validate_asset_contract(fixture,'wva01-closed-reference-fixture-v1')
        with self.assertRaises(ValueError):worker.validate_asset_contract(fixture,'wva01-gc01-free-grasp-v1')


try:
    import numpy as np
    from scipy.spatial.transform import Rotation
except ImportError:
    np=None


@unittest.skipIf(np is None,'optional NumPy/SciPy required')
class FreeModuleServoTests(unittest.TestCase):
    def test_measured_slip_is_compensated_without_moving_the_module_task_goal(self):
        sys.path.insert(0,str(ROOT/'src'))
        from omi_shapeforge.sim.isaac_contact_kinematics import free_module_servo_target,transform
        rng=np.random.default_rng(8821)
        for _ in range(40):
            matrices=[transform(rng.uniform(-1,1,3),Rotation.from_rotvec(rng.normal(0,.2,3)).as_matrix()) for _ in range(4)]
            tcp,actual_relative,goal,nominal=matrices
            module=tcp@actual_relative
            corrected=free_module_servo_target(tcp,module,goal,nominal)
            np.testing.assert_allclose(corrected@actual_relative,goal@nominal,atol=2e-14)

    def test_no_slip_recovers_the_original_tcp_goal(self):
        from omi_shapeforge.sim.isaac_contact_kinematics import free_module_servo_target,transform
        tcp=transform([.2,.3,.4],Rotation.from_euler('xyz',[.1,-.2,.3]).as_matrix())
        nominal=transform([.01,-.02,.24],Rotation.from_euler('xyz',[1.4,.1,.2]).as_matrix())
        goal=transform([.4,.2,.3],np.eye(3))
        np.testing.assert_allclose(free_module_servo_target(tcp,tcp@nominal,goal,nominal),goal,atol=2e-15)

    def test_soft_finger_spin_is_contact_load_bounded_and_releases(self):
        from omi_shapeforge.sim.isaac_contact_kinematics import bounded_contact_spin_torque
        for angle,speed in [(1.,10.),(-1.,-10.),(.003,.01),(-.003,-.01)]:
            torque,limit=bounded_contact_spin_torque(angle,speed,8e-6,2.,2.)
            self.assertLessEqual(abs(torque),.012)
            self.assertAlmostEqual(limit,.012)
        for forces in [(0.,2.),(2.,0.),(0.,0.)]:
            self.assertEqual(bounded_contact_spin_torque(1.,10.,8e-6,*forces),(0.,0.))

    def test_spin_contact_can_yield_under_load_and_is_not_an_angle_lock(self):
        from omi_shapeforge.sim.isaac_contact_kinematics import bounded_contact_spin_torque
        theta=omega=0.;dt=.0002;inertia=8e-6
        for _ in range(300):
            torque,limit=bounded_contact_spin_torque(theta,omega,inertia,2.,2.)
            omega+=dt*(.03+torque)/inertia  # external torque exceeds contact's .012 Nm limit
            theta+=dt*omega
        self.assertGreater(theta,.1)


if __name__=='__main__':unittest.main()
