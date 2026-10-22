#!/usr/bin/env python3
"""Validate relocated plugins and build independently verifiable release ZIPs."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {'.git', '.venv', '.harness', '__pycache__', '.pytest_cache', 'dist', '.DS_Store'}


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def files(root):
    for path in sorted(root.rglob('*')):
        relative = path.relative_to(root)
        if any(part in EXCLUDED or part.startswith(('.validation-', '.release-candidate')) for part in relative.parts):
            continue
        if path.is_symlink():
            raise ValueError(f'Symlinks are not release inputs: {relative}')
        if path.is_file() and path.suffix not in {'.pyc', '.pyo'}:
            yield path, relative.as_posix()


def invoke(plugin, command):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    result = subprocess.run([sys.executable, str(plugin / 'harness.py'), command,
                             *(['--plugin', str(plugin)] if command == 'validate' else [])],
                            capture_output=True, text=True, cwd=plugin, env=env, check=True)
    return json.loads(result.stdout)


def validate():
    if sys.version_info < (3, 12):
        raise ValueError('Use Python 3.12+ with the locked Harness dependencies installed')
    config = read_json(ROOT / 'release.json')
    if (ROOT / 'VERSION').read_text().strip() != config['version']:
        raise ValueError('Project versions disagree')
    catalog = read_json(ROOT / '.agents/plugins/marketplace.json')
    expected = {c['id']: './' + c['path'] for c in config['components']}
    actual = {p['name']: p['source']['path'] for p in catalog['plugins']}
    if actual != expected or len(catalog['plugins']) != 4:
        raise ValueError('Marketplace must expose exactly the four release components')
    report = {'project_version': config['version'], 'date': config['date'], 'components': [], 'errors': []}
    for component in config['components']:
        plugin = ROOT / component['path']
        if not plugin.resolve().is_relative_to(ROOT) or not (ROOT / component['source_path']).is_dir():
            raise ValueError(f'Invalid component path: {component["id"]}')
        manifest = read_json(plugin / '.codex-plugin/plugin.json')
        portable = read_json(plugin / 'plugin.json')
        if manifest['name'] != component['id'] or manifest['version'] != component['version']:
            raise ValueError(f'Component identity mismatch: {component["id"]}')
        if portable['name'] != manifest['name'] or portable['version'] != manifest['version']:
            raise ValueError(f'Portable/Codex manifest mismatch: {component["id"]}')
        capabilities = read_json(plugin / 'capabilities.json')['capabilities']
        if component['entry'] not in {c['id'] for c in capabilities}:
            raise ValueError(f'Unknown entry capability: {component["id"]}')
        required = ['harness.py', 'requirements.lock', 'capabilities.json', 'RUNTIME.md',
                    'THIRD_PARTY_NOTICES.md', 'sources.lock.json']
        for name in required:
            if not (plugin / name).is_file():
                raise ValueError(f'Missing {component["id"]}/{name}')
        lock = plugin / 'generation-lock.json'
        if lock.exists():
            for name, expected_hash in read_json(lock)['files'].items():
                target = (plugin / name).resolve()
                if not target.is_relative_to(plugin.resolve()) or not target.is_file() or digest(target) != expected_hash:
                    raise ValueError(f'Snapshot hash mismatch: {component["id"]}/{name}')
        result = invoke(plugin, 'validate')
        if not result.get('valid'):
            raise ValueError(f'Plugin validation failed: {component["id"]}: {result}')
        doctor = invoke(plugin, 'doctor')
        if not doctor.get('python_supported') or not doctor.get('codex_version'):
            raise ValueError(f'Runtime unavailable: {component["id"]}')
        report['components'].append({'id': component['id'], 'role': component['role'],
            'version': component['version'], 'validation': result,
            'runtime': {k: doctor[k] for k in ('python', 'python_supported', 'codex_version')}})
    secret = re.compile(r'(?:sk-[A-Za-z0-9_-]{24,}|gh[pousr]_[A-Za-z0-9]{24,})')
    for path, relative in files(ROOT):
        if path.suffix == '.py':
            ast.parse(path.read_text(encoding='utf-8'), filename=relative)
        if path.suffix in {'.py', '.md', '.json', '.yaml', '.yml', '.toml', '.txt'}:
            text = path.read_text(encoding='utf-8')
            if re.search(r'/Users/[A-Za-z0-9._-]+/', text) or secret.search(text):
                raise ValueError(f'Private local path or credential-like text: {relative}')
    report['status'] = 'passed'
    return report


def package(output):
    checks = validate()
    config = read_json(ROOT / 'release.json')
    output.mkdir(parents=True, exist_ok=True)
    manifest = {'project': config['project'], 'version': config['version'], 'date': config['date'],
                'components': [], 'validation': checks}
    for component in config['components']:
        source = ROOT / component['path']
        filename = component['id'] + '-' + component['version'] + '.zip'
        target = output / filename
        if target.exists():
            raise FileExistsError(target)
        hashes = {}
        with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as archive:
            for path, relative in files(source):
                info = zipfile.ZipInfo(component['id'] + '/' + relative, (2026, 10, 21, 0, 0, 0))
                mode = 0o755 if path.stat().st_mode & 0o111 else 0o644
                info.external_attr = mode << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, path.read_bytes())
                hashes[relative] = digest(path)
        with tempfile.TemporaryDirectory(prefix='script-plugins-zip-') as tmp:
            with zipfile.ZipFile(target) as archive:
                archive.extractall(tmp)
            unpacked = Path(tmp) / component['id']
            for relative, expected_hash in hashes.items():
                if digest(unpacked / relative) != expected_hash:
                    raise ValueError(f'ZIP content mismatch: {relative}')
            result = invoke(unpacked, 'validate')
            if not result.get('valid'):
                raise ValueError(f'Unpacked plugin invalid: {filename}')
        manifest['components'].append({**component, 'archive': filename, 'sha256': digest(target),
                                       'files': hashes, 'unpacked_validation': result})
    manifest_path = output / ('script-plugins-' + config['version'] + '-manifest.json')
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    artifacts = [output / c['archive'] for c in manifest['components']] + [manifest_path]
    (output / 'SHA256SUMS.txt').write_text(''.join(digest(p) + '  ' + p.name + '\n' for p in artifacts), encoding='utf-8')
    return {'status': 'packaged', 'project_version': config['version'],
            'archives': [c['archive'] for c in manifest['components']], 'manifest': manifest_path.name}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['validate', 'package'])
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.command == 'package':
        result = package((args.output or ROOT / ('dist/v' + read_json(ROOT / 'release.json')['version'])).resolve())
    else:
        result = validate()
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
