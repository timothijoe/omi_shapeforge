"""Verify experiment failure reporting and preservation of existing results."""
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

from omi_shapeforge.workspace import load_config, run_smoke


class RunSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory(prefix='omi shapeforge test ')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.repo = self.root / 'backend with spaces'
        self.repo.mkdir()
        self.script = self.repo / 'entry.py'
        self.checkpoint = self.root / 'model.pth'
        self.checkpoint.touch()
        self.config = {
            '_file': str(self.root / 'workspace.toml'),
            'storage': {'runtime_root': str(self.root / 'runtime'),
                        'run_directory': str(self.root / 'runs')},
            'backends': {'stereo': {
                'repository': str(self.repo), 'environment': str(Path(sys.executable).parent.parent),
                'python': sys.executable, 'entrypoint': str(self.script),
                'checkpoint': str(self.checkpoint),
            }},
        }

    def test_existing_output_is_preserved(self):
        self.script.write_text('raise SystemExit(0)\n')
        output = self.root / 'existing result'
        output.mkdir()
        sentinel = output / 'report.json'
        sentinel.write_text('original evidence')
        with self.assertRaises(FileExistsError):
            run_smoke(self.config, 'stereo', output)
        self.assertEqual(sentinel.read_text(), 'original evidence')
        self.assertFalse((output / 'run_manifest.json').exists())

    def test_backend_failure_is_recorded(self):
        self.script.write_text('print("backend failure"); raise SystemExit(7)\n')
        output = self.root / 'failed result'
        result = run_smoke(self.config, 'stereo', output)
        recorded = json.loads((output / 'run_manifest.json').read_text())
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(recorded['returncode'], 7)
        self.assertIn('finished_utc', recorded)
        self.assertIn('backend failure', (output / 'run.log').read_text())

    def test_zero_exit_without_report_cannot_pass(self):
        self.script.write_text('print("no result produced")\n')
        output = self.root / 'missing report'
        with self.assertRaises(FileNotFoundError):
            run_smoke(self.config, 'stereo', output)
        recorded = json.loads((output / 'run_manifest.json').read_text())
        self.assertEqual(recorded['status'], 'failed')
        self.assertIn('FileNotFoundError', recorded['error'])


class ConfigTests(unittest.TestCase):
    def test_paths_are_relative_to_config_and_launcher_is_not_dereferenced(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_file = root / 'workspace.toml'
            config_file.write_text('''
[storage]
runtime_root = "runtime with spaces"
run_directory = "runs"
[backends.stereo]
repository = "stereo"
environment = "venv"
entrypoint = "entry.py"
checkpoint = "model.pth"
[backends.bundlesdf]
repository = "bundlesdf"
environment = "venv"
entrypoint = "entry.py"
cuda_home = "cuda"
''')
            (root / 'venv/bin').mkdir(parents=True)
            (root / 'venv/bin/python').symlink_to(sys.executable)
            result = load_config(config_file)
            self.assertEqual(result['storage']['runtime_root'], str(root / 'runtime with spaces'))
            self.assertEqual(result['backends']['stereo']['python'], str(root / 'venv/bin/python'))


if __name__ == '__main__':
    unittest.main()
