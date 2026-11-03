#!/usr/bin/env python3
"""Cross-asset semantic consistency checks that do not rewrite judgments."""
import json
from pathlib import Path
def run(work):
    root=Path(work); data=json.loads((root/'scenes.json').read_text()); assets=json.loads((root/'assets.json').read_text()); errors=[]; warnings=[]
    for kind in ('characters','scenes','props'):
        for a in assets.get(kind,[]):
            states=a.get('states',[]); ids=[s.get('id') for s in states]
            if len(ids)!=len(set(ids)): errors.append(f'{kind}/{a.get("id")} 状态ID重复')
            names=[s.get('name') for s in states]
            if len(names)!=len(set(names)): warnings.append(f'{kind}/{a.get("id")} 状态名重复，需确认是否应合并')
    scene_ids={s['scene_id'] for e in data['episodes'] for s in e['scenes']}
    for kind in ('characters','scenes','props'):
        for a in assets.get(kind,[]):
            refs={sid for st in a.get('states',[]) for sid in st.get('scenes',[])}
            if not refs and a.get('states'): warnings.append(f'{kind}/{a.get("id")} 有状态但没有场次引用')
            invalid=refs-scene_ids
            if invalid: errors.append(f'{kind}/{a.get("id")} 引用不存在场次：{sorted(invalid)}')
    return {'ok':not errors,'errors':errors,'warnings':warnings}
