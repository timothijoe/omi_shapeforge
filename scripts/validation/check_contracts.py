"""Offline v1 contract checks; never execute a workflow or certify file contents."""
import argparse
from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path, PurePosixPath

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[2]
CONTRACTS = ROOT / 'contracts/v1'


def read_json(path):
    def nonfinite(value):
        raise ValueError(f'Non-finite JSON number: {value}')

    def unique_keys(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f'Duplicate JSON key: {key}')
            result[key] = value
        return result

    return json.loads(Path(path).read_text(), parse_constant=nonfinite,
                      object_pairs_hook=unique_keys)


def relative_path(value):
    path = PurePosixPath(value)
    return (not path.is_absolute() and '\\' not in value and ':' not in value
            and all(part not in ('', '.', '..') for part in value.split('/')))


def validate(record, schema, profiles):
    """Return structural and cross-field errors, without reading referenced files."""
    errors = [f'{error.json_path}: {error.message}' for error in
              Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(record)]
    if errors:
        return errors

    def require(condition, message):
        if not condition:
            errors.append(message)

    execution = record['execution']
    state, code = execution['state'], execution['returncode']
    started, finished = record['started_utc'], record['finished_utc']
    legacy = record['legacy']
    require(record['workflow'] in profiles, 'workflow has no v1 profile')
    if record['workflow'] not in profiles:
        return errors
    profile = profiles[record['workflow']]
    require(record['record_kind'] != 'imported' or legacy is not None,
            'imported records must reference legacy documents')
    require(record['record_kind'] != 'native' or legacy is None,
            'native records cannot claim legacy origin')
    if state == 'succeeded':
        require(code == 0 and execution['error'] is None,
                'successful execution requires exit 0 and no process error')
    elif state in ('pending', 'running', 'unknown'):
        require(code is None and execution['error'] is None,
                'unfinished/unknown execution cannot have an exit code or process error')
    else:
        require(code != 0 and execution['error'] is not None,
                'failed/cancelled execution needs a reason and cannot claim exit 0')
    require(state != 'unknown' or legacy is not None,
            'unknown execution is reserved for legacy imports')
    if state in ('pending', 'running'):
        require(finished is None, 'unfinished execution cannot have finished_utc')
    if state == 'pending':
        require(started is None, 'pending execution has no started_utc')
    if legacy is None and state in ('running', 'succeeded', 'failed', 'cancelled'):
        require(started is not None, 'new attempted execution needs started_utc')
        if state != 'running':
            require(finished is not None, 'new terminal execution needs finished_utc')
    if started is not None and finished is not None:
        require(datetime.fromisoformat(finished) >= datetime.fromisoformat(started),
                'finished_utc precedes started_utc')
    for stamp in (started, finished):
        if stamp is not None:
            require(datetime.fromisoformat(stamp).utcoffset().total_seconds() == 0,
                    'timestamps must be UTC')
    if state in ('running', 'succeeded') and legacy is None:
        require(bool(execution['command']) and execution['cwd'] is not None
                and execution['log'] is not None, 'launched process needs command/cwd/log')
        require(bool(record['sources']) and record['environment']['executable'] is not None,
                'launched process needs source/environment identity')
    if execution['log'] is not None:
        require(relative_path(execution['log']), 'log must stay within run root')
    for source in record['sources']:
        if any(source[key] is None for key in ('head', 'dirty', 'entrypoint_sha256')):
            require(source['note'] is not None, 'unknown source facts require a note')

    documents = [] if legacy is None else legacy['documents']
    files = record['inputs'] + record['artifacts'] + documents
    for item in record['inputs'] + documents:
        require(PurePosixPath(item['path']).is_absolute(),
                'input and legacy document paths must be absolute')
    ids = [item['id'] for item in files]
    require(len(ids) == len(set(ids)), 'file IDs must be unique across inputs/artifacts/legacy')
    paths = [item['path'] for item in record['artifacts']]
    require(len(paths) == len(set(paths)), 'artifact paths must be unique')
    for item in record['artifacts']:
        require(relative_path(item['path']), 'artifact path must stay within run root')
        require(item['path'].startswith('backend/'), 'backend artifacts belong in backend/')
    for group_name in ('validation', 'acceptance'):
        group = record[group_name]
        checks = group['checks']
        check_ids = [check['id'] for check in checks]
        require(len(check_ids) == len(set(check_ids)), f'{group_name}: duplicate check IDs')
        for check in checks:
            require(set(check['evidence']).issubset(ids), f'{group_name}: unknown evidence ID')
            if check['status'] == 'passed':
                require(check['observed'] is not None and bool(check['evidence']),
                        f'{group_name}: passed check needs observation and evidence')
        statuses = [check['status'] for check in checks]
        if group['status'] == 'passed':
            require(bool(checks) and all(s == 'passed' for s in statuses),
                    f'{group_name}: passed requires nonempty, all-passed checks')
        elif group['status'] == 'failed':
            require('failed' in statuses, f'{group_name}: failed needs a failed check')
        else:
            require(not statuses or ('not_evaluated' in statuses and 'failed' not in statuses),
                    f'{group_name}: inconsistent not_evaluated aggregate')
    require(record['acceptance']['scope'] == profile['scope'], 'acceptance scope exceeds profile')
    if record['validation']['status'] == 'passed':
        require(state == 'succeeded' or (legacy is not None and state == 'unknown'),
                'validation cannot pass for an incomplete or failed new execution')
        checks = {c['id'] for c in record['validation']['checks']}
        require({'required_artifacts', 'report_status', 'hashes', 'content'} <= checks,
                'validation is missing mandatory checks')
        status_check = next((c for c in record['validation']['checks']
                             if c['id'] == 'report_status'), None)
        if status_check:
            require(status_check['expected'] == profile['report_status']
                    and status_check['observed'] == profile['report_status'],
                    'report status must exactly match the workflow profile')
        inputs = {item['id'] for item in record['inputs']}
        require(set(profile['required_inputs']) <= inputs, 'missing required input identity')
        artifacts = {item['id']: item for item in record['artifacts']}
        for name, spec in profile['required_artifacts'].items():
            require(name in artifacts, f'missing required artifact: {name}')
            if name in artifacts:
                item = artifacts[name]
                require(all(item[k] == v for k, v in spec.items()),
                        f'artifact {name}: path/format/units/frame mismatch')
        for item in record['inputs'] + record['artifacts']:
            require(item['sha256'] is not None and item['size_bytes'] is not None
                    and item['size_bytes'] > 0, 'validated files need hash and positive byte size')
    if record['acceptance']['status'] != 'not_evaluated':
        require(state == 'succeeded' and record['validation']['status'] == 'passed',
                'acceptance evaluation requires successful execution and valid artifacts')
        checks = {c['id'] for c in record['acceptance']['checks']}
        require(set(profile['acceptance_checks']) <= checks, 'missing profile acceptance checks')
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('records', nargs='*', type=Path,
                        help='Additional records to check structurally; no file-content checks')
    args = parser.parse_args()
    schema = read_json(CONTRACTS / 'run.schema.json')
    Draft202012Validator.check_schema(schema)
    profiles = read_json(CONTRACTS / 'profiles.json')['profiles']
    failures = []
    examples = sorted((CONTRACTS / 'examples').glob('*.json'))
    for path in examples + args.records:
        errors = validate(read_json(path), schema, profiles)
        failures.extend(f'{path.name}: {error}' for error in errors)
    cases = read_json(CONTRACTS / 'invalid-cases.json')
    for case in cases:
        record = deepcopy(read_json(CONTRACTS / 'examples' / case['example']))
        for edit in case['edits']:
            parts = edit['path'].strip('/').split('/')
            target = record
            for part in parts[:-1]:
                target = target[int(part)] if isinstance(target, list) else target[part]
            key = int(parts[-1]) if isinstance(target, list) else parts[-1]
            target[key] = edit['value']
        errors = validate(record, schema, profiles)
        if not any(case['expected_error'] in error for error in errors):
            failures.append(f"negative case {case['id']}: expected error not found: {errors}")
    print(json.dumps({'status': 'failed' if failures else 'passed',
                      'examples': len(examples), 'negative_cases': len(cases),
                      'additional_records': len(args.records), 'errors': failures,
                      'scope': 'Schema and cross-field checks only; no runtime/file validation.'},
                     indent=2, ensure_ascii=False))
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
