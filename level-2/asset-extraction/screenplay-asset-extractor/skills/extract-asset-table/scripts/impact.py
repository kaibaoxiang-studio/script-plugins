#!/usr/bin/env python3
"""Explain which review scopes are affected by current snapshot changes."""
import json
from pathlib import Path
from audit_state import changed_scopes
def run(work):
    root=Path(work); data=json.loads((root/'scenes.json').read_text()); assets=json.loads((root/'assets.json').read_text()); review=json.loads((root/'review.json').read_text())
    changed=changed_scopes(data,assets,review)
    affected=[]
    if changed.get('characters'): affected += ['人物','场次总表']
    if changed.get('scenes'): affected += ['场景','场次总表']
    if changed.get('props'): affected += ['道具','场次总表']
    return {'changed_scopes':changed,'affected_sheets':sorted(set(affected)),'note':'仅提示复核范围，不自动修改视觉证据。'}
