#!/usr/bin/env python3
"""Run any plugin script with the same hash-locked Python runtime."""
import hashlib, importlib.util, os, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REQUIRED=('jsonschema','yaml','docx','openpyxl')
def ready(): return sys.version_info >= (3,12) and all(importlib.util.find_spec(x) for x in REQUIRED)
def main():
    if len(sys.argv)<2: raise SystemExit('用法：python3 scripts/launch.py <script.py> [参数]')
    target=Path(sys.argv[1]).resolve()
    if not target.is_file(): raise SystemExit(f'脚本不存在：{target}')
    if ready() or target.name in ('bootstrap.py','launch.py'):
        os.execv(sys.executable,[sys.executable,str(target),*sys.argv[2:]])
    lock=ROOT/'requirements.lock'; key=hashlib.sha256(lock.read_bytes()).hexdigest()[:16]
    suffix=Path('Scripts/python.exe') if os.name=='nt' else Path('bin/python')
    candidates=[ROOT/'.venv'/suffix,Path.home()/'.cache/harness-runtime'/key/f'py{sys.version_info.major}{sys.version_info.minor}'/suffix]
    candidates.extend(sorted(Path.home().glob(f'.cache/harness-runtime/{key}/py3*/{suffix.as_posix()}'), reverse=True))
    candidate=next((p for p in candidates if p.is_file()),None)
    if candidate: os.execv(str(candidate),[str(candidate),str(target),*sys.argv[2:]])
    raise SystemExit(f'插件运行环境不完整：需要 Python 3.12+ 及 {", ".join(REQUIRED)}。请先执行：{sys.executable} {ROOT / "scripts/bootstrap.py"} --install')
if __name__=='__main__': main()
