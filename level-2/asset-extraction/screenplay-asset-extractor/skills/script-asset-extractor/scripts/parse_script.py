#!/usr/bin/env python3
"""把标准剧本 docx 解析为按场次组织的 JSON。

用法:
    python3 parse_script.py <剧本.docx> <输出scenes.json>

标准剧本格式:
    第 N 集｜标题          （分隔符也可为 ・ · 或空格）
    本集概要：……
    N-M 场景名 内/外 时间
    人物：A、B、C          （也可写 出场人物：）
    ▲ 动作描述
    【音效】/【配乐】……     （单独成行的标注）
    角色（情绪）[VO/OS]：台词

「【旁白】张三：……」按张三的台词解析，【旁白】记入 emotion。
行内 Markdown 粗体 ** 会被去除。首场之前的设定、大纲等段落记为 preamble：
仍须逐条复核，但不计入未识别比例和连续未识别门槛。
"""
import json
import re
import sys
import hashlib
from pathlib import Path

import docx

RE_EPISODE = re.compile(r'^第\s*([0-9]+|[零一二三四五六七八九十百两]+)\s*集(?:\s*[｜|・·：:]\s*(.*)|\s+(.+))?$')
RE_SUMMARY = re.compile(r'^本集概要[：:]\s*(.*)$')
TIME = r'(?:清晨|早晨|上午|中午|下午|傍晚|黄昏|深夜|凌晨|白天|夜晚|日|夜|晨|午|晚)'
INOUT = r'(?:内外|外内|内/外|外/内|内景|外景|内|外)'
RE_SCENE_ID = re.compile(r'^(\d+)\s*[-－—–]\s*(\d+)\s*(.*)$')
# 「1-1 夜 外 乱葬岗」「1-1 日内 酒楼」「50-1 十年后 日 外 御花园」：时间在前，可带前缀。
RE_TIME_FIRST = re.compile(rf'^(?:(\S+)\s+)?({TIME})\s*({INOUT})\s+(.+)$')
# 「1-1 客厅 内 日」：地点在前。
RE_PLACE_FIRST = re.compile(r'^(.+?)\s+(内景|外景|内外|内|外)\s+(\S+)$')
RE_CHARS = re.compile(r'^(?:出场)?人物[：:]\s*(.*)$')
RE_CUE = re.compile(r'^【[^】]{1,10}】')
# 声音、字幕等不含画面的标注；其余【景别/特写/镜头…】行描述画面，按动作行处理。
RE_NON_VISUAL = re.compile(r'^【(?:音效|配乐|音乐|BGM|环境音|人名条|字幕|花字|旁白)')
# 疑似场头（含漏空格、全角连字符）：首场前出现时说明场头格式写错，不能当作设定区放过。
RE_SCENE_LIKE = re.compile(r'^\d+\s*[-－—–]\s*\d+')
RE_DIALOG = re.compile(r'^([^：:▲【]{1,15}?)\s*(?:（([^）]*)）)?\s*(?:\[(VO|OS)\])?\s*[：:]\s*(.*)$')
CN_DIGITS = {'零': 0, '一': 1, '二': 2, '两': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9}


def episode_number(text):
    """阿拉伯数字或中文数字（第二十四集）转为集号。"""
    if text.isdigit():
        return int(text)
    total, current = 0, 0
    for char in text:
        if char in CN_DIGITS:
            current = CN_DIGITS[char]
        elif char == '十':
            total += (current or 1) * 10; current = 0
        elif char == '百':
            total += (current or 1) * 100; current = 0
    return total + current


def scene_header(text):
    """返回 (场次号, 地点, 内外, 时间)；不是场头返回 None。缺内外/时间时对应值为空。"""
    m = RE_SCENE_ID.match(text)
    if not m or not m.group(3).strip():
        return None
    sid, rest = f'{m.group(1)}-{m.group(2)}', m.group(3).strip()
    t = RE_TIME_FIRST.match(rest)
    if t:
        prefix, time, inout, place = t.groups()
        time = f'{prefix}·{time}' if prefix else time
        return sid, place.strip(), inout.replace('内景', '内').replace('外景', '外'), time
    p = RE_PLACE_FIRST.match(rest)
    if p:
        return sid, p.group(1).strip(), p.group(2).replace('内景', '内').replace('外景', '外'), p.group(3)
    return sid, rest, '', ''


