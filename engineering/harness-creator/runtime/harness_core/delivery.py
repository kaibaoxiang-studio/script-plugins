"""Evidence gate for building and independently validating plugin features.

Plans and evidence live in the user's work area, outside the packaged plugin.
The gate verifies contracts, hashes and recorded checks; it cannot establish
that a claimed reviewer used a genuinely separate model context.
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import uuid

from .common import fingerprint, inside, now, read_json, require_name, sha, write_json
from .contracts import validate_data


SCHEMAS = Path(__file__).resolve().parents[2] / 'schemas'


def validate_plan(plan, blueprint):
    """Check a delivery plan against one frozen HarnessBlueprintV1."""
    from .packages import validate_spec

    validate_spec(blueprint)
    validate_data(plan, read_json(SCHEMAS / 'delivery-plan.schema.json'))
    feature_map = {}
    capability_ids = {item['id'] for item in blueprint['capabilities']}
    covered = set()
    for feature in plan['features']:
        feature_id = feature['id']
        require_name(feature_id)
        if feature_id in feature_map:
            raise ValueError(f'Duplicate delivery feature: {feature_id}')
        feature_map[feature_id] = feature
        for capability_id in feature['capability_ids']:
            if capability_id not in capability_ids:
                raise ValueError(f'Unknown capability in {feature_id}: {capability_id}')
            covered.add(capability_id)
        scenario_ids = set()
        for scenario in feature['scenarios']:
            scenario_id = scenario['id']
            require_name(scenario_id)
            if scenario_id in scenario_ids:
                raise ValueError(f'Duplicate scenario in {feature_id}: {scenario_id}')
            scenario_ids.add(scenario_id)
    if covered != capability_ids:
        raise ValueError(f'Delivery plan omits capabilities: {sorted(capability_ids - covered)}')
    visiting, visited = set(), set()

    def visit(feature_id):
        if feature_id not in feature_map:
            raise ValueError(f'Missing delivery dependency: {feature_id}')
        if feature_id in visiting:
            raise ValueError('Delivery plan contains a cycle')
        if feature_id in visited:
            return
        visiting.add(feature_id)
        for dep in feature_map[feature_id]['depends_on']:
            visit(dep)
        visiting.remove(feature_id)
        visited.add(feature_id)

    for feature_id in feature_map:
        visit(feature_id)
    return feature_map


def capture_check(workspace, feature_id, scenario_id, command, timeout=600):
    """Execute an explicit argv without a shell and retain the actual result."""
    workspace = Path(workspace).resolve()
    if not workspace.is_dir():
        raise ValueError(f'Workspace does not exist: {workspace}')
    require_name(feature_id)
    require_name(scenario_id)
    if not command or any(not isinstance(arg, str) or not arg for arg in command):
        raise ValueError('Check command must be a nonempty argv')
    if not 1 <= timeout <= 3600:
        raise ValueError('Check timeout must be 1-3600 seconds')
    try:
        completed = subprocess.run(command, cwd=workspace, capture_output=True,
                                   text=True, errors='replace', timeout=timeout, check=False)
        exit_code = completed.returncode
        stdout, stderr = completed.stdout, completed.stderr
    except subprocess.TimeoutExpired as exc:
        exit_code = 124
        stdout = (exc.stdout or b'').decode(errors='replace') if isinstance(exc.stdout, bytes) else (exc.stdout or '')
        stderr = (exc.stderr or b'').decode(errors='replace') if isinstance(exc.stderr, bytes) else (exc.stderr or '')
        stderr += f'\nCheck timed out after {timeout} seconds.'
    log = {'scenario_id': scenario_id, 'command': command, 'exit_code': exit_code,
           'captured_at': now(), 'stdout': stdout, 'stderr': stderr}
    relative = f'.harness/verification/{feature_id}/{uuid.uuid4().hex}.json'
    path = inside(workspace, relative)
    write_json(path, log)
    return {'status': 'passed' if exit_code == 0 else 'failed',
            'scenario_id': scenario_id, 'command': command, 'exit_code': exit_code,
            'log_path': relative, 'log_sha256': sha(path)}


def _verified_file(workspace, relative, expected):
    path = inside(workspace, relative)
    if path.is_symlink() or not path.is_file():
        raise ValueError(f'Evidence file is missing or a symlink: {relative}')
    if sha(path) != expected:
        raise ValueError(f'Evidence file changed: {relative}')
    return path


def _check_records(workspace, checks, scenario_ids, role, feature_id):
    passing = set()
    for check in checks:
        scenario_id = check['scenario_id']
        if scenario_id not in scenario_ids:
            raise ValueError(f'Unknown {role} scenario in {feature_id}: {scenario_id}')
        if 'status' in check and check['status'] != ('passed' if check['exit_code'] == 0 else 'failed'):
            raise ValueError(f'Check status disagrees with exit code: {check["log_path"]}')
        log_path = _verified_file(workspace, check['log_path'], check['log_sha256'])
        log = read_json(log_path)
        if any(log.get(key) != check[key] for key in ('scenario_id', 'command', 'exit_code')):
            raise ValueError(f'Check record disagrees with log: {check["log_path"]}')
        if check['exit_code'] == 0:
            passing.add(scenario_id)
        else:
            passing.discard(scenario_id)
    missing = scenario_ids - passing
    if missing:
        raise ValueError(f'{role} checks not passing in {feature_id}: {sorted(missing)}')


def check_delivery(workspace, blueprint_path, plan_path, evidence_dir, plugin):
    """Return a release gate report; never treat missing evidence as success."""
    workspace = Path(workspace).resolve()
    blueprint_path = Path(blueprint_path).resolve()
    plan_path = Path(plan_path).resolve()
    evidence_dir = Path(evidence_dir).resolve()
    plugin = Path(plugin).resolve()
    blueprint = read_json(blueprint_path)
    plan = read_json(plan_path)
    feature_map = validate_plan(plan, blueprint)
    if plan['blueprint_sha256'] != sha(blueprint_path):
        raise ValueError('Blueprint changed after delivery plan was prepared')
    packaged_blueprint = plugin / 'harness-blueprint.json'
    if not packaged_blueprint.is_file() or read_json(packaged_blueprint) != blueprint:
        raise ValueError('Delivery plugin does not match the checked blueprint')
    plan_hash = sha(plan_path)
    plugin_hash = fingerprint(plugin)
    errors, accepted = [], []
    evidence_schema = read_json(SCHEMAS / 'feature-evidence.schema.json')
    for feature_id, feature in feature_map.items():
        try:
            path = inside(evidence_dir, f'{feature_id}.json')
            if path.is_symlink() or not path.is_file():
                raise ValueError(f'Missing feature evidence: {feature_id}')
            record = read_json(path)
            validate_data(record, evidence_schema)
            if record['feature_id'] != feature_id or record['plan_sha256'] != plan_hash:
                raise ValueError(f'Stale or mismatched feature evidence: {feature_id}')
            implementation = record['implementation']
            validation = record['validation']
            if validation['plugin_fingerprint'] != plugin_hash:
                raise ValueError(f'Plugin changed after validation: {feature_id}')
            if implementation['session_id'] == validation['session_id']:
                raise ValueError(f'Implementer and validator session IDs match: {feature_id}')
            if validation['verdict'] != 'accept':
                raise ValueError(f'Feature {feature_id} verdict is {validation["verdict"]}')
            implementation_logs = {item['log_path'] for item in implementation['checks']}
            validation_logs = {item['log_path'] for item in validation['checks']}
            if implementation_logs & validation_logs:
                raise ValueError(f'Validator reused implementer check logs: {feature_id}')
            scenarios = {item['id'] for item in feature['scenarios']}
            _check_records(workspace, implementation['checks'], scenarios, 'Implementer', feature_id)
            _check_records(workspace, validation['checks'], scenarios, 'Validator', feature_id)
            for artifact in implementation['artifacts']:
                _verified_file(workspace, artifact['path'], artifact['sha256'])
            report = _verified_file(workspace, validation['report']['path'], validation['report']['sha256'])
            if report.stat().st_size == 0:
                raise ValueError(f'Validator report is empty: {feature_id}')
            accepted.append(feature_id)
        except (ValueError, KeyError, OSError, json.JSONDecodeError) as exc:
            errors.append(f'{feature_id}: {exc}')
    return {'valid': not errors, 'accepted': accepted, 'errors': errors,
            'features': len(feature_map), 'plan_sha256': plan_hash}
