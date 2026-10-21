#!/usr/bin/env python3
"""校验 assets.json 并生成剧本资产表 Excel。

用法:
    python3 build_xlsx.py <scenes.json> <assets.json> <输出.xlsx>
    python3 build_xlsx.py <scenes.json> <assets.json> --check   # 只校验不输出

输出 4 个 sheet: 人物 / 场景 / 道具 / 场次总表
"""
import json
import sys

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

KINDS = [
    # (assets.json 键, sheet 名, 名称列标题, 专属列)
    ('characters', '人物', '人物名', [('role', '角色类型')]),
    ('scenes', '场景', '场景名', [('int_ext', '内/外'), ('times', '时间')]),
    ('props', '道具', '道具名', [('owner', '归属人物')]),
]

HEADER_FILL = PatternFill('solid', fgColor='305496')
GROUP_FILLS = [PatternFill('solid', fgColor='FFFFFF'), PatternFill('solid', fgColor='EEF3FA')]
WARN_FILL = PatternFill('solid', fgColor='FCE4D6')
THIN = Side(style='thin', color='BFBFBF')
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
WRAP = Alignment(wrap_text=True, vertical='center', horizontal='center')


def scene_key(sid):
    a, b = sid.split('-')
    return int(a), int(b)


def episodes_of(scene_ids):
    return sorted({scene_key(s)[0] for s in scene_ids})


def join(v):
    return '、'.join(v) if isinstance(v, list) else (v or '')


def unit_count(asset, kind):
    """这个资产占几行：场景按 subscenes 优先、否则按 states；人物/道具按 states。"""
    if kind == 'scenes' and asset.get('subscenes'):
        return len(asset['subscenes'])
    return len(asset.get('states', []))


def scene_units(asset):
    """统一取出一个场景资产的可迭代单元列表：subscenes 优先，否则把 states 包成同样的形状。"""
    if asset.get('subscenes'):
        return asset['subscenes']
    return [{'name': asset.get('name', ''), 'description': st.get('description', ''), 'scenes': st.get('scenes', [])}
            for st in asset.get('states', [])] or [{'name': asset.get('name', ''), 'description': asset.get('description', ''), 'scenes': []}]


