#!/usr/bin/env python3
"""Validate that automatic visual evidence covers representative pages."""
import json
from pathlib import Path
from image_evidence import validate_png
SHEETS=('人物','场景','道具','场次总表')
def run(work):
    root=Path(work); review=json.loads((root/'review.json').read_text()); errors=[]; report={}
    rows={x.get('sheet'):x for x in (review.get('delivery_review') or {}).get('visual',[]) if isinstance(x,dict)}
    for sheet in SHEETS:
        files=rows.get(sheet,{}).get('evidence_files',[])
        if len(files)<3: errors.append(f'{sheet} 视觉证据少于首/中/尾三页')
        report[sheet]=len(files)
        for f in files:
            try: validate_png(Path(f).read_bytes())
            except (OSError,ValueError) as e: errors.append(f'{sheet} 视觉证据无效：{e}')
    return {'ok':not errors,'errors':errors,'pages':report}
