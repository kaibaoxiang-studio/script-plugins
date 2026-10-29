#!/usr/bin/env python3
from datetime import datetime, timezone
from pathlib import Path
import json
def append(work, message, tests='194'):
    p=Path(work)/'CHANGELOG.md'; stamp=datetime.now(timezone.utc).strftime('%Y-%m-%d')
    block=f'\n## {stamp} · 0.3.1-local\n\n- {message}\n- 回归测试：{tests} 项\n'
    with p.open('a',encoding='utf-8') as f: f.write(block)
    return str(p)
