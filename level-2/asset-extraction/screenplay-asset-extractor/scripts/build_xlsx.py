#!/usr/bin/env python3
"""校验 assets.json 并生成剧本资产表 Excel。

用法:
    python3 build_xlsx.py <scenes.json> <assets.json> <输出.xlsx>
    python3 build_xlsx.py <scenes.json> <assets.json> --check   # 只校验不输出
    python3 build_xlsx.py <scenes.json> <assets.json> --sync-character-scenes
    python3 build_xlsx.py <scenes.json> <assets.json> --sync-prop-scenes
    python3 build_xlsx.py <scenes.json> <assets.json> --warning-report
    python3 build_xlsx.py <scenes.json> <assets.json> <输出.xlsx> --warning-approvals <确认.json>

输出 4 个 sheet: 人物 / 场景 / 道具 / 场次总表
"""
import json
import sys
import argparse

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from character_ledger import character_breakdown, segment_position, state_notes, sync_characters, validate_characters
from asset_validation import input_errors
from warning_approvals import apply_approvals, approval_text, warning_id, warning_report
from prop_identity import identity_text, prop_state_notes, sync_props, validate_props
from pathlib import Path
from execution_review import load_review, validate_review, source_errors

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
    """返回 (错误列表, 警告列表)。任一非空均阻止生成 Excel。"""
    shape_errors = input_errors(scenes_data, assets)
    if shape_errors:
        return shape_errors, []
    errors, warnings = [], []
    scene_ids = [s['scene_id'] for e in scenes_data['episodes'] for s in e['scenes']]
    if len(scene_ids) != len(set(scene_ids)):
        errors.append('剧本存在重复场次号，须先修正解析结果，不能覆盖同号场次')
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

    # 逐场记录允许人物行出场或原文动作出镜；对白提及不证明出镜。
    ledger_errors, ledger_warnings = validate_characters(scenes_data, assets)
    errors.extend(ledger_errors)
    warnings.extend(ledger_warnings)
    prop_errors, prop_warnings = validate_props(scenes_data, assets)
    errors.extend(prop_errors)
    warnings.extend(prop_warnings)
    for a in assets.get('characters', []):
        for st in a.get('states', []):
            for sid in st.get('scenes', []):
                scene = all_scenes.get(sid)
                if scene and not any(r.get('scene_id') == sid and r.get('state_id') == st.get('id')
                                     for r in (a.get('appearances') or []) if isinstance(r, dict)):
                    warnings.append(
                        f'{sid} 「{a["name"]}」的状态 {st.get("id")} 引用了此场次，'
                        f'但没有对应逐场出镜记录')

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

    # 信息是否准确不以字数衡量；未知外观允许如实写未说明。
    for a in assets.get('characters', []):
        for st in a.get('states', []):
            if not st.get('description', '').strip():
                errors.append(f'[人物] {a.get("id")}-{st.get("id")} 缺少状态描述')

    return errors, warnings


def write_plan_sheet(wb, plan):
    """标准后端也消费同一展示契约，禁止再次维护独立列结构。"""
    from export_contract import STYLE
    ws = wb.create_sheet(plan['name'])
    ws.append(plan['headers'])
    for values in plan['rows']:
        ws.append(values)
    for index, width in enumerate(plan['widths'], 1):
        from openpyxl.utils import get_column_letter
        ws.column_dimensions[get_column_letter(index)].width = width
    for row in ws:
        for cell in row:
            cell.font = Font(name=STYLE['font'], size=STYLE['font_size'])
            cell.border = BORDER
            cell.alignment = Alignment(wrap_text=True, horizontal='center', vertical='center')
    for cell in ws[1]:
        cell.font = Font(name=STYLE['font'], size=STYLE['font_size'], bold=True, color='FFFFFF')
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    ws.row_dimensions[1].height = STYLE['header_height']
    for index, height in enumerate(plan['row_heights'], 2):
        ws.row_dimensions[index].height = height
    for index, group in enumerate(plan['groups']):
        for row in ws.iter_rows(min_row=group['start'], max_row=group['end']):
            for cell in row:
                cell.fill = GROUP_FILLS[index % 2]
        if group['end'] > group['start']:
            for col in group['merge_columns']:
                ws.merge_cells(start_row=group['start'], end_row=group['end'], start_column=col, end_column=col)
                cell = ws.cell(group['start'], col)
                cell.alignment = Alignment(wrap_text=True, horizontal='center', vertical='center')
    ws.freeze_panes = plan['freeze']
    ws.auto_filter.ref = plan['filter']
    ws.sheet_view.showGridLines = False
    return ws


