"""独立扫描外观候选行；关键词仅用于要求复核，不自动推断出镜或状态。"""
import hashlib
import re


VISUAL_CUES = re.compile(
    r'换上|换回|换成|换装|换了|穿上|脱下|脱掉|褪去|披上|卸下|戴上|摘下|'
    r'身穿|身着|穿着|(?:穿|着)[^。；，,]{0,8}(?:裙|袍|衣|甲|服)|'
    r'染血|沾血|血污|血迹|鲜血[^。；，,]{0,6}(?:浸透|浸染)|浑身是血|'
    r'包扎|纱布|伤疤|伤口|烧伤|受伤|淤青|泥污|污渍|破损|湿透|'
    r'化为|化作|变成|变回|恢复(?:人形|原形|原貌)|显露|显现|狐耳|兽耳|龙角|'
    r'童年|幼年|少年|老年|白发|盘发|束发|散发|妆容|卸妆|\d+岁'
)


def change_candidates(data, character):
    names = [character['name']] + character.get('aliases', [])
    for ep in data['episodes']:
        for scene in ep['scenes']:
            listed = bool(set(names) & set(scene.get('characters', [])))
            for line_no, line in enumerate(scene.get('lines', []), 1):
                text = line.get('text', '')
                if line.get('type') != 'action' or not (listed or any(name in text for name in names)):
                    continue
                digest = hashlib.sha256(text.encode('utf-8')).hexdigest()[:12]
                for match in VISUAL_CUES.finditer(text):
                    yield {
                        'candidate_id': f'{scene["scene_id"]}:L{line_no}:V{match.start()}-{match.end()}:{digest}',
                        'source': {'scene_id': scene['scene_id'], 'line': line_no, 'quote': text},
                        'cue': match.group(), 'start_offset': match.start(), 'end_offset': match.end(),
                    }


def covers(candidate, record, scenes):
    source = candidate['source']
    if record.get('scene_id') != source['scene_id']:
        return False
    line = source['line']
    if not record.get('start_line', -1) <= line <= record.get('end_line', -1):
        return False
    low = record.get('start_offset', 0) if line == record['start_line'] else 0
    high = (record.get('end_offset', len(scenes[source['scene_id']]['lines'][line - 1]['text']))
            if line == record['end_line'] else len(source['quote']))
    return low <= candidate['start_offset'] and candidate['end_offset'] <= high


def validate_reviews(data, character, scenes):
    errors = []
    candidates = {item['candidate_id']: item for item in change_candidates(data, character)}
    reviews = character.get('change_reviews', [])
    records = {rec['id']: rec for rec in character.get('appearances', [])}
    seen = set()
    label = f'[人物] {character.get("id")} {character.get("name")}'
    for review in reviews:
        cid = review['candidate_id']
        if cid in seen:
            errors.append(f'{label} 变化候选重复复核: {cid}')
        seen.add(cid)
        candidate = candidates.get(cid)
        if candidate is None:
            errors.append(f'{label} 变化候选不存在或原文已修改: {cid}')
            continue
        if review['source'] != candidate['source']:
            errors.append(f'{label} 变化复核原文与候选不一致: {cid}')
        if not review['reason'].strip():
            errors.append(f'{label} 变化复核缺少判读原因: {cid}')
        decision = review['decision']
        if decision not in ('recorded', 'component', 'not_visible', 'other_character', 'nonvisual', 'uncertain'):
            errors.append(f'{label} 变化复核 decision 无效: {cid}')
        linked = [records.get(rid) for rid in review['appearance_ids']]
        if any(rec is None for rec in linked):
            errors.append(f'{label} 变化复核引用不存在的出场记录: {cid}')
        linked = [rec for rec in linked if rec is not None]
        if decision in ('recorded', 'component', 'uncertain'):
            if not linked or not all(covers(candidate, rec, scenes) for rec in linked):
                errors.append(f'{label} 变化候选未关联覆盖该位置的出场阶段: {cid}')
            if decision == 'recorded' and not any(
                    rec.get('basis') == 'explicit' and any(
                        ref.get('scene_id') == candidate['source']['scene_id']
                        and ref.get('line') == candidate['source']['line']
                        and candidate['cue'] in ref.get('quote', '')
                        for ref in rec.get('evidence_refs', [])) for rec in linked):
                errors.append(f'{label} 已记录变化缺少该阶段的明确外观依据: {cid}')
            if decision == 'uncertain' and not any(rec.get('note', '').strip() for rec in linked):
                errors.append(f'{label} 不确定变化须写入关联出场记录 note: {cid}')
        elif review['appearance_ids']:
            errors.append(f'{label} 排除候选不应关联出场阶段: {cid}')
    for cid, candidate in candidates.items():
        if cid not in seen:
            errors.append(f'{label} 未复核外观变化候选: {cid}「{candidate["cue"]}」；请回查原文并填写 change_reviews')
    return errors
