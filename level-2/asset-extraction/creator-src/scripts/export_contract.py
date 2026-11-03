"""资产表的唯一展示契约：纯数据计划供不同 Excel 后端消费，不修改资产。"""
import math
import re
from itertools import groupby
from character_ledger import segment_position
from prop_identity import identity_text, prop_state_notes
from warning_approvals import approval_text
from design_fields import SUBSCENE, PROP_BASE, PROP_STATE, SCENE_STATE, character_fields, combined_text, design_text

STYLE = {'font': 'Arial', 'font_size': 10, 'header_fill': '305496',
         'group_fills': ['FFFFFF', 'EEF3FA'], 'border': 'BFBFBF',
         'header_height': 30, 'minimum_height': 24, 'maximum_height': 409,
         'line_height': 15, 'padding': 8, 'freeze': 'C2'}
HEADERS = {
    '人物': ['资产ID', '人物名', '别名/称谓', '角色类型', '基础设定', '状态ID',
           '状态名', '状态描述', '出现场次', '原文依据', '备注', '场次·阶段·时间线', '出场次数'],
    '场景': ['场景ID', '主场景名', '子场景名', '内/外', '时间', '子场景描述', '出现场次', '备注'],
    '道具': ['资产ID', '道具名', '别名/称谓', '归属人物', '基础设定', '状态ID',
           '状态名', '状态描述', '出现场次', '原文依据', '备注', '异称与身份依据'],
    '场次总表': ['场次', '集', '集标题', '场景名(剧本)', '内/外', '时间', '场景资产·状态',
              '人物·状态', '道具·状态', '待处理', '校验确认', '原文人物行', '逐场备注']}
# 基础设定、状态描述、子场景描述同时承载【原文】【设计】两段，列宽相应加宽。
WIDTHS = {'人物': [12, 16, 18, 12, 56, 19, 24, 56, 25, 46, 54, 68, 12],
          '场景': [12, 24, 20, 8, 10, 60, 25, 54],
          '道具': [12, 24, 18, 12, 56, 19, 22, 56, 25, 46, 52, 60],
          '场次总表': [9, 6, 14, 24, 8, 8, 40, 68, 52, 26, 42, 30, 58]}
TEXT_COLUMNS = {'人物': [5, 8, 10, 11, 12], '场景': [6, 8],
                '道具': [5, 8, 10, 11, 12], '场次总表': [7, 8, 9, 10, 11, 12, 13]}


def join(value):
    return '、'.join(value) if isinstance(value, list) else (value or '')


def ordered_records(character, order, state=None):
    return sorted((r for r in character.get('appearances', [])
                   if state is None or r['state_id'] == state),
                  key=lambda r: (order[r['scene_id']], r['start_line'], r.get('start_offset', 0)))


def first_use(character, order, state=None):
    records = ordered_records(character, order, state)
    return (order[records[0]['scene_id']], records[0]['start_line'], records[0].get('start_offset', 0)) if records else (math.inf, 0, 0)


def stage_text(record, state):
    # 只省略可从场次/状态名无歧义还原的重复项，不合并跨阶段记录。
    timeline = record['timeline']
    if timeline == record['scene_id'] + '·原文时间段':
        timeline = '本场原文时间段'
    elif timeline == '当前画面·' + record['scene_id']:
        timeline = record['scene_id']
    instance = '' if record['instance'] == '本体' else '/' + record['instance']
    segment = '' if record.get('segment') == state['name'] else '：' + record.get('segment', '')
    return f'{record["scene_id"]} {segment_position(record)} {timeline}{instance}{segment}'


def stage_summary(records, state):
    text = '；'.join(stage_text(r, state) for r in records)
    return ('实体未另标时为本体；阶段未另标时同状态名。\n' + text) if records else ''


def local_notes(records):
    # 只压缩输入序列中相邻且相同的备注；不把远处记录拖到前面。
    groups = groupby((r for r in records if r.get('note')), key=lambda r: r['note'])
    def compact(note):
        return note.replace('该阶段衣着及生理外观未明示，不能从其他时间/场景推断。',
                            '衣着/生理外观未明示，不能跨场次推断。')
    return '\n'.join('、'.join(f'{r["scene_id"]} {segment_position(r)}' for r in group)
                     + '：' + compact(note) for note, group in groups)


