#!/usr/bin/env python3
"""Create a concise Chinese delivery report from acceptance.json."""
import json
from pathlib import Path

def generate(work):
    root=Path(work); a=json.loads((root/'acceptance.json').read_text()); c=a.get('counts',{})
    lines=['# 剧本资产表交付报告','',f'版本：{a.get("version","")}',f'输入：{a.get("source_docx",{}).get("path","")}',f'输出：{a.get("output","")}', '', '## 统计',
           f'- 人物：{c.get("characters",{}).get("assets",0)} 个资产，{c.get("characters",{}).get("states",0)} 个状态',
           f'- 场景：{c.get("scenes",{}).get("assets",0)} 个资产，{c.get("scenes",{}).get("states",0)} 个状态',
           f'- 道具：{c.get("props",{}).get("assets",0)} 个资产，{c.get("props",{}).get("states",0)} 个状态', '', '## 验收',
           f'- 数据错误：{a.get("errors",0)}',f'- 未确认警告：{a.get("unconfirmed_warnings",0)}',f'- 已确认警告：{a.get("confirmed_warnings",0)}',f'- 视觉检查：{a.get("checks",{}).get("visual","")}', '', f'工作簿 SHA-256：`{a.get("workbook_sha256","")}`']
    return '\n'.join(lines)+'\n'