def validate(scenes_data, assets):
    """返回 (错误列表, 警告列表)。错误会阻止生成 Excel。"""
    errors, warnings = [], []
    all_scenes = {s['scene_id']: s for e in scenes_data['episodes'] for s in e['scenes']}

    for kind, label, _, _ in KINDS:
        seen_ids = set()
        for a in assets.get(kind, []):
            aid = a.get('id', '?')
            if aid in seen_ids:
                errors.append(f'[{label}] 资产ID重复: {aid}')
            seen_ids.add(aid)

            # 场景支持两种结构：subscenes（主子场景）或 states（独立场景）
            if kind == 'scenes':
                has_subscenes = bool(a.get('subscenes'))
                has_states = bool(a.get('states'))
                if not has_subscenes and not has_states:
                    errors.append(f'[{label}] {aid} {a.get("name")} 既没有子场景也没有状态')
                # int_ext/times 是场景表的必填列，主子场景结构下最容易在手工建主场景时漏写
                if not a.get('int_ext'):
                    errors.append(f'[{label}] {aid} {a.get("name")} 缺少 int_ext（内/外）')
                if not a.get('times'):
                    errors.append(f'[{label}] {aid} {a.get("name")} 缺少 times（时间）')
                # 检查子场景引用的场次
                for sub in a.get('subscenes', []):
                    for sid in sub.get('scenes', []):
                        if sid not in all_scenes:
                            errors.append(f'[{label}] {aid} 子场景「{sub.get("name")}」引用了不存在的场次 {sid}')
            else:
                # 人物和道具必须有状态
                if not a.get('states'):
                    errors.append(f'[{label}] {aid} {a.get("name")} 没有任何状态')

            # 检查 states 引用的场次
            for st in a.get('states', []):
                for sid in st.get('scenes', []):
                    if sid not in all_scenes:
                        errors.append(f'[{label}] {aid}-{st.get("id")} 引用了不存在的场次 {sid}')

    # 人物行中的每个名字都要能对上人物资产（名称或别名）
    name_map = {}
    for a in assets.get('characters', []):
        for n in [a['name']] + a.get('aliases', []):
            name_map[n] = a
    for sid, s in all_scenes.items():
        for c in s['characters']:
            if c not in name_map:
                warnings.append(f'{sid} 人物行中的「{c}」没有对应的人物资产')
                continue
            a = name_map[c]
            if not any(sid in st.get('scenes', []) for st in a['states']):
                warnings.append(f'{sid} 「{c}」出场但没有分配到任何状态')

    # 反向校验：人物状态里分配的场次，该人物行必须真的标注了出场
    # 这能抓出「错误地把场次塞进了状态」的问题（例如状态数据手工编辑出错）
    for a in assets.get('characters', []):
        for st in a.get('states', []):
            for sid in st.get('scenes', []):
                scene = all_scenes.get(sid)
                if scene and a['name'] not in scene['characters'] and not any(
                        al in scene['characters'] for al in a.get('aliases', [])):
                    warnings.append(
                        f'{sid} 「{a["name"]}」的状态 {st.get("id")} 引用了此场次，'
                        f'但剧本人物行里没有「{a["name"]}」出场')

    # 道具的弱反向校验：道具标了 owner 时，owner 通常该在那一场出场（允许道具脱离
    # owner 单独出镜的情况，比如被别人捡起/收走，所以降级为提示而非强校验，
    # 命中时不代表一定错，但值得回查原文确认）
    for a in assets.get('props', []):
        owner = a.get('owner')
        if not owner:
            continue
        for st in a.get('states', []):
            for sid in st.get('scenes', []):
                scene = all_scenes.get(sid)
                if scene and owner not in scene['characters']:
                    warnings.append(
                        f'{sid} 道具「{a["name"]}」的归属人物「{owner}」未在此场次人物行中出现，'
                        f'回查原文确认该场次道具是否确由他人持有或场次号是否有误')

    # 每个场次都要有场景资产覆盖（检查 subscenes 和 states）
    covered = set()
    for a in assets.get('scenes', []):
        # 从 subscenes 收集场次
        for sub in a.get('subscenes', []):
            covered.update(sub.get('scenes', []))
        # 从 states 收集场次
        for st in a.get('states', []):
            covered.update(st.get('scenes', []))

    for sid in all_scenes:
        if sid not in covered:
            warnings.append(f'{sid} 没有分配场景资产')

    # 检查 note 是否包含判断过程（应该只写需要人工确认的不确定内容）
    note_keywords = ['因此', '所以', '按规则', '已判断', '归类为', '因为']
    for kind, label, _, _ in KINDS:
        for a in assets.get(kind, []):
            # 检查资产级别的 note
            note = a.get('note', '')
            if note and any(kw in note for kw in note_keywords):
                warnings.append(f'[{label}] {a.get("id")} {a.get("name")} 的 note 疑似包含判断过程，应只写需要人工确认的不确定内容')
            # 检查状态级别的 note
            for st in a.get('states', []):
                st_note = st.get('note', '')
                if st_note and any(kw in st_note for kw in note_keywords):
                    warnings.append(f'[{label}] {a.get("id")}-{st.get("id")} 的 note 疑似包含判断过程，应只写需要人工确认的不确定内容')

    # 检查主角和主要配角的 description 完整性
    desc_keywords = ['岁', '发', '眼', '衣', '裙', '袍', '甲', '气质', '装']
    for a in assets.get('characters', []):
        if a.get('role') in ['主角', '主要配角']:
            desc = a.get('description', '')
            if len(desc) < 50:
                warnings.append(f'[人物] {a.get("id")} {a.get("name")} 的基础描述字数过少（{len(desc)}字），可能不完整')
            elif not any(kw in desc for kw in desc_keywords):
                warnings.append(f'[人物] {a.get("id")} {a.get("name")} 的基础描述缺少关键外观要素，建议检查是否完整')
            # 检查状态描述
            for st in a.get('states', []):
                st_desc = st.get('description', '')
                if len(st_desc) < 50:
                    warnings.append(f'[人物] {a.get("id")}-{st.get("id")} {a.get("name")}·{st.get("name")} 的状态描述字数过少（{len(st_desc)}字），可能不完整')

    return errors, warnings


def style_header(ws, headers, widths):
    ws.append(headers)
    for i, cell in enumerate(ws[1]):
        cell.font = Font(bold=True, color='FFFFFF')
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        cell.border = BORDER
        ws.column_dimensions[cell.column_letter].width = widths[i]
    ws.freeze_panes = 'C2'
    ws.row_dimensions[1].height = 24


