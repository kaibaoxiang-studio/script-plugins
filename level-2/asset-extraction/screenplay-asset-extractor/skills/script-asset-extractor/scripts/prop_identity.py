"""道具实物身份与局部称呼校验；名称匹配只生成回查线索，不自动合并。"""
import re

from asset_validation import input_errors
from character_ledger import check_refs, scene_index


GENERIC_NAMES = {'刀', '剑', '匕首', '戒指', '尾戒', '卷轴', '信', '药瓶', '玉佩',
                 '短刃', '长剑', '指环', '佩玉', '瓶子', '药剂', '信件', '项链', '盒子',
                 '它', '这个', '那个', '此物', '这把刀', '那把刀', '这把剑', '那把剑', '登记本'}
PROP_TYPES = [ {'刀', '匕首', '短刃'}, {'剑', '长剑'}, {'戒指', '尾戒', '指环'},
               {'卷轴', '契约', '血契'}, {'药瓶', '药剂'}, {'玉佩', '佩玉'} ]


def is_generic_name(name):
    return name in GENERIC_NAMES or bool(re.fullmatch(r'[这那此](?:一)?[把枚个件封只瓶条张块本支颗]?(.+)', name)
                                         and re.sub(r'^[这那此](?:一)?[把枚个件封只瓶条张块本支颗]?', '', name) in GENERIC_NAMES)


def related_props(assets):
    """候选而非合并结论；同类型、包含关系和同异称都需要原文核对。"""
    props = assets.get('props', [])
    for i, left in enumerate(props):
        left_names = {left['name'], *left.get('aliases', [])}
        for right in props[i + 1:]:
            right_names = {right['name'], *right.get('aliases', [])}
            reasons = []
            if left_names & right_names:
                reasons.append('名称/异称重叠')
            elif any(a in b or b in a for a in left_names for b in right_names if a and b):
                reasons.append('名称包含关系')
            elif any(any(term in name for term in group for name in left_names)
                     and any(term in name for term in group for name in right_names) for group in PROP_TYPES):
                reasons.append('物件类型相近')
            if reasons:
                yield {'left_id': left['id'], 'right_id': right['id'],
                       'left_name': left['name'], 'right_name': right['name'],
                       'reasons': reasons, 'decision': '待原文判读'}


def text_matches(text, terms):
    """重叠名称取更长的原文词，不让“匕首”覆盖“屠龙匕首”。"""
    pattern = '|'.join(re.escape(term) for term in sorted(set(terms), key=lambda s: (-len(s), s)) if term)
    if pattern:
        for match in re.finditer(pattern, text):
            yield {'raw_name': match.group(), 'start_offset': match.start(), 'end_offset': match.end()}


def prop_candidates(data, prop, extra_terms=()):
    names = [prop['name'], prop.get('source_name', ''), *prop.get('aliases', []),
             *(mention['raw_name'] for mention in prop.get('mentions', [])), *extra_terms]
    for ep in data['episodes']:
        for scene in ep['scenes']:
            for line_no, line in enumerate(scene['lines'], 1):
                for match in text_matches(line['text'], names):
                    yield {'source': {'scene_id': scene['scene_id'], 'line': line_no, 'quote': line['text']},
                           'line_type': line['type'], **match}


