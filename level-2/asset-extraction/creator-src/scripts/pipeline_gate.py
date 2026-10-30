#!/usr/bin/env python3
"""Deterministic phase gate for the packaged screenplay asset workflow."""
import argparse, hashlib, json, subprocess, sys
from pathlib import Path

def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('phase', choices=('prepare','check','postcheck')); ap.add_argument('source_path'); ap.add_argument('artifact_dir', type=Path); args=ap.parse_args()
    root=Path(__file__).resolve().parents[1]; source=Path(args.source_path).expanduser().resolve(); work=args.artifact_dir.resolve(); work.mkdir(parents=True,exist_ok=True)
    if not source.is_file(): raise SystemExit(f'源剧本不存在：{source}')
    marker=work/'pipeline.json'
    if args.phase=='prepare':
        if (work/'scenes.json').exists() or (work/'progress.json').exists(): raise SystemExit('artifact_dir 已存在工作状态；请使用 status 恢复，不得覆盖旧执行')
        subprocess.run([sys.executable,str(root/str(root/'scripts/workflow.py')),'prepare',str(source),str(work)],check=True)
        marker.write_text(json.dumps({'source_sha256':digest(source),'stage':'prepared'},ensure_ascii=False),encoding='utf-8')
        print(json.dumps({'status':'prepared','artifact_dir':str(work)},ensure_ascii=False)); return
    if not marker.is_file(): raise SystemExit('缺少 pipeline.json；必须先运行 prepare gate')
    state=json.loads(marker.read_text(encoding='utf-8'))
    if state.get('source_sha256') != digest(source): raise SystemExit('源剧本已变化；必须重新 prepare')
    status=subprocess.run([sys.executable,str(root/str(root/'scripts/workflow.py')),'status',str(work)],capture_output=True,text=True)
    if status.returncode: raise SystemExit(status.stderr or status.stdout)
    if args.phase=='check':
        if 'ready_to_finalize' not in status.stdout and 'complete' not in status.stdout: raise SystemExit('语义审核或工作簿检查未完成，禁止进入 finalize')
        marker.write_text(json.dumps({'source_sha256':state['source_sha256'],'stage':'ready_to_finalize'},ensure_ascii=False),encoding='utf-8')
        print(status.stdout); return
    verifier=root/str(root/'scripts/verify_delivery.py'); subprocess.run([sys.executable,str(verifier),str(work)],check=True)
    marker.write_text(json.dumps({'source_sha256':state['source_sha256'],'stage':'complete'},ensure_ascii=False),encoding='utf-8')
    print(json.dumps({'status':'postcheck_passed','artifact_dir':str(work),'artifacts':['assets.json','screenplay-asset-table.xlsx']},ensure_ascii=False))
if __name__=='__main__': main()