def calculate_cell_height(text, width):
    """根据文本内容和列宽计算合适的行高"""
    if not text:
        return 15

    # 中文字符约等于2个英文字符宽度
    char_count = sum(2 if ord(c) > 127 else 1 for c in str(text))
    # Excel列宽单位大约是8.43像素，字符宽度约7像素
    chars_per_line = int(width * 1.2)
    lines = max(1, char_count // chars_per_line + (1 if char_count % chars_per_line else 0))

    # 每行约15点高度，最小15，最大150
    return min(150, max(18, lines * 15))


def write_asset_sheet(wb, kind, sheet_name, name_col, extra_cols, assets):
    ws = wb.create_sheet(sheet_name)

    # 场景 sheet 特殊处理：精简列，子场景替代状态
    if kind == 'scenes':
        headers = ['场景ID', '主场景名', '子场景名', '内/外', '时间', '子场景描述', '出现场次', '备注']
        # 优化列宽：场景ID适当加宽，描述列加宽以容纳更多内容
        widths = [12, 20, 20, 8, 10, 50, 25, 30]
    else:
        headers = ['资产ID', name_col, '别名/称谓'] + [h for _, h in extra_cols] + [
            '基础设定', '状态ID', '状态名', '状态描述', '出现场次', '原文依据', '备注']
        # 优化列宽：描述列加宽，出现场次适当缩小
        widths = [12, 16, 18] + [12] * len(extra_cols) + [45, 18, 18, 45, 25, 50, 30]

    style_header(ws, headers, widths)

    for gi, a in enumerate(assets.get(kind, [])):
        fill = GROUP_FILLS[gi % 2]
        start_row = ws.max_row + 1

        # 场景特殊处理：按子场景展开行
        if kind == 'scenes':
            subscenes = a.get('subscenes', [])
            if not subscenes:
                # 没有子场景，从 states 获取场次
                state_scenes = []
                for st in a.get('states', []):
                    state_scenes.extend(st.get('scenes', []))
                subscenes = [{
                    'name': a['name'],
                    'description': a.get('description', ''),
                    'scenes': sorted(set(state_scenes), key=scene_key)
                }]

            for i, sub in enumerate(subscenes):
                sids = sorted(sub.get('scenes', []), key=scene_key)
                # 子场景没有 description 字段，需要从主场景获取或留空
                sub_desc = sub.get('description', '')

                if i == 0:
                    # 第一行：显示场景ID和主场景名
                    row = [
                        a['id'],
                        a['name'],
                        sub['name'],
                        join(a.get('int_ext', '')),
                        join(a.get('times', '')),
                        sub_desc,
                        join(sids),
                        a.get('note', ''),
                    ]
                else:
                    # 后续行：场景ID和主场景名留空
                    row = [
                        '',
                        '',
                        sub['name'],
                        '',
                        '',
                        sub_desc,
                        join(sids),
                        '',
                    ]
                ws.append(row)

            # 应用样式并调整行高（场景表）
            for row_idx in range(start_row, ws.max_row + 1):
                max_height = 18
                for col_idx, cell in enumerate(ws[row_idx], 1):
                    cell.fill = fill
                    cell.alignment = WRAP
                    cell.border = BORDER
                    # 计算这个单元格需要的高度
                    col_width = widths[col_idx - 1]
                    cell_height = calculate_cell_height(cell.value, col_width)
                    max_height = max(max_height, cell_height)
                # 设置这一行的高度为所有单元格中的最大值
                ws.row_dimensions[row_idx].height = max_height

            # 合并单元格（场景ID、主场景名、内/外、时间、备注）
            if len(subscenes) > 1:
                end_row = start_row + len(subscenes) - 1
                for col_idx in [1, 2, 4, 5, 8]:  # 场景ID、主场景名、内/外、时间、备注
                    cell = ws.cell(start_row, col_idx)
                    ws.merge_cells(start_row=start_row, end_row=end_row, start_column=col_idx, end_column=col_idx)
                    cell.alignment = Alignment(wrap_text=True, vertical='center', horizontal='center')
        else:
            # 人物、道具按原逻辑（按状态展开）
            states = a['states']
            for i, st in enumerate(states):
                sids = sorted(st.get('scenes', []), key=scene_key)
                if i == 0:
                    # 第一行：显示完整资产信息
                    row = [a['id'], a['name'], join(a.get('aliases', []))]
                    row += [join(a.get(k, '')) for k, _ in extra_cols]
                    row += [a.get('description', '')]
                else:
                    # 后续行：资产基础信息留空，等待合并
                    base_cols = 3 + len(extra_cols) + 1  # ID、名称、别名、专属列、基础设定
                    row = [''] * base_cols

                row += [
                    f'{a["id"]}-{st["id"]}',
                    st.get('name', ''),
                    st.get('description', ''),
                    join(sids),
                    st.get('evidence', ''),
                    join([x for x in [a.get('note', ''), st.get('note', '')] if x]),
                ]
                ws.append(row)

            # 应用样式并调整行高（人物/道具表）
            for row_idx in range(start_row, ws.max_row + 1):
                max_height = 18
                for col_idx, cell in enumerate(ws[row_idx], 1):
                    cell.fill = fill
                    cell.alignment = WRAP
                    cell.border = BORDER
                    # 计算这个单元格需要的高度
                    col_width = widths[col_idx - 1]
                    cell_height = calculate_cell_height(cell.value, col_width)
                    max_height = max(max_height, cell_height)
                # 设置这一行的高度为所有单元格中的最大值
                ws.row_dimensions[row_idx].height = max_height

            # 合并同一资产的基础信息单元格
            if len(states) > 1:
                end_row = ws.max_row
                merge_cols = 3 + len(extra_cols) + 1  # ID、名称、别名、专属列、基础设定
                for col_idx in range(1, merge_cols + 1):
                    cell = ws.cell(start_row, col_idx)
                    ws.merge_cells(start_row=start_row, start_column=col_idx,
                                  end_row=end_row, end_column=col_idx)
                    cell.alignment = Alignment(wrap_text=True, vertical='center', horizontal='center')

    ws.auto_filter.ref = ws.dimensions


def write_breakdown(wb, scenes_data, assets):
    ws = wb.create_sheet('场次总表')
    headers = ['场次', '集', '集标题', '场景名(剧本)', '内/外', '时间', '场景资产·状态', '人物·状态', '道具·状态', '待处理']
    style_header(ws, headers, [8, 6, 20, 22, 7, 7, 26, 44, 36, 30])

    def lookup(kind, sid):
        out = []
        for a in assets.get(kind, []):
            units = scene_units(a) if kind == 'scenes' else a.get('states', [])
            for st in units:
                if sid in st.get('scenes', []):
                    out.append((a, st))
        return out

    name_map = {n: a for a in assets.get('characters', []) for n in [a['name']] + a.get('aliases', [])}

    for ep in scenes_data['episodes']:
        for s in ep['scenes']:
            sid = s['scene_id']
            scn = lookup('scenes', sid)
            chars = lookup('characters', sid)
            props = lookup('props', sid)
            todo = []
            for c in s['characters']:
                a = name_map.get(c)
                if a is None:
                    todo.append(f'人物「{c}」无资产')
                elif not any(x[0] is a for x in chars):
                    todo.append(f'人物「{c}」无状态')
            if not scn:
                todo.append('无场景资产')
            ws.append([
                sid, ep['episode'], ep['title'], s['location'], s['int_ext'], s['time'],
                '\n'.join(f'{a["name"]}·{st["name"]}' for a, st in scn),
                '\n'.join(f'{a["name"]}·{st["name"]}' for a, st in chars),
                '\n'.join(f'{a["name"]}·{st["name"]}' for a, st in props),
                '\n'.join(todo),
            ])
            for cell in ws[ws.max_row]:
                cell.alignment = WRAP
                cell.border = BORDER
                if todo:
                    cell.fill = WARN_FILL
    ws.auto_filter.ref = ws.dimensions


def main():
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    with open(sys.argv[1], encoding='utf-8') as f:
        scenes_data = json.load(f)
    with open(sys.argv[2], encoding='utf-8') as f:
        assets = json.load(f)

    errors, warnings = validate(scenes_data, assets)
    for e in errors:
        print('错误:', e)
    for w in warnings:
        print('警告:', w)
    counts = {label: (len(assets.get(k, [])), sum(unit_count(a, k) for a in assets.get(k, [])))
              for k, label, _, _ in KINDS}
    print('统计:', '  '.join(f'{l} {n}个/{m}状态' for l, (n, m) in counts.items()))
    print(f'错误 {len(errors)} 条，警告 {len(warnings)} 条')
    if errors:
        sys.exit(1)
    if sys.argv[3] == '--check':
        return

    wb = Workbook()
    wb.remove(wb.active)
    for kind, sheet_name, name_col, extra in KINDS:
        write_asset_sheet(wb, kind, sheet_name, name_col, extra, assets)
    write_breakdown(wb, scenes_data, assets)
    wb.save(sys.argv[3])
    print('已生成:', sys.argv[3])


if __name__ == '__main__':
    main()
