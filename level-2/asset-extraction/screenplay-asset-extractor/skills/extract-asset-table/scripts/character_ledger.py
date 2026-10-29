"""人物逐场记录校验和派生场次。只验证可计算约束，不替代原文语义复核。"""
from collections import defaultdict
from asset_validation import input_errors
from character_changes import validate_reviews


def scene_index(data):
    return {s['scene_id']: s for e in data['episodes'] for s in e['scenes']}


def check_refs(refs, scenes, label, errors, required=True):
    if not isinstance(refs, list) or (required and not refs):
        errors.append(f'{label} 缺少结构化原文依据')
        return False
    valid = True
    for ref in refs:
        if not isinstance(ref, dict):
            errors.append(f'{label} 原文依据必须为对象')
            valid = False
            continue
        sid, line, quote = ref.get('scene_id'), ref.get('line'), ref.get('quote')
        scene = scenes.get(sid)
        if (scene is None or type(line) is not int or line < 1
                or line > len(scene.get('lines', [])) or not isinstance(quote, str)
                or not quote.strip()):
            errors.append(f'{label} 原文定位无效: {sid}:L{line}')
            valid = False
        elif quote not in scene['lines'][line - 1].get('text', ''):
            errors.append(f'{label} 引文不在指定原文中: {sid}:L{line}「{quote}」')
            valid = False
    return valid


def derive_scenes(character, scenes):
    """按剧本顺序去重；不修改 appearances，不自行判断状态归属。"""
    assignments = defaultdict(set)
    for appearance in character.get('appearances', []):
        assignments[appearance['state_id']].add(appearance['scene_id'])
    return {state['id']: [sid for sid in scenes if sid in assignments[state['id']]]
            for state in character.get('states', [])}


def evidence_text(refs):
    return '\n'.join(f'{r["scene_id"]}:L{r["line"]}：{r["quote"]}' for r in refs)


