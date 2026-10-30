#!/usr/bin/env python3
"""Dispatch asset_core.py with this plugin's hash-locked Python runtime."""
import hashlib
import importlib.util
import os
from pathlib import Path
import sys


def main():
    root = Path(__file__).resolve().parents[1]
    key = hashlib.sha256((root / "requirements.lock").read_bytes()).hexdigest()[:16]
    version = "py{}{}".format(sys.version_info.major, sys.version_info.minor)
    cached = Path.home() / ".cache" / "harness-runtime" / key
    candidates = [cached / version / "bin" / "python"]
    candidates.extend(sorted(cached.glob("py3*/bin/python"), reverse=True))
    if sys.version_info >= (3, 12) and all(importlib.util.find_spec(name) for name in ("yaml", "jsonschema", "docx", "openpyxl", "lxml")):
        executable = Path(sys.executable)
    else:
        executable = next((item for item in candidates if item.is_file()), None)
    if executable is None:
        raise SystemExit("缺少插件锁定运行时；请用 Python 3.12+ 执行本插件 scripts/bootstrap.py --install")
    os.execv(str(executable), [str(executable), str(root / "scripts" / "asset_core.py"), *sys.argv[1:]])


if __name__ == "__main__":
    main()