def _markdown_paragraphs(path):
    """Read the supported Markdown screenplay subset without losing source line numbers."""
    rows = []
    for index, raw in enumerate(Path(path).read_text(encoding='utf-8-sig').splitlines(), 1):
        line = raw.strip()
        if not line or line == '---':
            continue
        # Markdown headings and blockquotes are presentation, not screenplay content.
        line = re.sub(r'^#{1,6}\s*', '', line)
        line = re.sub(r'^>\s*', '', line)
        line = re.sub(r'^\*+(.*?)\*+$', r'\1', line)
        line = line.replace('**', '').strip()
        line = line.replace('\\-', '-').replace('\\.', '.')
        if line:
            rows.append((index, line))
    return rows, []


def _docx_paragraphs(path):
    doc = docx.Document(path)
    return [(i, p.text.strip()) for i, p in enumerate(doc.paragraphs, 1) if p.text.strip()], doc


def parse(path):
    path = Path(path)
    if path.suffix.lower() in ('.md', '.markdown'):
        paras, doc = _markdown_paragraphs(path)
        tables = []
    else:
        paras, doc = _docx_paragraphs(path)
        tables = doc.tables

    result = {'title': '', 'episodes': [], 'warnings': []}
    ep = None
    scene = None
    unknown = []
    run, maximum_run = 0, 0
    scene_like_preamble = []
    incomplete, mismatched = [], []

    def unrecognized(index, text, preamble=False):
        nonlocal run, maximum_run
        item = {'paragraph': index, 'text': text}
        if preamble:
            # 首场前的设定/大纲区：保留复核，不计入质量门槛。
            item['preamble'] = True
            unknown.append(item)
            # 场头、动作行、人物行出现在首场前，说明某个场头没被识别、整场正文落进了设定区。
            if (RE_SCENE_LIKE.match(text.lstrip('▲').strip()) or text.startswith('▲')
                    or RE_CHARS.match(text)):
                scene_like_preamble.append(text)
            return
        unknown.append(item)
        run += 1
        maximum_run = max(maximum_run, run)

    for index, line in paras:
        m = RE_EPISODE.match(line)
        if m:
            title = m.group(2) if m.group(2) is not None else m.group(3)
            ep = {'episode': episode_number(m.group(1)), 'title': title or None, 'summary': '', 'scenes': []}
            result['episodes'].append(ep)
            scene = None
            run = 0
            continue
        if ep is None:
            # 集标题之前的内容视为剧名
            if not result['title']:
                result['title'] = line
                run = 0
            else:
                unrecognized(index, line, preamble=True)
                result['warnings'].append(f'集标题前的未识别行: {line}')
            continue
        m = RE_SUMMARY.match(line)
        if m:
            ep['summary'] = m.group(1)
            run = 0
            continue
        scene_candidate = line[1:].strip() if line.startswith('▲') else line
        scene_candidate = re.sub(r'^\*+(.*?)\*+$', r'\1', scene_candidate)
        scene_candidate = scene_candidate.replace('\\-', '-').replace('\\.', '.')
        header = scene_header(scene_candidate)
        # 只有地点、缺时间内外的场头只在非动作行且不含冒号时接受，避免把「3-5个侍卫」之类当场头。
        if header and not header[2] and (line.startswith('▲') or re.search(r'[：:]', scene_candidate)):
            header = None
        if header:
            sid, location, int_ext, time = header
            scene = {'scene_id': sid, 'location': location, 'int_ext': int_ext, 'time': time,
                     'characters': [], 'lines': []}
            if not int_ext or not time:
                incomplete.append(f'{sid} {location}')
            if int(sid.split('-')[0]) != ep['episode']:
                mismatched.append(f'{sid}（位于第{ep["episode"]}集下）')
            ep['scenes'].append(scene)
            run = 0
            continue
        if scene is None:
            result['warnings'].append(f'第{ep["episode"]}集场头前的未识别行: {line}')
            unrecognized(index, line, preamble=True)
            continue
        m = RE_CHARS.match(line)
        if m:
            scene['characters'] = [c.strip() for c in re.split(r'[、，,]', m.group(1)) if c.strip()]
            run = 0
            continue
        if line.startswith('▲'):
            scene['lines'].append({'type': 'action', 'text': line.lstrip('▲').strip()})
            run = 0
            continue
        cue = RE_CUE.match(line)
        # 「【旁白】张三：……」这类后面跟着台词的行仍按台词解析，不能让说话人被吞进标注。
        if line.startswith('【') and not (cue and RE_DIALOG.match(line[cue.end():].strip())):
            # 【特写】【全景】【镜头：…】等描述画面，人物/道具可凭此出镜，记为动作行；
            # 声音、字幕和只有标签的转场标记（【闪回】【10年后】）记为标注行。
            visual = not RE_NON_VISUAL.match(line) and not re.fullmatch(r'【[^】]{1,10}】', line)
            scene['lines'].append({'type': 'action' if visual else 'cue', 'text': line})
            run = 0
            continue
        # 台词前的【旁白】等标注拆进 emotion，说话人只保留人物名，才能对上人物资产。
        tag = ''
        if cue:
            tag, line = cue.group(0)[1:-1], line[cue.end():].strip()
        m = RE_DIALOG.match(line)
        if m:
            speaker, paren, voice = m.group(1).strip(), m.group(2) or '', m.group(3) or ''
            # 「江岁欢os：」「黑衣人A（VO）：」等写法：画外音标记归入 voice，说话人只留人物名。
            # 前面须是空格或非拉丁字母，避免把英文名 Marcos 拆成 Marc + OS。
            suffix = re.fullmatch(r'(.+?)(?:\s+|(?<![A-Za-z]))(os|vo)', speaker, re.I)
            if not voice and suffix:
                speaker, voice = suffix.group(1), suffix.group(2).upper()
            if not voice and paren.strip().upper() in ('OS', 'VO'):
                voice, paren = paren.strip().upper(), ''
            emotion = '；'.join(x for x in (tag, paren) if x)
            scene['lines'].append({
                'type': 'dialog',
                'speaker': speaker,
                'emotion': emotion,
                'voice': voice,
                'text': m.group(4),
            })
            run = 0
            continue
        scene['lines'].append({'type': 'other', 'text': line})
        result['warnings'].append(f'{scene["scene_id"]} 未识别行: {line}')
        unrecognized(index, line)

    table_text = [cell.text.strip() for table in tables for row in table.rows
                  for cell in row.cells if cell.text.strip()]
    preamble_count = sum(1 for item in unknown if item.get('preamble'))
    result['parse_report'] = {'nonempty_paragraphs': len(paras),
                              'unrecognized_count': len(unknown),
                              'preamble_count': preamble_count,
                              'max_consecutive_unrecognized': maximum_run,
                              'unrecognized': unknown,
                              'scene_like_preamble': scene_like_preamble,
                              'empty_episodes': [ep['episode'] for ep in result['episodes'] if not ep['scenes']],
                              'incomplete_headers': incomplete,
                              'mismatched_episodes': mismatched,
                              'table_text_count': len(table_text)}
    if incomplete:
        result['warnings'].append(f'场头缺少时间或内外，表格中留空：{incomplete}')
    source = path.resolve()
    result['source'] = {'path': str(source), 'sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                        'format': source.suffix.lower().lstrip('.') or 'unknown'}
    return result


def quality_errors(data):
    errors = []
    if not data.get('episodes') or not any(ep.get('scenes') for ep in data.get('episodes', [])):
        errors.append('解析结果为 0 集或 0 场，不能继续')
    report = data.get('parse_report', {})
    preamble = report.get('preamble_count', 0)
    total = report.get('nonempty_paragraphs', 0) - preamble
    if total > 0 and (report.get('unrecognized_count', 0) - preamble) / total > 0.05:
        errors.append('未识别段落超过非空段落总数的 5%，须修正规范格式后重新解析')
    ids = [s['scene_id'] for ep in data.get('episodes', []) for s in ep.get('scenes', [])]
    duplicated = sorted({sid for sid in ids if ids.count(sid) > 1})
    if duplicated:
        errors.append(f'场次号重复：{duplicated}，须在剧本中改为唯一场次号')
    if report.get('mismatched_episodes'):
        errors.append(f'场次号与所在集不符，可能漏了集标题：{report["mismatched_episodes"][:5]}')
    if report.get('empty_episodes'):
        errors.append(f'第 {report["empty_episodes"]} 集没有识别出任何场次，检查场头格式（如「1-1 客厅 内 日」）')
    if report.get('scene_like_preamble'):
        errors.append(f'某集首场前出现场头、动作行或人物行，可能有场头格式写错（如「1-1 客厅 内 日」漏空格）：{report["scene_like_preamble"][:3]}')
    if report.get('max_consecutive_unrecognized', 0) >= 10:
        errors.append('连续至少 10 行无法解析，须修正规范格式后重新解析')
    if report.get('table_text_count', 0):
        errors.append('DOCX 表格中存在正文，当前解析器不能保证覆盖；请转换为标准段落后重试')
    return errors


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    output = Path(sys.argv[2]).resolve()
    if output == Path(sys.argv[1]).resolve() or output.suffix.lower() != '.json':
        sys.exit('错误: 解析输出须为独立的 .json 文件，不能覆盖原始 DOCX')
    data = parse(sys.argv[1])
    errors = quality_errors(data)
    if errors:
        for error in errors:
            print('错误:', error)
        print(json.dumps(data['parse_report'], ensure_ascii=False, indent=2))
        sys.exit(1)
    with open(output, 'w', encoding='utf-8') as f:
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