def validate_characters(data, assets, check_derived=True):
    shape_errors = input_errors(data, assets)
    if shape_errors:
        return shape_errors, []
    errors, warnings = [], []
    scenes = scene_index(data)
    original_ids = [s['scene_id'] for e in data['episodes'] for s in e['scenes']]
    if len(original_ids) != len(scenes):
        errors.append('剧本场次号重复，无法建立唯一原文定位')
    order = {sid: i for i, sid in enumerate(scenes)}
    names = {}
    for char in assets.get('characters', []):
        for name in [char.get('name')] + char.get('aliases', []):
            if name in names and names[name] != char.get('id'):
                errors.append(f'人物名称/别名冲突: {name}')
            names[name] = char.get('id')

    for char in assets.get('characters', []):
        label = f'[人物] {char.get("id")} {char.get("name")}'
        states = {}
        for state in char.get('states', []):
            state_id = state.get('id')
            if not state_id or state_id in states:
                errors.append(f'{label} 状态ID为空或重复: {state_id}')
            states[state_id] = state
            if len(state.get('scenes', [])) != len(set(state.get('scenes', []))):
                errors.append(f'{label}-{state_id} 出现场次重复')

        records = char.get('appearances')
        if not isinstance(records, list) or not records:
            errors.append(f'{label} 缺少 appearances 逐场记录；旧版数据须回查原文迁移')
            continue
        for state_id, state in states.items():
            visual = state.get('visual')
            fields = {'age', 'costume', 'form', 'hair_makeup', 'injury', 'stains'}
            if (not isinstance(visual, dict) or not fields <= visual.keys()
                    or any(not isinstance(visual[k], str) or not visual[k].strip()
                           for k in fields if isinstance(visual, dict) and k in visual)):
                errors.append(f'{label}-{state_id} 缺少六类 visual 外观记录（未知写未说明）')
            check_refs(state.get('evidence_refs'), scenes, f'{label}-{state_id}', errors,
                       required=state.get('basis') != 'unspecified')
            if state.get('basis') not in ('explicit', 'unspecified'):
                errors.append(f'{label}-{state_id} 状态 basis 必须为 explicit/unspecified')
            if state.get('basis') == 'unspecified' and isinstance(visual, dict):
                if any(v != '未说明' for v in visual.values()):
                    errors.append(f'{label}-{state_id} 未说明状态不能填入推测外观')

        by_id, previous, intervals = {}, {}, defaultdict(list)
        used = set()
        last_position = None
        for rec in records:
            if not isinstance(rec, dict):
                errors.append(f'{label} appearance 必须为对象')
                continue
            rid, sid, stid = rec.get('id'), rec.get('scene_id'), rec.get('state_id')
            rlabel = f'{label}/{rid}'
            if not rid or rid in by_id:
                errors.append(f'{rlabel} 出场记录ID为空或重复')
            scene = scenes.get(sid)
            if scene is None or stid not in states:
                errors.append(f'{rlabel} 场次或状态不存在: {sid}/{stid}')
                continue
            used.add(stid)
            start, end = rec.get('start_line'), rec.get('end_line')
            nlines = len(scene.get('lines', []))
            if (type(start) is not int or type(end) is not int
                    or not (1 <= start <= end <= nlines if nlines else start == end == 0)):
                errors.append(f'{rlabel} 段落区间无效: {sid}:L{start}-L{end}')
                continue
            start_offset = rec.get('start_offset', 0)
            end_offset = rec.get('end_offset', len(scene['lines'][end - 1].get('text', '')) if nlines else 0)
            start_length = len(scene['lines'][start - 1].get('text', '')) if nlines else 0
            end_length = len(scene['lines'][end - 1].get('text', '')) if nlines else 0
            if (type(start_offset) is not int or type(end_offset) is not int
                    or not 0 <= start_offset <= start_length or not 0 <= end_offset <= end_length
                    or (nlines and (start, start_offset) >= (end, end_offset))):
                errors.append(f'{rlabel} 段落内字符区间无效（结束位置不包含在区间内）')
                continue
            begin, finish = (start, start_offset), (end, end_offset)
            position = (order[sid], start, start_offset)
            if last_position is not None and position < last_position:
                errors.append(f'{rlabel} 未按剧本场次、段落顺序记录')
            last_position = position
            timeline, instance = rec.get('timeline'), rec.get('instance')
            if not isinstance(timeline, str) or not timeline.strip() or not isinstance(instance, str) or not instance.strip():
                errors.append(f'{rlabel} 缺少 timeline/instance')
                continue
            track = (timeline, instance)
            for old_start, old_end in intervals[(sid, track)]:
                if max(begin, old_start) < min(finish, old_end) or (not nlines and begin == old_start):
                    errors.append(f'{rlabel} 同场同时间线同实体的阶段区间重叠')
            intervals[(sid, track)].append((begin, finish))

            presence = rec.get('presence', {})
            kind = presence.get('kind') if isinstance(presence, dict) else None
            if kind == 'header':
                if not any(n in scene.get('characters', []) for n in [char.get('name')] + char.get('aliases', [])):
                    errors.append(f'{rlabel} 声称人物行出场，但人物行无此人')
            elif kind == 'action':
                refs = presence.get('refs')
                if check_refs(refs, scenes, rlabel + ' 出镜证据', errors):
                    for ref in refs:
                        line = ref['line']
                        if (ref['scene_id'] != sid or not start <= line <= end
                                or scenes[sid]['lines'][line - 1].get('type') != 'action'):
                            errors.append(f'{rlabel} 动作出镜证据必须位于本阶段的动作行')
                        else:
                            text = scene['lines'][line - 1].get('text', '')
                            lower = start_offset if line == start else 0
                            upper = end_offset if line == end else len(text)
                            if ref['quote'] not in text[lower:upper]:
                                errors.append(f'{rlabel} 动作出镜证据超出本阶段字符区间')
            else:
                errors.append(f'{rlabel} presence.kind 必须为 header/action；台词提及不证明出镜')

            basis, boundary = rec.get('basis'), rec.get('boundary')
            if boundary not in ('continuous', 'reset'):
                errors.append(f'{rlabel} boundary 必须为 continuous/reset')
            refs = rec.get('evidence_refs')
            check_refs(refs, scenes, rlabel, errors, required=basis == 'explicit')
            if isinstance(refs, list):
                for ref in refs:
                    if isinstance(ref, dict) and (ref.get('scene_id') != sid
                            or type(ref.get('line')) is not int
                            or not start <= ref['line'] <= end):
                        errors.append(f'{rlabel} 外观依据必须位于本场本阶段')
                    elif isinstance(ref, dict) and isinstance(ref.get('quote'), str) and ref['quote'] and type(ref.get('line')) is int:
                        source_text = scene['lines'][ref['line'] - 1].get('text', '')
                        lower = start_offset if ref['line'] == start else 0
                        upper = end_offset if ref['line'] == end else len(source_text)
                        if ref['quote'] not in source_text[lower:upper]:
                            errors.append(f'{rlabel} 引文超出本阶段字符区间')
            if (basis == 'explicit' and states[stid].get('basis') == 'unspecified'):
                errors.append(f'{rlabel} 明示外观记录不能分配未说明状态')
            prior = previous.get(track)
            if basis == 'inherited':
                if not isinstance(rec.get('continuity'), str) or not rec['continuity'].strip():
                    errors.append(f'{rlabel} 缺少故事连续性判读说明 continuity')
                source = by_id.get(rec.get('from'))
                if (source is None or source is not prior or boundary != 'continuous'
                        or source.get('state_id') != stid):
                    errors.append(f'{rlabel} 继承必须指向同时间线同实体最近记录且状态相同，不得跨 reset')
                elif source.get('basis') == 'unspecified':
                    errors.append(f'{rlabel} 不能从未说明记录继承已确认状态')
            elif basis == 'unspecified':
                if states[stid].get('basis') != 'unspecified':
                    errors.append(f'{rlabel} 未说明记录不能强行分配已知造型')
            elif basis != 'explicit':
                errors.append(f'{rlabel} basis 必须为 explicit/inherited/unspecified')
            if basis != 'inherited' and rec.get('from'):
                errors.append(f'{rlabel} 非继承记录不能设置 from')
            if prior is None and boundary != 'reset':
                errors.append(f'{rlabel} 时间线/实体首条记录必须 reset')
            if prior and prior['scene_id'] == sid and prior['state_id'] != stid and basis != 'explicit':
                if basis != 'unspecified' or boundary != 'reset':
                    errors.append(f'{rlabel} 同场状态变化必须有本阶段明确依据')
            by_id[rid] = rec
            previous[track] = rec

        for stid in states:
            if stid not in used:
                errors.append(f'{label}-{stid} 状态无任何出场记录')
            for ref in states[stid].get('evidence_refs', []) or []:
                if not isinstance(ref, dict):
                    continue
                if not any(r.get('state_id') == stid and r.get('basis') == 'explicit'
                           and ref in (r.get('evidence_refs') or [])
                           for r in records if isinstance(r, dict)):
                    errors.append(f'{label}-{stid} 状态依据未关联到该状态的明确出场记录')
        if check_derived and not errors:
            derived = derive_scenes(char, scenes)
            for stid, state in states.items():
                if state.get('scenes') != derived[stid]:
                    errors.append(f'{label}-{stid} scenes 与逐场记录不一致，应为 {derived[stid]}；校对记录后用 --sync-character-scenes')
                if state.get('evidence') != evidence_text(state.get('evidence_refs', [])):
                    errors.append(f'{label}-{stid} evidence 与结构化依据不一致；用 --sync-character-scenes')

        if not errors:
            errors.extend(validate_reviews(data, char, scenes))

    return errors, warnings


