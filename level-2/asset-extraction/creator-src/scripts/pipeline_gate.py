#!/usr/bin/env python3
"""Deterministic prepare/postcheck gate for the packaged asset workflow."""
import argparse, json, subprocess, sys
from pathlib import Path

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('phase', choices=('prepare','postcheck'))
    ap.add_argument('source_path')
    ap.add_argument('artifact_dir', type=Path)
    args=ap.parse_args()
    root=Path(__file__).resolve().parents[1]
    source=Path(args.source_path).expanduser().resolve()
    work=args.artifact_dir.resolve(); work.mkdir(parents=True,exist_ok=True)
    if not source.is_file(): raise SystemExit(f'源剧本不存在：{source}')
    if args.phase=='prepare':
        if (work/'scenes.json').exists() or (work/'progress.json').exists():
            raise SystemExit('artifact_dir 已存在工作状态；请使用 status 恢复，不得覆盖旧执行')
        subprocess.run([sys.executable,str(root/'scripts/workflow.py'),'prepare',str(source),str(work)],check=True)
        print(json.dumps({'status':'prepared','artifact_dir':str(work)},ensure_ascii=False)); return
    verifier=root/'scripts/verify_delivery.py'
    subprocess.run([sys.executable,str(verifier),str(work)],check=True)
    print(json.dumps({'status':'postcheck_passed','artifact_dir':str(work),'artifacts':['assets.json','screenplay-asset-table.xlsx']},ensure_ascii=False))
if __name__=='__main__': main()
