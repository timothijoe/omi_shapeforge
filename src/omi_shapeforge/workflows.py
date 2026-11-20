"""Workflow-specific inputs and commands around the shared process runner."""
import os
from pathlib import Path
import uuid
import xml.etree.ElementTree as ET

from .runner import (ROOT, ProcessPlan, file_record, now, run_task, source_record, write_json)

INSPECTOR = ROOT / 'scripts/validation/inspect_outputs.py'


def scene_files(scene):
    """Resolve the includes and mesh/texture/height-field files used by MJCF."""
    visited = set()

    def visit(path):
        path = Path(path).resolve(strict=True)
        if path in visited:
            return
        visited.add(path)
        tree = ET.parse(path).getroot()
        compiler = tree.find('compiler')
        settings = compiler.attrib if compiler is not None else {}
        for element in tree.iter():
            filename = element.get('file')
            if not filename:
                continue
            if element.tag == 'include':
                visit(path.parent / filename)
                continue
            directory = settings.get('assetdir', '')
            if element.tag == 'mesh':
                directory = settings.get('meshdir', directory)
            elif element.tag == 'texture':
                directory = settings.get('texturedir', directory)
            dependency = (path.parent / directory / filename).resolve(strict=True)
            visited.add(dependency)

    visit(scene)
    return sorted(visited)


def launch(config, workflow, output=None, scene=None, steps=240):
    from .workspace import backend_environment
    if workflow == 'simulation.mujoco' and (type(steps) is not int or steps <= 0):
        raise ValueError('steps must be a positive integer')
    if output is None:
        label = now().replace(':', '').replace('+0000', 'Z') + '_' + uuid.uuid4().hex[:8]
        output = Path(config['storage']['run_directory']) / (label + '_' + workflow.replace('.', '_'))

    def prepare(output, record):
        record['sources'] = [source_record(ROOT, ROOT / 'src/omi_shapeforge/runner.py')]
        record['inputs'] = [file_record('inspector_source', INSPECTOR, 'python')]
        record['limitations'] = ['Existing environments and compiled extensions; not a clean build validation.']
        if workflow.startswith('smoke.'):
            name = workflow.split('.')[1]
            backend = config['backends'][name]
            repo = Path(backend['repository'])
            record['sources'].append(source_record(repo, backend['entrypoint']))
            env = backend_environment(config, name)
            sample = repo / 'assets' if name == 'stereo' else repo.parent / 'FoundationStereo/assets'
            left, right = sample / 'left.png', sample / 'right.png'
            record['inputs'] += [file_record('left', left, 'png'), file_record('right', right, 'png')]
            command = [backend['python'], backend['entrypoint'], '--output', str(output / 'backend'),
                       '--left', str(left), '--right', str(right)]
            if name == 'stereo':
                checkpoint = Path(backend['checkpoint'])
                record['inputs'] += [file_record('intrinsics', sample / 'K.txt', 'text'),
                                     file_record('checkpoint', checkpoint),
                                     file_record('model_config', checkpoint.parent / 'cfg.yaml', 'yaml')]
                command += ['--checkpoint', str(checkpoint), '--intrinsics', str(sample / 'K.txt'),
                            '--scale', '1', '--iterations', '32', '--z-far', '10']
                record['parameters'] = {'iterations': 32, 'scale': 1.0, 'z_far': 10.0}
                record['limitations'].append('Official sample, not raw optical-module reconstruction or depth truth.')
            else:
                record['inputs'] += [file_record('loftr_checkpoint', repo / 'BundleTrack/LoFTR/weights/outdoor_ds.ckpt'),
                                     file_record('bundletrack_config', repo / 'BundleTrack/config_ho3d.yml', 'yaml')]
                record['parameters'] = {'image_width': 640, 'image_height': 448}
                record['limitations'].append('Component checks, not full video tracking or mesh reconstruction.')
            cwd = str(repo)
            python = backend['python']
        else:
            backend = config['simulations']['mujoco']
            python = backend['python']
            scene_path = Path(scene or backend['scene']).expanduser().resolve(strict=True)
            dependencies = [file_record(f'scene_file_{i}', path) for i, path in enumerate(scene_files(scene_path))]
            write_json(output / 'inputs.json', {'scene': str(scene_path), 'files': dependencies})
            record['inputs'] += [file_record('scene', scene_path, 'mjcf', 'm', 'mjcf_world'),
                                 file_record('scene_dependencies', output / 'inputs.json', 'json')]
            env = dict(os.environ)
            for key in ('PYTHONHOME', 'PYTHONPATH'):
                env.pop(key, None)
            env.update(VIRTUAL_ENV=backend['environment'], PYTHONNOUSERSITE='1',
                       MUJOCO_GL='egl', PYTHONUNBUFFERED='1')
            record['sources'].append(source_record(ROOT, backend['entrypoint']))
            record['parameters'] = {'steps': steps, 'renderer': 'egl'}
            record['limitations'] += ['Bounding-box collision, assumed mass/friction; physical accuracy unvalidated.',
                                      'max(abs(qvel)) mixes linear and angular velocity units.']
            cwd = str(ROOT)
            command = [python, backend['entrypoint'], '--scene', str(scene_path),
                       '--steps', str(steps), '--output', str(output / 'backend')]
        inspection = [python, str(INSPECTOR), '--manifest', str(output / 'run_manifest.json')]
        return ProcessPlan(command, cwd, env, inspection)

    return run_task(workflow, output, prepare)