def sync_characters(data, assets):
    errors, warnings = validate_characters(data, assets, check_derived=False)
    if errors:
        return errors, warnings
    scenes = scene_index(data)
    for char in assets.get('characters', []):
        derived = derive_scenes(char, scenes)
        for state in char['states']:
            state['scenes'] = derived[state['id']]
            state['evidence'] = evidence_text(state['evidence_refs'])
    return errors, warnings


def character_breakdown(character, sid):
    states = {s['id']: s for s in character.get('states', [])}
    records = [r for r in character.get('appearances', []) if r['scene_id'] == sid]
    basis_names = {'explicit': '原文明示', 'inherited': '连续沿用', 'unspecified': '未说明'}
    return '\n'.join(
        f'{character["name"]}·{states[r["state_id"]]["name"]}'
        f' [{r["timeline"]}/{r["instance"]}；{segment_position(r)}；{basis_names[r["basis"]]}]'
        + (f'；备注：{r["note"]}' if r.get('note') else '')
        for r in records)


def state_notes(character, state):
    notes = [value for value in [character.get('note', ''), state.get('note', '')] if value]
    notes.extend(f'{rec["scene_id"]} {segment_position(rec)} '
                 f'{rec["timeline"]}/{rec["instance"]}：{rec["note"]}'
                 for rec in character.get('appearances', [])
                 if rec['state_id'] == state['id'] and rec.get('note'))
    return '\n'.join(notes)


def segment_position(record):
    text = f'L{record["start_line"]}-{record["end_line"]}'
    if 'start_offset' in record or 'end_offset' in record:
        text += f'（字符{record.get("start_offset", 0)}:{record.get("end_offset", "末尾")}）'
    return text