def validate_props(data, assets, check_derived=True):
    shape_errors = input_errors(data, assets)
    if shape_errors:
        return shape_errors, []
    errors, warnings = [], []
    scenes = scene_index(data)
    if len(scenes) != sum(len(ep['scenes']) for ep in data['episodes']):
        errors.append('剧本场次号重复，不能建立道具实物记录')
    scene_order = {sid: i for i, sid in enumerate(scenes)}
    all_ids = {prop['id'] for prop in assets.get('props', [])}
    if len(all_ids) != len(assets.get('props', [])):
        errors.append('道具资产ID重复，须先核对实物身份')
    used_names, occupied, source_terms = {}, {}, set()
    for prop in assets.get('props', []):
        label = f'[道具] {prop["id"]} {prop["name"]}'
        names = [prop['name'], *prop.get('aliases', [])]
        source_name = prop.get('source_name', prop['name'])
        if not source_name.strip():
            errors.append(f'{label} source_name 原文主称呼不能为空')
        source_terms.add(source_name)
        if len(names) != len(set(names)) or any(not name.strip() for name in names):
            errors.append(f'{label} 名称/异称为空或重复')
        for name in names:
            if name in used_names and used_names[name] != prop['id']:
                errors.append(f'{label} 与 {used_names[name]} 共用全局名称「{name}」；同物应合并，不同实物应区分命名')
            used_names[name] = prop['id']
        mentions = prop.get('mentions')
        if not isinstance(mentions, list) or not mentions:
            errors.append(f'{label} 缺少 mentions 实物指代记录，须回查原文迁移')
            continue
        states = {}
        if not prop.get('states'):
            errors.append(f'{label} 缺少非空 states 状态列表；仅提及而从未出镜的物品不作为道具资产交付')
        for state in prop.get('states', []):
            if not state['id'].strip() or state['id'] in states:
                errors.append(f'{label} 状态ID为空或重复: {state["id"]}')
            states[state['id']] = state
        aliases = {}
        for link in prop.get('alias_evidence', []):
            alias = link['alias']
            if alias in aliases or alias not in prop.get('aliases', []):
                errors.append(f'{label} 异称证据重复或不在 aliases 中: {alias}')
            aliases[alias] = link
            if is_generic_name(alias):
                errors.append(f'{label} 泛称「{alias}」不能作全局 aliases；按单次 mentions 的上下文指代记录')
            if link['basis'] not in ('explicit', 'continuity', 'distinctive') or not link['reason'].strip():
                errors.append(f'{label} 异称缺少有效的身份判读依据: {alias}')
            refs = link.get('evidence_refs', [])
            if check_refs(refs, scenes, label + ' 异称 ' + alias, errors):
                if not any(alias in ref['quote'] for ref in refs):
                    errors.append(f'{label} 异称证据未包含原文称呼「{alias}」')
        for alias in prop.get('aliases', []):
            if alias not in aliases:
                errors.append(f'{label} 全局异称「{alias}」缺少 alias_evidence 原文依据')

        by_id, visible, previous_position = {}, {}, None
        for mention in mentions:
            mid, source = mention['id'], mention['source']
            mlabel = f'{label}/{mid}'
            if not mid.strip() or mid in by_id:
                errors.append(f'{mlabel} 指代记录ID为空或重复')
            sid, line = source['scene_id'], source['line']
            if not check_refs([source], scenes, mlabel, errors):
                continue
            text = scenes[sid]['lines'][line - 1]['text']
            low, high = mention['start_offset'], mention['end_offset']
            if not 0 <= low < high <= len(text) or text[low:high] != mention['raw_name']:
                errors.append(f'{mlabel} 原文称呼与字符位置不一致')
                continue
            if mention['raw_name'] not in source['quote']:
                errors.append(f'{mlabel} 出现依据未包含该原文称呼')
            position = (scene_order[sid], line, low)
            if previous_position is not None and position < previous_position:
                errors.append(f'{mlabel} 指代记录未按原文顺序排列')
            previous_position = position
            if not mention['timeline'].strip():
                errors.append(f'{mlabel} 缺少实物连续段 timeline')
            basis = mention['basis']
            if basis == 'named':
                if mention['raw_name'] not in [source_name, *names]:
                    errors.append(f'{mlabel} named 原文称呼不在 source_name/name/aliases 中')
            elif basis == 'introduced':
                if not mention.get('identity_reason', '').strip():
                    errors.append(f'{mlabel} 首次实物引入缺少身份区分说明')
                # 兼容旧版限定展示名：真实首次引入的特指称呼仍需全剧漏提回查。
                source_terms.add(mention['raw_name'])
            elif basis == 'contextual':
                anchor = by_id.get(mention.get('from'))
                if anchor is None or anchor['timeline'] != mention['timeline']:
                    errors.append(f'{mlabel} 局部指代须指向同实物同连续段的先前记录')
                elif anchor['source'] not in mention.get('identity_refs', []):
                    errors.append(f'{mlabel} 指代依据须包含所引用实物的先前原文位置')
                if not mention.get('identity_reason', '').strip():
                    errors.append(f'{mlabel} 上下文指代缺少交接/指代解释')
                check_refs(mention.get('identity_refs', []), scenes, mlabel + ' 指代链', errors)
            else:
                errors.append(f'{mlabel} basis 必须为 named/introduced/contextual')
            if basis != 'contextual' and mention.get('from'):
                errors.append(f'{mlabel} 非局部指代不能设置 from')
            visibility, stid = mention['visibility'], mention.get('state_id')
            if visibility == 'visible':
                if scenes[sid]['lines'][line - 1]['type'] != 'action':
                    errors.append(f'{mlabel} 台词提及不能直接当作道具出镜')
                if stid not in states:
                    errors.append(f'{mlabel} 引用了不存在的状态: {stid}')
                visible.setdefault(stid, set()).add(sid)
                for (old_sid, old_line, old_low, old_high), old_id in occupied.items():
                    if old_sid == sid and old_line == line and max(low, old_low) < min(high, old_high):
                        errors.append(f'{mlabel} 与 {old_id} 重复认领同一原文道具称呼')
                occupied[(sid, line, low, high)] = f'{prop["id"]}/{mid}'
            elif visibility == 'reference':
                if stid is not None:
                    errors.append(f'{mlabel} 非画面提及不能填入状态场次')
                if not mention.get('note', '').strip():
                    errors.append(f'{mlabel} 非画面提及须说明排除理由')
            else:
                errors.append(f'{mlabel} visibility 必须为 visible/reference')
            by_id[mid] = mention

        if 'source_name' in prop and not any(m['raw_name'] == source_name
                                            and m['basis'] in ('named', 'introduced') for m in by_id.values()):
            errors.append(f'{label} source_name 缺少实际原文主称呼记录')
        for alias in aliases:
            if not any(mention['raw_name'] == alias for mention in mentions):
                errors.append(f'{label} 异称「{alias}」未关联任何实际原文指代记录')
            link = aliases[alias]
            refs = link.get('evidence_refs', [])
            roots = [mention for mention in by_id.values() if mention['basis'] == 'introduced'
                     or (mention['basis'] == 'named' and mention['raw_name'] == source_name)]
            other_names = {mention['raw_name'] for mention in roots if mention['raw_name'] != alias}
            if link['basis'] == 'explicit':
                if not any(alias in {hit['raw_name'] for hit in text_matches(ref['quote'], [alias, *other_names])}
                           and any(hit['raw_name'] in other_names for hit in text_matches(ref['quote'], [alias, *other_names]))
                           for ref in refs):
                    errors.append(f'{label} 显式异称说明须同时包含两个称呼: {alias}')
            elif link['basis'] in ('continuity', 'distinctive'):
                sides = []
                for alias_side in (True, False):
                    covered = [mention for mention in (by_id.values() if alias_side else roots)
                               if (mention['raw_name'] == alias) == alias_side
                               and any(mention['source']['scene_id'] == ref['scene_id']
                                       and mention['source']['line'] == ref['line']
                                       and mention['raw_name'] in ref['quote'] for ref in refs)]
                    sides.append(covered)
                    if not covered:
                        errors.append(f'{label} 异称判读须覆盖该称呼及同一资产另一称呼的实际原文: {alias}')
                if all(sides) and not any(
                        left['source']['scene_id'] != right['source']['scene_id']
                        or left['source']['line'] != right['source']['line']
                        or left['end_offset'] <= right['start_offset']
                        or right['end_offset'] <= left['start_offset']
                        for left in sides[0] for right in sides[1]):
                    errors.append(f'{label} {alias} 的身份判读须覆盖两个独立原文字符位置')
        for relation in prop.get('identity_relations', []):
            if relation['other_id'] not in all_ids or relation['other_id'] == prop['id']:
                errors.append(f'{label} 身份关系引用无效道具: {relation["other_id"]}')
            if relation['decision'] not in ('distinct', 'uncertain') or not relation['reason'].strip():
                errors.append(f'{label} 身份关系必须记录 distinct/uncertain 和判读原因')
            check_refs(relation.get('evidence_refs', []), scenes, label + ' 身份关系', errors,
                       required=relation['decision'] == 'distinct')
            if relation['decision'] == 'uncertain' and not prop.get('note', '').strip():
                errors.append(f'{label} 疑似同一道具须同时在 note 中标明待确认问题')
        for state_id, state in states.items():
            if state_id not in visible:
                errors.append(f'{label}-{state_id} 状态没有实际出镜记录')
            expected = [sid for sid in scenes if sid in visible.get(state_id, set())]
            if check_derived and state.get('scenes', []) != expected:
                errors.append(f'{label}-{state_id} scenes 与实物指代记录不一致；核对后用 --sync-prop-scenes')
    # 从原文独立检查确认过的名称；泛称不作全剧自动归属，避免混淆同类物件。
    terms = [name for name in set(used_names) | source_terms if name and not is_generic_name(name)]
    claimed = {(mention['source']['scene_id'], mention['source']['line'],
                mention['start_offset'], mention['end_offset'])
               for prop in assets['props'] for mention in prop.get('mentions', [])}
    for sid, scene in scenes.items():
        for line_no, line in enumerate(scene['lines'], 1):
            for hit in text_matches(line['text'], terms):
                if not any(old_sid == sid and old_line == line_no
                           and low <= hit['start_offset'] < hit['end_offset'] <= high
                           for old_sid, old_line, low, high in claimed):
                    errors.append(f'[道具] 原文名称未核对: {sid}:L{line_no}「{hit["raw_name"]}」；请记录实物身份或非画面提及')
    return errors, warnings


