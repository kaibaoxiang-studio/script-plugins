#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import venv

def main():
    parser=argparse.ArgumentParser(description='Install the pinned Python runtime in the user cache.')
    parser.add_argument('--install',action='store_true')
    args=parser.parse_args()
    if sys.version_info<(3,12): raise SystemExit('Python 3.12+ required')
    lock=Path(__file__).resolve().parents[1]/'requirements.lock'
    key=hashlib.sha256(lock.read_bytes()).hexdigest()[:16]
    target=Path.home()/'.cache/harness-runtime'/key/f'py{sys.version_info.major}{sys.version_info.minor}'
    executable=target/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    command=[str(executable),'-m','pip','install','--disable-pip-version-check','--require-hashes',
             '--only-binary=:all:','--no-deps','-r',str(lock)]
    if not args.install:
        print(json.dumps({'status':'install_required','target':str(target),
                          'command':[sys.executable,str(Path(__file__).resolve()),'--install']})); return
    if not executable.exists(): venv.EnvBuilder(with_pip=True).create(target)
    subprocess.run(command,check=True)
    subprocess.run([str(executable),'-c','import yaml,jsonschema'],check=True)
    print(json.dumps({'status':'ready','python':str(executable)}))

if __name__=='__main__': main()
