"""执行台账的覆盖与证据检查；结构通过不代表自然语言判断正确。"""
import hashlib
import json
import re
from pathlib import Path
from source_candidates import candidates
from candidate_links import validate_action_refs

VERSION = '0.3.2'
SCHEMA = 'asset_execution_review_v1'
KINDS = ('characters', 'scenes', 'props')
PLACEHOLDER = re.compile(r'^(?:已完成|完成|已检查|已审核|已审阅|已读|全部已读|已核对|无|暂无|无问题|通过|ok|done|待填写|待补充|未说明)[。.!！\s]*$', re.I)


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':')).encode('utf-8')).hexdigest()


def file_digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def asset_digest(assets):
    return digest({kind: assets.get(kind, []) for kind in KINDS})


def concrete(text):
    return isinstance(text, str) and bool(text.strip()) and not PLACEHOLDER.fullmatch(text.strip())


def scene_assets(assets, sid):
    result = {}
    for kind in KINDS:
        result[kind] = {asset['id'] for asset in assets.get(kind, [])
                        if any(sid in group.get('scenes', [])
                               for group in [*asset.get('states', []), *asset.get('subscenes', [])])}
    return result


def skeleton(data):
    """只创建空白待办，不生成通过、排除或已读结论。"""
    return {'schema_version': SCHEMA, 'source_sha256': '', 'assets_sha256': '',
            'parse_reviews': [{'paragraph': item['paragraph'], 'quote': item['text'], 'conclusion': ''}
                              for item in data.get('parse_report', {}).get('unrecognized', [])],
            'scenes': [{'scene_id': scene['scene_id'],
                        'lines': [{'line': i, 'quote': row['text'], 'asset_ids': [], 'conclusion': ''}
                                  for i, row in enumerate(scene['lines'], 1)],
                        'categories': {kind: {'asset_ids': [], 'conclusion': ''} for kind in KINDS}}
                       for ep in data['episodes'] for scene in ep['scenes']],
            'candidate_reviews': [{**candidate, 'decision': '', 'asset_ids': [],
                                   'evidence_refs': [], 'reason': ''} for candidate in candidates(data)],
            'character_reviews': [], 'delivery_review': {}}


def load_review(path):
    try:
        value = json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError) as error:
        raise ValueError(f'无法读取执行台账 {path}：{error}') from error
    if not isinstance(value, dict):
        raise ValueError('review.json 顶层必须为对象')
    return value