def sync_props(data, assets):
    errors, warnings = validate_props(data, assets, check_derived=False)
    if errors:
        return errors, warnings
    scenes = scene_index(data)
    for prop in assets['props']:
        for state in prop['states']:
            found = {mention['source']['scene_id'] for mention in prop['mentions']
                     if mention['visibility'] == 'visible' and mention['state_id'] == state['id']}
            state['scenes'] = [sid for sid in scenes if sid in found]
    return errors, warnings


def identity_text(prop):
    lines = [f'{item["alias"]}（{item["basis"]}）：{item["reason"]}；'
                     + '；'.join(f'{ref["scene_id"]}:L{ref["line"]}：{ref["quote"]}' for ref in item['evidence_refs'])
                     for item in prop.get('alias_evidence', [])]
    lines.extend(f'{relation["other_id"]}（{relation["decision"]}）：{relation["reason"]}；'
                 + '；'.join(f'{ref["scene_id"]}:L{ref["line"]}：{ref["quote"]}'
                            for ref in relation.get('evidence_refs', []))
                 for relation in prop.get('identity_relations', []))
    return '\n'.join(lines)


def prop_state_notes(prop, state):
    out = [value for value in [prop.get('note', ''), state.get('note', '')] if value]
    out.extend(f'{mention["source"]["scene_id"]}:L{mention["source"]["line"]} '
               f'「{mention["raw_name"]}」：{mention["note"]}' for mention in prop.get('mentions', [])
               if mention.get('note') and (mention.get('state_id') == state['id']
                                          or (mention['visibility'] == 'reference' and state is prop['states'][0])))
    return '\n'.join(out)
