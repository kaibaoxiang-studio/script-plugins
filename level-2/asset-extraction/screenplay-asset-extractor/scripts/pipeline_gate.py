#!/usr/bin/env python3
"""Deterministic pipeline gates: initialize or postcheck an asset workflow."""
import argparse, json, subprocess, sys
from pathlib import Path

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--input',required=True); ap.add_argument('--output',required=True); ap.add_argument('--phase',choices=['prepare','postcheck'],required=True)
    a=ap.parse_args(); task=json.loads(Path(a.input).read_text(encoding='utf-8')); inputs=task.get('inputs',{}); phase=inputs.get('phase',a.phase); work=Path(task['artifact_dir']); work.mkdir(parents=True,exist_ok=True)
    root=Path(__file__).resolve().parents[1]; wf=root/'scripts'/'workflow.py'; source=Path(inputs['source_path']).expanduser().resolve()
    if not source.is_file(): raise SystemExit(f'源剧本不存在：{source}')
    if a.phase=='prepare':
        if (work/'progress.json').exists() or (work/'scenes.json').exists():
            result={'status':'existing','artifact_dir':'.'}
        else:
            subprocess.run([sys.executable,str(wf),'prepare',str(source),str(work)],check=True)
            result={'status':'prepared','artifact_dir':'.'}
    else:
        verifier=root/'scripts'/'verify_delivery.py'
        if not (work/'acceptance.json').is_file(): raise SystemExit('尚未完成 finalize：缺少 acceptance.json')
        subprocess.run([sys.executable,str(verifier),str(work)],check=True)
        result={'status':'postcheck_passed','artifact_dir':'.','artifacts':['assets.json','screenplay-asset-table.xlsx']}
    Path(a.output).write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8')
if __name__=='__main__': main()
