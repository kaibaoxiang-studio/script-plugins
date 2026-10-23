#!/usr/bin/env python3
"""把标准剧本 docx 解析为按场次组织的 JSON。

用法:
    python3 parse_script.py <剧本.docx> <输出scenes.json>

标准剧本格式:
    第 N 集｜标题
    本集概要：……
    N-M 场景名 内/外 时间
    人物：A、B、C
    ▲ 动作描述
    角色（情绪）[VO/OS]：台词
"""
import json
import re
import sys

import docx

RE_EPISODE = re.compile(r'^第\s*(\d+)\s*集(?:\s*[｜|]\s*(.*))?$')
RE_SUMMARY = re.compile(r'^本集概要[：:]\s*(.*)$')
RE_SCENE = re.compile(r'^(\d+)-(\d+)\s+(.+?)\s+(内|外|内外)\s+(\S+)$')
RE_CHARS = re.compile(r'^人物[：:]\s*(.*)$')
RE_DIALOG = re.compile(r'^([^：:▲]{1,15}?)\s*(?:（([^）]*)）)?\s*(?:\[(VO|OS)\])?\s*[：:]\s*(.*)$')


def parse(path):
    doc = docx.Document(path)
    paras = [p.text.strip() for p in doc.paragraphs if p.text.strip()]

    result = {'title': '', 'episodes': [], 'warnings': []}
    ep = None
    scene = None

    for line in paras:
        m = RE_EPISODE.match(line)
        if m:
            ep = {'episode': int(m.group(1)), 'title': m.group(2), 'summary': '', 'scenes': []}
            result['episodes'].append(ep)
            scene = None
            continue
        if ep is None:
            # 集标题之前的内容视为剧名
            result['title'] = result['title'] or line
            continue
        m = RE_SUMMARY.match(line)
        if m:
            ep['summary'] = m.group(1)
            continue
        m = RE_SCENE.match(line)
        if m:
            scene = {
                'scene_id': f'{m.group(1)}-{m.group(2)}',
                'location': m.group(3),
                'int_ext': m.group(4),
                'time': m.group(5),
                'characters': [],
                'lines': [],
            }
            ep['scenes'].append(scene)
            continue
        if scene is None:
            result['warnings'].append(f'第{ep["episode"]}集场头前的未识别行: {line}')
            continue
        m = RE_CHARS.match(line)
        if m:
            scene['characters'] = [c.strip() for c in re.split(r'[、，,]', m.group(1)) if c.strip()]
            continue
        if line.startswith('▲'):
            scene['lines'].append({'type': 'action', 'text': line.lstrip('▲').strip()})
            continue
        m = RE_DIALOG.match(line)
        if m:
            scene['lines'].append({
                'type': 'dialog',
                'speaker': m.group(1).strip(),
                'emotion': m.group(2) or '',
                'voice': m.group(3) or '',
                'text': m.group(4),
            })
            continue
        scene['lines'].append({'type': 'other', 'text': line})
        result['warnings'].append(f'{scene["scene_id"]} 未识别行: {line}')

    return result


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    data = parse(sys.argv[1])
    with open(sys.argv[2], 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=1)

    n_scenes = sum(len(e['scenes']) for e in data['episodes'])
    print(f'剧名: {data["title"]}')
    print(f'集数: {len(data["episodes"])}  场次: {n_scenes}')
    print(f'出场人物(人物行汇总): {"、".join(sorted({c for e in data["episodes"] for s in e["scenes"] for c in s["characters"]}))}')
    print(f'场景名(去重前): {len({s["location"] for e in data["episodes"] for s in e["scenes"]})} 个')
    for w in data['warnings']:
        print('警告:', w)


if __name__ == '__main__':
    main()
