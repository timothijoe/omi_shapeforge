"""Exercise real subprocess transport and evidence failures without GPU dependencies."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
from tempfile import TemporaryDirectory
import time
import unittest

from omi_shapeforge.runner import (ProcessPlan, ROOT, file_record, passed, read_json,
                                    run_task, source_record)
from omi_shapeforge.workflows import scene_files


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory(prefix='runner evidence ')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.input = self.root / 'input.txt'
        self.input.write_text('original input')
        self.profile = read_json(ROOT / 'contracts/v1/profiles.json')['profiles']['smoke.bundlesdf']

    def run_case(self, mutate='', status=None, inspector_exit=0, python=None):
        output = self.root / 'run'
        report_status = status or self.profile['report_status']
        backend = ('from pathlib import Path; import json; '
                   f'p=Path({str(output / "backend")!r}); p.mkdir(); '
                   f'(p/"report.json").write_text(json.dumps({{"status":{report_status!r}}})); '
                   '(p/"loftr_matches.npy").write_bytes(b"test array transport"); '
                   '(p/"loftr_matches.jpg").write_bytes(b"test image transport"); ' + mutate)
        result = {'valid': True, 'accepted': True, 'content': 'Fixture inspector',
                  'expected': 'Transport fixture', 'observed': 'Fixture outputs', 'versions': {'python': 'fixture'}}
        inspection = ('from pathlib import Path; '
                      f'Path({str(output / "backend/inspection.json")!r}).write_text({json.dumps(result)!r}); '
                      f'raise SystemExit({inspector_exit})')

        def prepare(path, record):
            record['inputs'] = [file_record(key, self.input) for key in self.profile['required_inputs']]
            record['sources'] = [source_record(ROOT, Path(__file__))]
            return ProcessPlan([python or sys.executable, '-c', backend], str(self.root), dict(os.environ),
                               [sys.executable, '-c', inspection])

        return run_task('smoke.bundlesdf', output, prepare)

    def test_success_has_three_independent_verdicts(self):
        result = self.run_case()
        self.assertTrue(passed(result))
        self.assertEqual(result['schema_version'], 1)
        self.assertTrue((self.root / 'run/backend/inspection.json').is_file())
        self.assertFalse(list((self.root / 'run').glob('*.tmp')))

    def test_input_change_cannot_pass(self):
        result = self.run_case(f'Path({str(self.input)!r}).write_text("changed")')
        self.assertEqual(result['execution']['state'], 'succeeded')
        self.assertEqual(result['validation']['status'], 'failed')
        self.assertIn('File changed', result['validation']['checks'][-1]['observed'])

    def test_wrong_report_status_cannot_pass(self):
        result = self.run_case(status='passed_unrelated_workflow')
        self.assertEqual(result['validation']['status'], 'failed')

    def test_inspector_failure_does_not_rewrite_backend_exit(self):
        result = self.run_case(inspector_exit=9)
        self.assertEqual(result['execution']['returncode'], 0)
        self.assertEqual(result['validation']['status'], 'failed')
        self.assertEqual(result['acceptance']['status'], 'not_evaluated')

    def test_missing_interpreter_has_terminal_manifest(self):
        result = self.run_case(python=str(self.root / 'missing interpreter'))
        self.assertEqual(result['execution']['state'], 'failed')
        self.assertIsNone(result['execution']['returncode'])
        self.assertIsNotNone(result['finished_utc'])
        self.assertEqual(result, read_json(self.root / 'run/run_manifest.json'))

    def test_symlink_escape_is_rejected(self):
        result = self.run_case('(p/"loftr_matches.jpg").unlink(); '
                               f'(p/"loftr_matches.jpg").symlink_to({str(self.input)!r})')
        self.assertEqual(result['validation']['status'], 'failed')
        self.assertIn('escapes run directory', result['validation']['checks'][-1]['observed'])
        self.assertEqual(self.input.read_text(), 'original input')

    def test_duplicate_and_nonfinite_json_are_rejected(self):
        for text in ('{"a":1,"a":2}', '{"a":NaN}', '{"a":Infinity}'):
            self.input.write_text(text)
            with self.assertRaises(ValueError):
                read_json(self.input)

    def test_scene_includes_and_meshes_are_fingerprinted(self):
        (self.root / 'part.obj').write_text('v 0 0 0')
        child = self.root / 'child.xml'
        child.write_text('<mujoco><asset><mesh file="part.obj"/></asset></mujoco>')
        scene = self.root / 'scene.xml'
        scene.write_text('<mujoco><include file="child.xml"/></mujoco>')
        self.assertEqual(set(scene_files(scene)), {scene, child, self.root / 'part.obj'})

    @unittest.skipUnless(os.name == 'posix', 'Process-group interruption uses POSIX signals')
    def test_interrupt_stops_child_process_and_saves_cancelled_record(self):
        marker = self.root / 'child.pid'
        output = self.root / 'interrupted'
        child = f'import os,time; from pathlib import Path; Path({str(marker)!r}).write_text(str(os.getpid())); time.sleep(60)'
        script = ('import os,sys; from omi_shapeforge.runner import *\n'
                  'def prepare(output, record):\n'
                  f' return ProcessPlan([sys.executable,"-c",{child!r}],{str(self.root)!r},dict(os.environ),[])\n'
                  'try:\n'
                  f' run_task("smoke.bundlesdf",{str(output)!r},prepare)\n'
                  'except RunCancelled: pass\n')
        env = dict(os.environ, PYTHONPATH=str(ROOT / 'src'))
        controller = subprocess.Popen([sys.executable, '-c', script], env=env,
                                      stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        try:
            for _ in range(200):
                if marker.exists():
                    break
                if controller.poll() is not None:
                    self.fail(controller.stderr.read().decode())
                time.sleep(.01)
            self.assertTrue(marker.exists(), 'Child failed to start')
            controller.send_signal(signal.SIGINT)
            controller.communicate(timeout=12)
            record = read_json(output / 'run_manifest.json')
            self.assertEqual(record['execution']['state'], 'cancelled')
            self.assertIsNotNone(record['finished_utc'])
            with self.assertRaises(ProcessLookupError):
                os.kill(int(marker.read_text()), 0)
        finally:
            if controller.poll() is None:
                controller.kill()
                controller.communicate()


if __name__ == '__main__':
    unittest.main()
