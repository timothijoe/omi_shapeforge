import json
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import unittest

from omi_shapeforge.sim.process_supervisor import OwnedProcess


class ProcessSupervisorTests(unittest.TestCase):
    def test_group_signal_cannot_kill_supervisor_and_native_status_survives(self):
        with tempfile.TemporaryDirectory() as tmp:
            child = OwnedProcess([sys.executable, '-c',
                'import os,signal; os.killpg(0,signal.SIGTERM)'], directory=tmp, name='child')
            self.assertEqual(child.wait(10), -signal.SIGTERM)
            receipt = json.loads((Path(tmp)/'child_process.json').read_text())
            self.assertEqual(receipt['state'], 'exited')
            self.assertEqual(receipt['returncode'], -signal.SIGTERM)
            self.assertEqual(receipt['pid'], receipt['pgid'])

    def test_timeout_is_recorded_and_process_reaped(self):
        with tempfile.TemporaryDirectory() as tmp:
            child = OwnedProcess([sys.executable, '-c', 'import time; time.sleep(30)'], directory=tmp, name='child')
            with self.assertRaises(subprocess.TimeoutExpired):child.wait(.1)
            receipt = json.loads((Path(tmp)/'child_process.json').read_text())
            self.assertTrue(receipt['timed_out'])
            self.assertTrue(receipt['stop_requested'])
            self.assertIsNotNone(child.poll())

    def test_normal_exit_is_saved_immediately(self):
        with tempfile.TemporaryDirectory() as tmp:
            child = OwnedProcess([sys.executable, '-c', 'print("complete")'], directory=tmp, name='child')
            self.assertEqual(child.wait(10), 0)
            self.assertEqual(json.loads((Path(tmp)/'child_process.json').read_text())['returncode'], 0)


if __name__ == '__main__':unittest.main()
