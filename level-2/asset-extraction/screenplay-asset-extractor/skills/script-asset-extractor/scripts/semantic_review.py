"""DOCX 资产提取的逐场判读凭据；校验完成情况，不代替语义判断。

这里不提供自动生成“已审阅”记录的命令。哈希只绑定输入快照，
行级结论、类别取舍和排除依据必须来自对当前剧本的实际阅读。
"""
import hashlib
import json


CATEGORIES = ('characters', 'scenes', 'props')
SCHEMA = 'asset_semantic_review_v1'


def canonical_sha256(value):
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True,
                         separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(payload).hexdigest()


def asset_snapshot(assets):
    """仅绑定三类业务数据，避免把审核对象自身加入哈希形成循环。"""
    return {kind: assets.get(kind, []) for kind in CATEGORIES}


def scene_asset_ids(assets, scene_id):
    result = {}
    for kind in CATEGORIES:
        ids = set()
        for asset in assets.get(kind, []):
            groups = [*asset.get('states', []), *asset.get('subscenes', [])]
            if any(scene_id in group.get('scenes', []) for group in groups):
                ids.add(asset['id'])
        result[kind] = ids
    return result


def _nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def _id_set(value, label, errors):
    if not isinstance(value, list) or any(not _nonempty(item) for item in value):
        errors.append(f'{label} asset_ids 必须为非空字符串数组，可用空数组表示无此类资产')
        return set()
    if len(value) != len(set(value)):
        errors.append(f'{label} asset_ids 重复')
    return set(value)


def validate_semantic_review(data, assets):
    """在基础容器类型已通过检查后，返回阻止正式导出的审核错误。"""
    errors = []
    review = assets.get('semantic_review')
    if not isinstance(review, dict) or review.get('schema_version') != SCHEMA:
        return ['缺少有效 semantic_review 逐场语义审核；基础数据不能直接作为正式资产表导出，见 references/semantic_review.md']
    if review.get('source_sha256') != canonical_sha256(data):
        errors.append('semantic_review 来源快照已变化或未绑定，须回查当前 scenes.json 后重新审核')
    if review.get('assets_sha256') != canonical_sha256(asset_snapshot(assets)):
        errors.append('semantic_review 资产快照已变化或未绑定，须复核当前资产及状态后重新审核')
    scenes = {scene['scene_id']: scene for ep in data['episodes'] for scene in ep['scenes']}
    if not scenes:
        errors.append('来源没有有效场次，不能核定为已完成资产提取')
    records = review.get('scenes')
    if not isinstance(records, list):
        return errors + ['semantic_review.scenes 必须为逐场审核数组，不能用完成标记代替']
    seen = set()
    for record in records:
        if not isinstance(record, dict):
            errors.append('semantic_review.scenes 存在非对象记录')
            continue
        sid = record.get('scene_id')
        if not isinstance(sid, str) or sid not in scenes:
            errors.append(f'semantic_review 引用了不存在的场次：{sid}')
            continue
        if sid in seen:
            errors.append(f'semantic_review 场次审核重复：{sid}')
        seen.add(sid)
        scene = scenes[sid]
        expected = scene_asset_ids(assets, sid)
        allowed = set().union(*expected.values())
        categories = record.get('categories')
        if not isinstance(categories, dict) or set(categories) != set(CATEGORIES):
            errors.append(f'{sid} categories 须分别审核 characters、scenes、props，空类别也须说明')
        else:
            for kind in CATEGORIES:
                category = categories[kind]
                label = f'{sid}/{kind}'
                if not isinstance(category, dict):
                    errors.append(f'{label} 缺少类别审核对象')
                    continue
                actual = _id_set(category.get('asset_ids'), label, errors)
                if actual != expected[kind]:
                    errors.append(f'{label} 审核资产与本场实际状态/子场景不一致；应为 {sorted(expected[kind])}')
                if not _nonempty(category.get('conclusion')):
                    errors.append(f'{label} 缺少具体类别结论；零道具也须有本场判读理由')
        line_reviews = record.get('lines')
        if not isinstance(line_reviews, list):
            errors.append(f'{sid} 缺少逐行 lines 审核，不能只填场级结论')
            line_reviews = []
        lines_seen, reviewed_ids = set(), {}
        for item in line_reviews:
            if not isinstance(item, dict):
                errors.append(f'{sid} lines 存在非对象记录')
                continue
            line = item.get('line')
            if not isinstance(line, int) or isinstance(line, bool) or not 1 <= line <= len(scene['lines']):
                errors.append(f'{sid} 审核行号无效：{line}')
                continue
            label = f'{sid}:L{line}'
            if line in lines_seen:
                errors.append(f'{label} 审核重复')
            lines_seen.add(line)
            if item.get('quote') != scene['lines'][line - 1]['text']:
                errors.append(f'{label} 审核引文须完整对应当前原文行')
            if not _nonempty(item.get('conclusion')):
                errors.append(f'{label} 缺少具体语义判读结论')
            ids = _id_set(item.get('asset_ids'), label, errors)
            if not ids <= allowed:
                errors.append(f'{label} 引用了本场未分配状态/子场景的资产：{sorted(ids - allowed)}')
            reviewed_ids[line] = ids
        missing = set(range(1, len(scene['lines']) + 1)) - lines_seen
        if missing:
            errors.append(f'{sid} 未完成逐行语义审核：{sorted(missing)}')
        # 道具须落到原文使用行及已确认实物记录；场级列表不能替代逐行阅读。
        for prop in assets['props']:
            if prop['id'] not in expected['props']:
                continue
            visible = [mention for mention in prop.get('mentions', [])
                       if mention.get('visibility') == 'visible'
                       and mention.get('source', {}).get('scene_id') == sid]
            for mention in visible:
                line = mention['source']['line']
                if prop['id'] not in reviewed_ids.get(line, set()):
                    errors.append(f'{sid}:L{line} 道具 {prop["id"]} 已有出镜记录但未关联逐行审核')
        exclusions = record.get('exclusions')
        if not isinstance(exclusions, list):
            errors.append(f'{sid} exclusions 必须为数组；无排除项时填写 []')
            continue
        for item in exclusions:
            if not isinstance(item, dict) or item.get('category') not in CATEGORIES or not _nonempty(item.get('reason')):
                errors.append(f'{sid} 排除项须说明有效 category 与具体 reason')
                continue
            refs = item.get('evidence')
            if not isinstance(refs, list) or not refs:
                errors.append(f'{sid} 排除项缺少原文 evidence，不能用未写持有人/无变化等泛化理由排除')
                continue
            for ref in refs:
                if not isinstance(ref, dict):
                    errors.append(f'{sid} 排除项 evidence 必须为对象')
                    continue
                line = ref.get('line')
                if (ref.get('scene_id') != sid or not isinstance(line, int) or isinstance(line, bool)
                        or not 1 <= line <= len(scene['lines']) or not _nonempty(ref.get('quote'))
                        or ref['quote'] not in scene['lines'][line - 1]['text']):
                    errors.append(f'{sid} 排除项证据与当前原文不符')
    if seen != set(scenes):
        errors.append(f'semantic_review 场次覆盖不完整，尚缺：{sorted(set(scenes) - seen)}')
    return errors
