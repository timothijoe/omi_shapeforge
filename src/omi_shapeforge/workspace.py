"""Configure external backends and preserve provenance for each experiment."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tomllib

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def resolve_path(base, value):
    return (base / Path(os.path.expandvars(value)).expanduser()).resolve()


def load_config(path=None):
    path = Path(path or os.environ.get('OMI_SHAPEFORGE_CONFIG') or
                PROJECT_ROOT / 'configs/workspace.toml').resolve()
    with path.open('rb') as handle:
        config = tomllib.load(handle)
    config['_file'] = str(path)
    for key in ('runtime_root', 'run_directory'):
        config['storage'][key] = str(resolve_path(path.parent, config['storage'][key]))
    for name in ('stereo', 'bundlesdf'):
        backend = config['backends'][name]
        for key in ('repository', 'environment', 'checkpoint', 'cuda_home'):
            if key in backend:
                backend[key] = str(resolve_path(path.parent, backend[key]))
        backend['python'] = str(Path(backend['environment']) / 'bin/python')
        # Preserve the venv launcher path rather than resolving its interpreter symlink.
        entry = (Path(backend['repository']) / backend['entrypoint']).resolve()
        if not entry.is_relative_to(Path(backend['repository'])):
            raise ValueError(f'Entrypoint escapes the {name} repository')
        backend['entrypoint'] = str(entry)
    for backend in config.get('simulations', {}).values():
        for key in ('environment', 'entrypoint', 'scene'):
            backend[key] = str(resolve_path(path.parent, backend[key]))
        backend['python'] = str(Path(backend['environment']) / 'bin/python')
    return config


def file_sha256(path):
    with Path(path).open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def git_snapshot(repository, entrypoint=None):
    repository = Path(repository)

    def git(*args):
        return subprocess.check_output(['git', '-C', str(repository), *args],
                                       stderr=subprocess.PIPE)

    try:
        result = {
            'repository': str(repository),
            'head': git('rev-parse', 'HEAD').decode().strip(),
            'status': git('status', '--porcelain').decode().splitlines(),
            'tracked_diff_sha256': hashlib.sha256(git('diff', 'HEAD', '--binary')).hexdigest(),
        }
        try:
            result['origin'] = git('remote', 'get-url', 'origin').decode().strip()
        except subprocess.CalledProcessError:
            result['origin'] = None
        if entrypoint and Path(entrypoint).is_file():
            result['entrypoint_sha256'] = file_sha256(entrypoint)
        return result
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        return {'repository': str(repository), 'error': str(exc)}


def doctor(config):
    checks = {}
    for name, backend in config['backends'].items():
        checks[name] = {
            'repository': Path(backend['repository']).is_dir(),
            'python': Path(backend['python']).is_file() and os.access(backend['python'], os.X_OK),
            'entrypoint': Path(backend['entrypoint']).is_file(),
        }
        if 'checkpoint' in backend:
            checks[name]['checkpoint'] = Path(backend['checkpoint']).is_file()
        if name == 'bundlesdf':
            checks[name]['nvcc'] = (Path(backend['cuda_home']) / 'bin/nvcc').is_file()
    simulations = {
        name: {'python': Path(b['python']).is_file() and os.access(b['python'], os.X_OK),
               'entrypoint': Path(b['entrypoint']).is_file(), 'scene': Path(b['scene']).is_file()}
        for name, b in config.get('simulations', {}).items()
    }
    return {
        'ready': all(all(values.values()) for values in [*checks.values(), *simulations.values()]),
        'scope': 'Checks configured paths and launchers; run smoke workflows to verify GPU execution.',
        'config': config['_file'], 'checks': checks,
        'simulations': simulations,
        'backends': {name: git_snapshot(b['repository'], b['entrypoint'])
                     for name, b in config['backends'].items()},
    }


def backend_environment(config, name):
    backend = config['backends'][name]
    runtime = Path(config['storage']['runtime_root'])
    env = dict(os.environ)
    env.pop('PYTHONHOME', None)
    env.pop('PYTHONPATH', None)
    env.update({
        'VIRTUAL_ENV': backend['environment'], 'PYTHONNOUSERSITE': '1',
        'PYTHONUTF8': '1', 'PYTHONUNBUFFERED': '1',
        'HF_HOME': str(runtime / 'cache/huggingface'),
        'TORCH_HOME': str(runtime / 'cache/torch'),
        'OMP_NUM_THREADS': '8' if name == 'stereo' else '4',
    })
    paths = [str(Path(backend['environment']) / 'bin')]
    if name == 'bundlesdf':
        repository = Path(backend['repository'])
        env['PYTHONPATH'] = os.pathsep.join(str(repository / suffix)
                                           for suffix in ('', 'mycuda', 'BundleTrack/build'))
        env.update({
            'CUDA_HOME': backend['cuda_home'],
            'TORCH_EXTENSIONS_DIR': str(runtime / 'cache/torch_extensions'),
            'WARP_CACHE_PATH': str(runtime / 'cache/warp'),
        })
        paths.append(str(Path(backend['cuda_home']) / 'bin'))
    env['PATH'] = os.pathsep.join(paths + [env.get('PATH', '')])
    return env


def run_smoke(config, name, output=None):
    from .workflows import launch
    if name not in ('stereo', 'bundlesdf'):
        raise ValueError(f'Unknown smoke backend: {name}')
    return launch(config, 'smoke.' + name, output)
