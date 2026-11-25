import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'omi_proj/src'))
try:
    from omi_hil_rl.training.isaac_client import make_contract
except ImportError:
    make_contract = None


@unittest.skipIf(make_contract is None, 'optional numpy / OMI client required')
class NativeContractTests(unittest.TestCase):
    def test_native_contract_is_distinct_and_legacy_default_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp);source = root/'transfer.json';source.write_text('{}')
            metadata = dict(transfer_sha256=hashlib.sha256(source.read_bytes()).hexdigest(), rendered=True,
                projection={}, wrist_roi=[], wrist_sampling='test', physics_dt=.005, current_assets=[],
                execution_config=dict(max_steps=900, teacher_min_step_mm=.05, target_overtravel_mm=.1))
            legacy = make_contract(root, metadata, 900)
            self.assertEqual(legacy['action_contract'], 'isaac-world-tcp-normalized-delta-dls-servo-v1')
            metadata['action_contract'] = 'isaac-world-tcp-normalized-delta-tianji-servo-v1'
            metadata['execution_config'] = dict(metadata['execution_config'], ik_backend=dict(
                version='tianji-ccs-left-world-v1', source_sha256={'libKine.so':'fixture-hash'}))
            native = make_contract(root, metadata, 900)
            self.assertNotEqual(native['action_contract'], legacy['action_contract'])
            self.assertNotEqual(native['execution_config'], legacy['execution_config'])
            self.assertEqual(json.loads(json.dumps(native))['execution_config']['ik_backend']['source_sha256'],
                             {'libKine.so':'fixture-hash'})


if __name__ == '__main__':unittest.main()