def validate_review(data, assets, review, bound=True):
    from asset_validation import input_errors
    shape_errors = input_errors(data, assets)
    if shape_errors:
        return shape_errors
    errors = []
    if not isinstance(review, dict) or review.get('schema_version') != SCHEMA:
        return ['缺少有效执行台账 review.json；先逐场判读，不能直接交付资产表']
    if bound:
        if review.get('source_sha256') != digest(data):
            errors.append('原文快照变化或未绑定；重新定位并复核后执行 workflow.py bind')
        if review.get('assets_sha256') != asset_digest(assets):
            errors.append('资产快照变化或未绑定；复核受影响判读后执行 workflow.py bind')
    unknown = {row['paragraph']: row['text'] for row in data.get('parse_report', {}).get('unrecognized', [])}
    parse_seen = set()
    parse_reviews = review.get('parse_reviews', [])
    if not isinstance(parse_reviews, list):
        errors.append('parse_reviews 必须为未识别段落复核数组')
        parse_reviews = []
    for item in parse_reviews:
        number = item.get('paragraph') if isinstance(item, dict) else None
        if type(number) is not int or number not in unknown or number in parse_seen:
            errors.append('未识别段落复核引用无效或重复')
            continue
        parse_seen.add(number)
        if item.get('quote') != unknown[number] or not concrete(item.get('conclusion')):
            errors.append(f'段落 {number} 未识别内容须回查完整原文并写具体判读')
    if parse_seen != set(unknown):
        errors.append(f'漏审未识别段落：{sorted(set(unknown) - parse_seen)}')
    scenes = {s['scene_id']: s for ep in data['episodes'] for s in ep['scenes']}
    if not scenes:
        errors.append('没有有效场次，不能完成审核')
    seen, line_assets = set(), {}

    def id_set(value, label):
        if not isinstance(value, list) or any(not isinstance(v, str) or not v.strip() for v in value):
            errors.append(f'{label} asset_ids 须为字符串数组')
            return set()
        if len(value) != len(set(value)):
            errors.append(f'{label} asset_ids 重复')
        return set(value)

    records = review.get('scenes', [])
    if not isinstance(records, list):
        return errors + ['scenes 审核须为逐场数组']
    for record in records:
        if not isinstance(record, dict) or not isinstance(record.get('scene_id'), str) or record['scene_id'] not in scenes:
            errors.append('审核存在无效场次')
            continue
        sid = record['scene_id']
        if sid in seen:
            errors.append(f'{sid} 场次审核重复')
        seen.add(sid)
        expected = scene_assets(assets, sid)
        allowed = set().union(*expected.values())
        categories = record.get('categories')
        if not isinstance(categories, dict) or set(categories) != set(KINDS):
            errors.append(f'{sid} 必须分别审核人物、场景、道具三类')
        else:
            for kind in KINDS:
                item = categories[kind]
                if not isinstance(item, dict):
                    errors.append(f'{sid}/{kind} 类别审核必须为对象')
                    continue
                if id_set(item.get('asset_ids'), f'{sid}/{kind}') != expected[kind]:
                    errors.append(f'{sid}/{kind} 审核与本场资产不一致')
                if not concrete(item.get('conclusion')):
                    errors.append(f'{sid}/{kind} 缺少具体结论；空类别也不能填已完成')
        rows = record.get('lines', [])
        if not isinstance(rows, list):
            errors.append(f'{sid} 逐行审核必须为数组')
            rows = []
        covered = set()
        for item in rows:
            if not isinstance(item, dict):
                errors.append(f'{sid} 逐行审核存在非对象')
                continue
            number = item.get('line')
            if type(number) is not int or not 1 <= number <= len(scenes[sid]['lines']):
                errors.append(f'{sid} 审核行号无效')
                continue
            if number in covered:
                errors.append(f'{sid}:L{number} 重复审核')
            covered.add(number)
            if item.get('quote') != scenes[sid]['lines'][number - 1]['text']:
                errors.append(f'{sid}:L{number} 审核引文须等于完整原文行')
            if not concrete(item.get('conclusion')):
                errors.append(f'{sid}:L{number} 缺少具体判读，不能填已完成')
            ids = id_set(item.get('asset_ids'), f'{sid}:L{number}')
            if not ids <= allowed:
                errors.append(f'{sid}:L{number} 引用不在本场的资产')
            line_assets[sid, number] = ids
        missing = set(range(1, len(scenes[sid]['lines']) + 1)) - covered
        if missing:
            errors.append(f'{sid} 漏审原文行：{sorted(missing)}')
    if seen != set(scenes):
        errors.append(f'漏审场次：{sorted(set(scenes) - seen)}')

    for prop in assets['props']:
        for mention in prop.get('mentions', []):
            ref = mention['source']
            if mention.get('visibility') == 'visible' and prop['id'] not in line_assets.get((ref['scene_id'], ref['line']), set()):
                errors.append(f'{ref["scene_id"]}:L{ref["line"]} 已出镜道具 {prop["id"]} 未关联该行审核')

    # 独立来源候选不因资产被删除而消失。
    expected_candidates = {c['candidate_id']: c for c in candidates(data)}
    seen_candidates = set()
    reviews = review.get('candidate_reviews', [])
    if not isinstance(reviews, list):
        errors.append('candidate_reviews 必须为数组')
        reviews = []
    for item in reviews:
        cid = item.get('candidate_id') if isinstance(item, dict) else None
        if not isinstance(cid, str) or cid not in expected_candidates:
            errors.append('候选审核引用不存在或已变化的原文候选')
            continue
        if cid in seen_candidates:
            errors.append(f'{cid} 候选重复审核')
        seen_candidates.add(cid)
        candidate = expected_candidates[cid]
        if any(item.get(key) != candidate[key] for key in ('source', 'kind', 'start_offset', 'end_offset', 'cue')):
            errors.append(f'{cid} 候选定位或引文与原文不一致')
        source = candidate['source']
        sid, number = source['scene_id'], source['line']
        ids = id_set(item.get('asset_ids'), cid)
        if not concrete(item.get('reason')):
            errors.append(f'{cid} 缺少具体候选判读原因')
        refs = item.get('evidence_refs')
        valid_evidence = False
        if isinstance(refs, list):
            for ref in refs:
                if (isinstance(ref, dict) and ref.get('scene_id') == sid and ref.get('line') == number
                        and isinstance(ref.get('quote'), str) and ref['quote']
                        and ref['quote'] in source['quote'] and candidate['cue'] in ref['quote']):
                    valid_evidence = True
                else:
                    errors.append(f'{cid} 候选证据须覆盖本行线索')
        if not valid_evidence:
            errors.append(f'{cid} 缺少覆盖线索的原文证据')
        decision = item.get('decision')
        action_ids, action_errors = validate_action_refs(candidate, item, assets, scenes[sid])
        errors.extend(action_errors)
        if decision == 'recorded':
            if not ids or not ids <= line_assets.get((sid, number), set()):
                errors.append(f'{cid} 已收录候选须关联本行实际资产')
            if candidate['kind'].startswith('prop_'):
                matched = False
                for prop in assets['props']:
                    if prop['id'] not in ids:
                        continue
                    for mention in prop.get('mentions', []):
                        ref = mention.get('source', {})
                        low, high = mention.get('start_offset', -1), mention.get('end_offset', -1)
                        if ref.get('scene_id') == sid and ref.get('line') == number and mention.get('visibility') == 'visible':
                            if candidate['kind'] == 'prop_term':
                                matched |= low <= candidate['start_offset'] and high >= candidate['end_offset']
                            else:
                                matched |= candidate['start_offset'] <= low < high <= candidate['end_offset']
                if not matched and not action_ids:
                    errors.append(f'{cid} 缺少覆盖该物件线索的 visible mentions，不能用同场其他道具顶替')
            elif candidate['kind'] in ('visual', 'timeline'):
                matched = any(char['id'] in ids and any(rec['scene_id'] == sid
                              and rec['start_line'] <= number <= rec['end_line']
                              for rec in char.get('appearances', [])) for char in assets['characters'])
                if not matched:
                    errors.append(f'{cid} 外观/时间线候选须关联人物出场阶段')
        elif decision == 'excluded':
            if ids:
                errors.append(f'{cid} 排除项不应引用已收录资产；理由说明归场景/人物或非出镜')
        elif decision == 'uncertain':
            errors.append(f'{cid} 候选仍待确认，不能正式交付')
        else:
            errors.append(f'{cid} decision 必须为 recorded/excluded/uncertain')
    if seen_candidates != set(expected_candidates):
        errors.append(f'漏审原文候选：{sorted(set(expected_candidates) - seen_candidates)}')

    required_chars = {char['id'] for char in assets['characters']
                      if len(char.get('states', [])) > 1 or any(rec.get('boundary') == 'reset'
                      or rec.get('basis') == 'inherited' for rec in char.get('appearances', []))}
    char_reviews = review.get('character_reviews', [])
    char_seen = set()
    if not isinstance(char_reviews, list):
        errors.append('character_reviews 必须为数组')
        char_reviews = []
    for item in char_reviews:
        if (not isinstance(item, dict) or not isinstance(item.get('character_id'), str)
                or item['character_id'] not in required_chars):
            errors.append('人物边界复核引用无效人物')
            continue
        cid = item['character_id']
        if cid in char_seen:
            errors.append(f'{cid} 人物边界复核重复')
        char_seen.add(cid)
        char = next(c for c in assets['characters'] if c['id'] == cid)
        if id_set(item.get('appearance_ids'), cid) != {r['id'] for r in char.get('appearances', [])}:
            errors.append(f'{cid} 人物边界复核未覆盖全部出场阶段')
        if not concrete(item.get('conclusion')):
            errors.append(f'{cid} 缺少状态变化、恢复和继承的复核结论')
    if char_seen != required_chars:
        errors.append(f'人物边界复核未完成：{sorted(required_chars - char_seen)}')
    if bound:
        from audit_state import audit_errors
        errors.extend(audit_errors(data, assets, review))
    return errors