def first_character_use(character, scene_order, state_id=None):
    from export_contract import first_use
    return first_use(character, scene_order, state_id)


def write_asset_sheet(wb, kind, sheet_name, name_col, extra_cols, assets, scenes_data=None):
    from export_contract import build_plan
    if scenes_data is None:
        ids = sorted({r['scene_id'] for c in assets.get('characters', []) for r in c.get('appearances', [])}, key=scene_key)
        scenes_data = {'episodes': [{'episode': 0, 'title': '', 'scenes': [
            {'scene_id': sid, 'characters': [], 'location': '', 'int_ext': '', 'time': ''} for sid in ids]}]}
    plan = build_plan(scenes_data, assets)
    write_plan_sheet(wb, next(s for s in plan['sheets'] if s['name'] == sheet_name))


def write_breakdown(wb, scenes_data, assets, approvals=None):
    from export_contract import build_plan
    write_plan_sheet(wb, build_plan(scenes_data, assets, approvals)['sheets'][-1])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('scenes_file')
    parser.add_argument('assets_file')
    parser.add_argument('output', nargs='?')
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--check', action='store_true')
    modes.add_argument('--sync-character-scenes', action='store_true')
    modes.add_argument('--sync-prop-scenes', action='store_true')
    modes.add_argument('--warning-report', action='store_true')
    modes.add_argument('--export-spec', metavar='展示计划.json', help='验证通过后导出统一展示契约，供其他 Excel 后端消费')
    parser.add_argument('--warning-approvals', metavar='确认文件.json')
    parser.add_argument('--review-file', metavar='review.json', help='默认使用 scenes.json 同目录的 review.json')
    args = parser.parse_args()
    if not (args.output or args.check or args.sync_character_scenes or args.sync_prop_scenes or args.warning_report or args.export_spec):
        parser.error('指定输出.xlsx 或 --check/--sync-character-scenes/--sync-prop-scenes/--warning-report')
    if args.output and (args.check or args.sync_character_scenes or args.sync_prop_scenes or args.warning_report or args.export_spec):
        parser.error('输出文件与校验/同步/报告模式不能同时使用')
    if (args.sync_character_scenes or args.sync_prop_scenes) and args.warning_approvals:
        parser.error('同步模式不使用警告确认；先同步数据，再生成确认报告')
    if args.warning_report and args.warning_approvals:
        parser.error('报告模式不使用警告确认文件；需要应用确认时使用 --check 或导出模式')
    try:
        with open(args.scenes_file, encoding='utf-8') as f:
            scenes_data = json.load(f)
        with open(args.assets_file, encoding='utf-8') as f:
            assets = json.load(f)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        parser.exit(1, f'错误: 无法读取输入 JSON：{error}\n')
    shape_errors = input_errors(scenes_data, assets)
    if shape_errors:
        for error in shape_errors:
            print('错误:', error)
        parser.exit(1)
    protected = {Path(args.scenes_file).resolve(), Path(args.assets_file).resolve(),
                 Path(args.review_file or Path(args.scenes_file).with_name('review.json')).resolve()}
    if args.warning_approvals:
        protected.add(Path(args.warning_approvals).resolve())
    if isinstance(scenes_data.get('source'), dict) and isinstance(scenes_data['source'].get('path'), str):
        protected.add(Path(scenes_data['source']['path']).resolve())
    protected.update(path.resolve() for path in Path(__file__).resolve().parent.parent.rglob('*') if path.is_file())
    if args.output and (Path(args.output).suffix.lower() != '.xlsx' or Path(args.output).resolve() in protected):
        parser.exit(1, '输出须为 .xlsx，不能覆盖剧本、工作数据或 skill 文件\n')
    if args.export_spec and Path(args.export_spec).resolve() in protected:
        parser.exit(1, '展示计划不能覆盖输入、台账或 skill 文件\n')

    if args.sync_character_scenes or args.sync_prop_scenes:
        errors, warnings = (sync_characters(scenes_data, assets) if args.sync_character_scenes
                            else sync_props(scenes_data, assets))
        for error in errors:
            print('错误:', error)
        if errors:
            sys.exit(1)
        with open(args.assets_file, 'w', encoding='utf-8') as f:
            json.dump(assets, f, ensure_ascii=False, indent=2)
        print('已同步人物场次及依据' if args.sync_character_scenes else '已从道具实物指代记录同步状态场次')
        print('请继续执行 --check')
        return

    errors, warnings = validate(scenes_data, assets)
    if args.warning_report:
        report = warning_report(scenes_data, assets, warnings)
        report['errors'] = errors
        print(json.dumps(report, ensure_ascii=False, indent=2))
        parser.exit(1 if errors else 0)
    errors.extend(source_errors(scenes_data))
    try:
        review_path = Path(args.review_file or Path(args.scenes_file).with_name('review.json'))
        review = load_review(review_path)
        from audit_state import team_mode_errors
        errors.extend(team_mode_errors(scenes_data,review,[review_path.parent,Path(args.scenes_file).parent]))
        errors.extend(validate_review(scenes_data, assets, review))
    except ValueError as error:
        errors.append(str(error))
    document = None
    if args.warning_approvals:
        try:
            with open(args.warning_approvals, encoding='utf-8') as f:
                document = json.load(f)
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            parser.exit(1, f'错误: 无法读取警告确认文件：{error}\n')
        if document is None:
            parser.exit(1, '错误: 警告确认文件必须为对象，不能为 null\n')
    remaining, accepted, approval_errors = apply_approvals(scenes_data, assets, warnings, document)
    errors.extend(approval_errors)
    for e in errors:
        print('错误:', e)
    for w in remaining:
        print(f'未确认警告 {warning_id(w)}:', w)
    for item in accepted:
        print('已确认警告:', approval_text(item))
    counts = {label: (len(assets.get(k, [])), sum(len(a.get('states', [])) for a in assets.get(k, [])))
              for k, label, _, _ in KINDS}
    print('统计:', '  '.join(f'{l} {n}个/{m}状态' for l, (n, m) in counts.items()))
    print(f'错误 {len(errors)} 条，未确认警告 {len(remaining)} 条，已确认警告 {len(accepted)} 条')
    if errors or remaining:
        sys.exit(1)
    if args.check:
        return

    from export_contract import build_plan
    try:
        plan = build_plan(scenes_data, assets, accepted)
    except ValueError as error:
        parser.exit(1, f'错误: {error}\n')
    if args.export_spec:
        with open(args.export_spec, 'w', encoding='utf-8') as f:
            json.dump(plan, f, ensure_ascii=False, indent=2)
        print('已生成展示计划:', args.export_spec)
        return

    wb = Workbook()
    wb.remove(wb.active)
    for sheet in plan['sheets']:
        write_plan_sheet(wb, sheet)
    from delivery_guard import save_verified
    if Path(args.output).resolve() in {Path(args.scenes_file).resolve(), Path(args.assets_file).resolve()}:
        parser.exit(1, '输出不能覆盖输入文件\n')
    try:
        save_verified(wb, scenes_data, assets, args.output, accepted)
    except (OSError, ValueError) as error:
        parser.exit(1, f'错误: {error}\n')
    print('已生成并自动验收工作簿:', args.output)
    print('正式交付仍须 workflow.py finalize 完成原文快照、语义/视觉复核和文件哈希验收')


if __name__ == '__main__':
    main()