def labeled_notes(items):
    return '\n'.join('、'.join(label for label, _ in group) + '：' + note
                     for note, group in groupby(items, key=lambda item: item[1]) if note)


def text_lines(value, width):
    return sum(max(1, math.ceil(sum(1 if ord(c) < 128 else 2 for c in line) / max(1, width - 1)))
               for line in str(value or '').split('\n'))


MAX_LINES = (STYLE['maximum_height'] - STYLE['padding']) // STYLE['line_height']


def split_cell(value, width, limit=MAX_LINES):
    """按原有换行及「、；」保序切块，每块不超过 limit 行；不删字，只在块边界换行。"""
    text = str(value or '')
    if text_lines(text, width) <= limit:
        return [text]
    per_line = max(1, (width - 1) // 2)
    atoms = []
    for line in text.split('\n'):
        first = True
        for part in re.findall(r'[^、；]+[、；]?|[、；]', line) or ['']:
            # 单个片段本身超出时按字符宽度切，仍保持原顺序。
            while text_lines(part, width) > limit:
                atoms.append((part[:limit * per_line], first)); part = part[limit * per_line:]; first = False
            atoms.append((part, first)); first = False
    chunks, current = [], ''
    for part, newline in atoms:
        candidate = current + ('\n' if newline and current else '') + part
        if current and text_lines(candidate, width) > limit:
            chunks.append(current); current = part
        else:
            current = candidate
    chunks.append(current)
    return chunks


def expand_row(values, widths, keep, label_col, merged=()):
    """单行超出 Excel 行高时，把非 keep 列的长文本拆到续行；续行在 label_col 标「（续）」。"""
    parts = {col: split_cell(v, widths[col - 1]) for col, v in enumerate(values, 1)
             if col not in keep and col not in merged and isinstance(v, str)}
    count = max([len(p) for p in parts.values()] or [1])
    if count == 1:
        return [values]
    rows = []
    for i in range(count):
        row = list(values) if i == 0 else [None if v is None or isinstance(v, int) else '' for v in values]
        for col, chunks in parts.items():
            row[col - 1] = chunks[i] if i < len(chunks) else ''
        if i and values[label_col - 1]:
            row[label_col - 1] = f'{values[label_col - 1]}（续）'
        rows.append(row)
    return rows


def pad_group(rows, start, merge_columns, widths, label_col):
    """合并列（基础设定等）的文字比整组各行能容纳的还多时，补空白续行，不截断。"""
    first = rows[start - 2]
    needed = max([text_lines(first[col - 1], widths[col - 1]) for col in merge_columns] or [1])
    capacity = (len(rows) - start + 2) * MAX_LINES
    label = rows[start - 2][label_col - 1]
    while capacity < needed:
        rows.append([None if v is None or isinstance(v, int) else '' for v in first])
        if label:
            rows[-1][label_col - 1] = f'{label}（续）'
        capacity += MAX_LINES


def column_name(index):
    text = ''
    while index:
        index, remainder = divmod(index - 1, 26)
        text = chr(65 + remainder) + text
    return text


def sheet_plan(name, rows, groups):
    widths = WIDTHS[name]
    merged = {(row, col) for group in groups for col in group['merge_columns']
              for row in range(group['start'], group['end'] + 1)}
    heights = []
    for index, values in enumerate(rows, 2):
        lines = max([text_lines(v, widths[col - 1]) for col, v in enumerate(values, 1)
                     if (index, col) not in merged] or [1])
        heights.append(max(STYLE['minimum_height'], lines * STYLE['line_height'] + STYLE['padding']))
    for group in groups:
        for col in group['merge_columns']:
            needed = text_lines(rows[group['start'] - 2][col - 1], widths[col - 1]) * 15 + 8
            actual = sum(heights[group['start'] - 2:group['end'] - 1])
            # 合并单元格缺的高度依次分给组内各行，单行不超过上限。
            for index in range(group['start'] - 2, group['end'] - 1):
                if needed <= actual: break
                extra = min(needed - actual, STYLE['maximum_height'] - heights[index])
                if extra > 0:
                    heights[index] += extra; actual += extra
            if needed > actual:
                heights[group['start'] - 2] += needed - actual
    excessive = [i + 2 for i, height in enumerate(heights) if height > STYLE['maximum_height']]
    if excessive:
        raise ValueError(f'{name} 行{excessive}超出 Excel 行高；保序压缩重复项或申请调整展示，不能截断。')
    return {'name': name, 'headers': HEADERS[name], 'widths': widths, 'rows': rows,
            'groups': groups, 'row_heights': heights, 'text_columns': TEXT_COLUMNS[name],
            'freeze': STYLE['freeze'], 'filter': f'A1:{column_name(len(widths))}{len(rows) + 1}'}


def build_plan(data, assets, approvals=None):
    scenes = [s for e in data['episodes'] for s in e['scenes']]
    order = {s['scene_id']: i for i, s in enumerate(scenes)}
    def scene_ids(ids):
        found = set(ids)
        return [sid for sid in order if sid in found]
    chars = sorted(assets.get('characters', []), key=lambda c: (
        -len({r['scene_id'] for r in c.get('appearances', [])}), first_use(c, order)))
    sheets = []
    rows, groups = [], []
    merge = {'人物': [1, 2, 3, 4, 5, 13], '场景': [1, 2, 4, 5, 8], '道具': [1, 2, 3, 4, 5, 12]}
    for c in chars:
        start = len(rows) + 2
        base_fields, state_fields = character_fields(c)
        for i, state in enumerate(sorted(c['states'], key=lambda st: first_use(c, order, st['id']))):
            records = ordered_records(c, order, state['id'])
            notes = '\n'.join(x for x in [c.get('note'), state.get('note'), local_notes(records)] if x)
            base = ([c['id'], c['name'], join(c.get('aliases', [])), c.get('role', ''),
                     combined_text(c, base_fields)] if i == 0 else [''] * 5)
            rows.extend(expand_row(base + [c['id'] + '-' + state['id'], state['name'], combined_text(state, state_fields),
                        join(scene_ids(state['scenes'])), state.get('evidence', ''), notes,
                        stage_summary(records, state), len({r['scene_id'] for r in c['appearances']}) if i == 0 else None],
                        WIDTHS['人物'], keep={6, 7}, label_col=6, merged=set(merge['人物'])))
        pad_group(rows, start, merge['人物'], WIDTHS['人物'], label_col=6)
        groups.append({'start': start, 'end': len(rows) + 1, 'merge_columns': merge['人物']})
    sheets.append(sheet_plan('人物', rows, groups))
    rows, groups = [], []
    for a in assets.get('scenes', []):
        start = len(rows) + 2
        units = a.get('subscenes') or [{'name': a['name'], 'description': a.get('description', ''),
                 'design': a.get('design'), 'design_basis': a.get('design_basis', ''),
                 'scenes': scene_ids(sid for st in a.get('states', []) for sid in st['scenes'])}]
        notes = [a.get('note', '')]
        for st in a.get('states', []):
            notes.append(f'{st["id"]} {st["name"]}（{join(scene_ids(st["scenes"]))}）：{st.get("description", "")}')
            if st.get('evidence'): notes.append('依据：' + st['evidence'])
            if st.get('design'): notes.append('【设计】\n' + design_text(st, SCENE_STATE))
            if st.get('note'): notes.append('状态备注：' + st['note'])
        for i, sub in enumerate(units):
            rows.extend(expand_row([a['id'] if i == 0 else '', a['name'] if i == 0 else '', sub['name'],
                         join(a['int_ext']) if i == 0 else '', join(a['times']) if i == 0 else '',
                         combined_text(sub, SUBSCENE), join(scene_ids(sub['scenes'])),
                         '\n'.join(filter(None, notes)) if i == 0 else ''],
                         WIDTHS['场景'], keep={3}, label_col=3, merged=set(merge['场景'])))
        pad_group(rows, start, merge['场景'], WIDTHS['场景'], label_col=3)
        groups.append({'start': start, 'end': len(rows) + 1, 'merge_columns': merge['场景']})
    sheets.append(sheet_plan('场景', rows, groups))
    rows, groups = [], []
    for p in assets.get('props', []):
        start = len(rows) + 2
        for i, st in enumerate(p['states']):
            base = ([p['id'], p['name'], join(p.get('aliases', [])), p.get('owner', ''),
                     combined_text(p, PROP_BASE)] if i == 0 else [''] * 5)
            rows.extend(expand_row(base + [p['id'] + '-' + st['id'], st['name'], combined_text(st, PROP_STATE),
                        join(scene_ids(st['scenes'])), st.get('evidence', ''), prop_state_notes(p, st),
                        ('原文主称呼：' + p.get('source_name', p['name']) + '\n' + identity_text(p)).strip() if i == 0 else ''],
                        WIDTHS['道具'], keep={6, 7}, label_col=6, merged=set(merge['道具'])))
        pad_group(rows, start, merge['道具'], WIDTHS['道具'], label_col=6)
        groups.append({'start': start, 'end': len(rows) + 1, 'merge_columns': merge['道具']})
    sheets.append(sheet_plan('道具', rows, groups))
    rows, groups = [], []
    name_map = {name: c for c in chars for name in [c['name']] + c.get('aliases', [])}
    for episode in data['episodes']:
        for scene in episode['scenes']:
            sid = scene['scene_id']
            scn = [(a, st) for a in assets.get('scenes', []) for st in a.get('states', []) if sid in st['scenes']]
            subonly = [a for a in assets.get('scenes', []) if not a.get('states') and any(sid in sub['scenes'] for sub in a.get('subscenes', []))]
            records = [(c, r) for c in chars for r in ordered_records(c, order) if r['scene_id'] == sid]
            records.sort(key=lambda item: (item[1]['start_line'], item[1].get('start_offset', 0)))
            props = [(p, st) for p in assets.get('props', []) for st in p['states'] if sid in st['scenes']]
            todo = []
            for name in scene['characters']:
                c = name_map.get(name)
                if c is None: todo.append(f'人物「{name}」无资产')
                elif not any(x is c for x, _ in records): todo.append(f'人物「{name}」无状态')
            if not scn and not subonly: todo.append('无场景资产')
            character_lines = []
            for c, record in records:
                state = next(st for st in c['states'] if st['id'] == record['state_id'])
                basis = {'explicit': '原文明示', 'inherited': '连续沿用', 'unspecified': '未说明'}[record['basis']]
                character_lines.append(f'{c["name"]}·{state["name"]} [{segment_position(record)}；{record["timeline"]}/{record["instance"]}；{basis}]')
            prop_lines = []
            for p, st in props:
                raw = list(dict.fromkeys(m['raw_name'] for m in p['mentions'] if m['source']['scene_id'] == sid and m['visibility'] == 'visible' and m['state_id'] == st['id']))
                prop_lines.append(f'{p["name"]}·{st["name"]}（原文：{join(raw)}）')
            notes = [(f'{c["name"]} {segment_position(r)}', r['note']) for c, r in records if r.get('note')]
            notes.extend((f'{a["name"]}·{st["name"]}', st['note']) for a, st in scn if st.get('note'))
            notes.extend((p['name'], p['note']) for p, _ in props if p.get('note'))
            notes.extend((f'{p["name"]}·{st["name"]}', st['note']) for p, st in props if st.get('note'))
            # 同名但非本物件的命中只为名称核对，不进场次总表，避免误显示为该道具的提及。
            notes.extend((f'{p["name"]}:L{m["source"]["line"]}「{m["raw_name"]}」', m['note']) for p in assets.get('props', []) for m in p['mentions'] if m['source']['scene_id'] == sid and m.get('note') and m.get('visibility') != 'unrelated')
            if scene.get('voice_only'): notes.insert(0, ('仅声音/信息', join(scene['voice_only'])))
            start = len(rows) + 2
            rows.extend(expand_row([sid, episode['episode'], episode.get('title') or '', scene['location'], scene['int_ext'], scene['time'],
                         '\n'.join([f'{a["id"]} {a["name"]}·{st["id"]} {st["name"]}' for a, st in scn] + [a['name'] + '·子场景覆盖' for a in subonly]),
                         '\n'.join(character_lines), '\n'.join(prop_lines), '\n'.join(todo),
                         '\n'.join(approval_text(item) for item in approvals or [] if item['message'].startswith(sid + ' ') or (not rows and not any(item['message'].startswith(x + ' ') for x in order))),
                         join(scene.get('raw_characters', scene['characters'])), labeled_notes(notes)],
                         WIDTHS['场次总表'], keep={1, 2, 3, 4, 5, 6}, label_col=1))
            groups.append({'start': start, 'end': len(rows) + 1, 'merge_columns': []})
    sheets.append(sheet_plan('场次总表', rows, groups))
    return {'contract_version': 1, 'style': STYLE, 'sheets': sheets}