def source_errors(data):
    """正式流程必须能回到原始 DOCX，拒绝手改解析结果规避校验。"""
    from parse_script import parse, quality_errors
    from zipfile import BadZipFile
    from docx.opc.exceptions import PackageNotFoundError
    if not isinstance(data, dict):
        return ['scenes.json 顶层必须为对象']
    source = data.get('source')
    if not isinstance(source, dict) or not isinstance(source.get('path'), str):
        return ['缺少原始 DOCX 快照；旧项目须用 workflow.py prepare 重新解析']
    try:
        path = Path(source['path'])
        if file_digest(path) != source.get('sha256'):
            return ['原始 DOCX 已变化，旧解析及审核失效']
        current = parse(path)
        errors = quality_errors(current)
        if digest(current) != digest(data):
            # 0.3.2 added source.format; accept old 0.3.2 workspaces when
            # that is the only difference, while keeping all screenplay content strict.
            legacy = json.loads(json.dumps(data, ensure_ascii=False))
            legacy_source = legacy.get('source', {})
            current_source = current.get('source', {})
            legacy_source.pop('format', None); current_source.pop('format', None)
            if digest(current) != digest(legacy):
                errors.append('scenes.json 与原始 DOCX 重解析不一致，禁止修改原文结构规避校验')
        return errors
    except (OSError, ValueError, KeyError, BadZipFile, PackageNotFoundError) as error:
        return [f'无法回查原始 DOCX：{error}']
