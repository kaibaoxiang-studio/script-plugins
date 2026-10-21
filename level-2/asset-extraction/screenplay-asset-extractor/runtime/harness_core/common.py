from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from datetime import datetime, timezone

IGNORED = {'.git', '.venv', '__pycache__', '.harness', 'dist', '.pytest_cache'}
NAME = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')

def now():
    return datetime.now(timezone.utc).isoformat()

def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':')).encode()).hexdigest()

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def write_text(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.' + path.name, dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            handle.write(value)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)

def write_json(path, value):
    write_text(path, json.dumps(value, ensure_ascii=False, indent=2) + '\n')

def inside(root, relative):
    root = Path(root).resolve()
    if Path(relative).is_absolute() or '..' in Path(relative).parts:
        raise ValueError(f'Expected package-relative path: {relative}')
    candidate = root / relative
    if not candidate.resolve().is_relative_to(root):
        raise ValueError(f'Path escapes root: {relative}')
    return candidate

def files(root):
    root = Path(root)
    for path in sorted(root.rglob('*')):
        relative = path.relative_to(root)
        if any(part in IGNORED for part in relative.parts):
            continue
        if path.is_symlink():
            raise ValueError(f'Symlinks are not portable package resources: {relative}')
        if path.is_file():
            yield path, relative.as_posix()

def fingerprint(root):
    return digest({relative: sha(path) for path, relative in files(root)})

def require_name(name):
    if not isinstance(name, str) or not NAME.fullmatch(name) or len(name) > 64:
        raise ValueError(f'Invalid kebab-case identifier: {name!r}')

def redact(text):
    return re.sub(r'(?i)(api[_-]?key|password|token|secret)\s*[:=]\s*[^\s,;]+',
                  '[REDACTED]', str(text))
