"""Standard-library process runner and v1 evidence records."""
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import uuid

ROOT = Path(__file__).resolve().parents[2]


def now():
    return datetime.now(timezone.utc).isoformat()


def read_json(path):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f'Duplicate JSON key: {key}')
            result[key] = value
        return result

    def nonfinite(value):
        raise ValueError(f'Non-finite JSON: {value}')

    return json.loads(Path(path).read_text(), object_pairs_hook=pairs, parse_constant=nonfinite)


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write_json(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        with temporary.open('x') as stream:
            stream.write(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def file_record(identifier, path, format='opaque', units=None, frame=None, root=None):
    path = Path(path)
    resolved = path.resolve(strict=True)
    if root is not None and not resolved.is_relative_to(Path(root).resolve()):
        raise ValueError(f'File escapes run directory: {path}')
    if not resolved.is_file() or resolved.stat().st_size == 0:
        raise ValueError(f'Expected a nonempty regular file: {path}')
    return {'id': identifier, 'path': str(path.relative_to(root)) if root else str(resolved),
            'sha256': digest(resolved), 'size_bytes': resolved.stat().st_size,
            'format': format, 'units': units, 'frame': frame}


def source_record(repository, entrypoint):
    from .workspace import git_snapshot
    snapshot = git_snapshot(repository, entrypoint)
    return {'repository': str(repository), 'head': snapshot.get('head'),
            'dirty': bool(snapshot['status']) if 'status' in snapshot else None,
            'entrypoint_sha256': snapshot.get('entrypoint_sha256'),
            'note': snapshot.get('error') or ('Uncommitted source changes.' if snapshot.get('status') else None)}


def check(identifier, status, expected, observed, evidence, method=None):
    return {'id': identifier, 'status': status, 'method': method or identifier,
            'expected': expected, 'observed': observed, 'evidence': evidence}


def passed(record):
    return (record['execution']['state'] == 'succeeded'
            and record['validation']['status'] == 'passed'
            and record['acceptance']['status'] == 'passed')


@dataclass
class ProcessPlan:
    command: list
    cwd: str
    environment: dict
    inspection_command: list


class RunCancelled(KeyboardInterrupt):
    def __init__(self, record=None, returncode=None):
        self.record = record
        self.returncode = returncode


def invoke(command, cwd, env, log):
    """Own the process group so a caught interruption cannot orphan GPU work."""
    process = subprocess.Popen(command, cwd=cwd, env=env, stdout=log,
                               stderr=subprocess.STDOUT, start_new_session=True)
    try:
        return process.wait()
    except KeyboardInterrupt:
        for sig, timeout in ((signal.SIGINT, 3), (signal.SIGTERM, 3), (signal.SIGKILL, 3)):
            try:
                os.killpg(process.pid, sig)
            except ProcessLookupError:
                pass
            try:
                process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                continue
            # The group leader can exit while descendants still hold GPU work.
            # Escalate for the remaining group rather than treating wait() as
            # proof that every process has stopped.
            try:
                os.killpg(process.pid, 0)
            except ProcessLookupError:
                break
        raise RunCancelled(returncode=process.returncode) from None


def run_task(workflow, output, prepare):
    profile = read_json(ROOT / 'contracts/v1/profiles.json')['profiles'][workflow]
    output = Path(output).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=False)
    record = {'schema_version': 1, 'record_kind': 'native',
              'run_id': datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_') + uuid.uuid4().hex[:12],
              'workflow': workflow, 'started_utc': None, 'finished_utc': None,
              'execution': {'state': 'pending', 'returncode': None, 'command': [],
                            'cwd': None, 'log': 'run.log', 'error': None},
              'sources': [], 'environment': {'executable': None, 'versions': {}},
              'parameters': {}, 'inputs': [], 'artifacts': [],
              'validation': {'status': 'not_evaluated', 'checks': []},
              'acceptance': {'status': 'not_evaluated', 'scope': profile['scope'], 'checks': []},
              'legacy': None, 'limitations': []}
    manifest = output / 'run_manifest.json'
    write_json(manifest, record)
    stage = 'prepare'
    try:
        record['started_utc'] = now()
        plan = prepare(output, record)
        record['execution'].update(state='running', command=plan.command, cwd=plan.cwd)
        record['environment']['executable'] = plan.command[0]
        write_json(manifest, record)
        stage = 'execute'
        with (output / 'run.log').open('w') as log:
            code = invoke(plan.command, plan.cwd, plan.environment, log)
        record['execution']['returncode'] = code
        if code:
            record['execution'].update(state='cancelled' if code == -signal.SIGINT else 'failed',
                                       error=f'Backend exited with code {code}')
            return record
        record['execution']['state'] = 'succeeded'
        stage = 'validate'
        write_json(manifest, record)
        artifacts = []
        for identifier, spec in profile['required_artifacts'].items():
            artifacts.append(file_record(identifier, output / spec['path'], spec['format'],
                                         spec['units'], spec['frame'], root=output))
        record['artifacts'] = artifacts
        record['validation']['checks'].append(check('required_artifacts', 'passed',
                                                    'All required outputs exist and stay in run root',
                                                    f'{len(artifacts)} nonempty artifacts', ['report']))
        report = read_json(output / 'backend/report.json')
        if not isinstance(report, dict) or report.get('status') != profile['report_status']:
            raise ValueError('Unexpected backend report status')
        record['validation']['checks'].append(check('report_status', 'passed', profile['report_status'],
                                                    report['status'], ['report']))
        write_json(manifest, record)
        with (output / 'inspection.log').open('w') as log:
            code = invoke(plan.inspection_command, plan.cwd, plan.environment, log)
        if code:
            raise ValueError(f'Artifact inspector exited with code {code}; see inspection.log')
        inspection_file = file_record('inspection', output / 'backend/inspection.json', 'json', root=output)
        inspection = read_json(output / 'backend/inspection.json')
        if type(inspection.get('valid')) is not bool or type(inspection.get('accepted')) is not bool:
            raise ValueError('Malformed inspector verdict')
        # Neither the backend nor the inspector may silently change any input/output.
        for item in record['inputs'] + artifacts:
            path = Path(item['path']) if item in record['inputs'] else output / item['path']
            if item in artifacts and not path.resolve().is_relative_to(output):
                raise ValueError('Artifact escaped run directory during inspection')
            if path.stat().st_size != item['size_bytes'] or digest(path) != item['sha256']:
                raise ValueError(f'File changed during execution/inspection: {path}')
        record['artifacts'].append(inspection_file)
        record['environment']['versions'] = inspection['versions']
        record['validation']['checks'].append(check('hashes', 'passed', 'Recorded inputs and outputs unchanged',
                                                    'SHA256 and byte sizes match', ['inspection']))
        record['validation']['checks'].append(check('content', 'passed' if inspection['valid'] else 'failed',
                                                    'Workflow content rules satisfied', inspection['content'], ['inspection']))
        record['validation']['status'] = 'passed' if inspection['valid'] else 'failed'
        if inspection['valid']:
            status = 'passed' if inspection['accepted'] else 'failed'
            record['acceptance'] = {'status': status, 'scope': profile['scope'], 'checks': [
                check(profile['acceptance_checks'][0], status, inspection['expected'],
                      inspection['observed'], ['inspection', 'report'])]}
    except KeyboardInterrupt as exc:
        if stage in ('prepare', 'execute'):
            code = getattr(exc, 'returncode', None)
            if code == 0:
                # Some backends cleanly exit 0 after SIGINT. Preserve the actual
                # process outcome, while leaving validation/acceptance unperformed.
                record['execution'].update(state='succeeded', returncode=0, error=None)
                record['limitations'].append('User cancelled; backend exited 0 during cleanup; no acceptance performed.')
            else:
                record['execution'].update(state='cancelled', returncode=code, error='Interrupted by user')
        else:
            record['validation']['status'] = 'failed'
            record['validation']['checks'].append(check('inspection_interrupted', 'failed',
                                                        'Complete artifact inspection', 'Interrupted by user', []))
        raise RunCancelled(record, getattr(exc, 'returncode', None)) from None
    except Exception as exc:
        error = f'{type(exc).__name__}: {exc}'
        if stage in ('prepare', 'execute'):
            record['execution'].update(state='failed', error=error)
        else:
            record['validation']['status'] = 'failed'
            record['validation']['checks'].append(check('artifact_error', 'failed',
                                                        'Valid complete workflow outputs', error, []))
    finally:
        record['finished_utc'] = now()
        write_json(manifest, record)
    return record
