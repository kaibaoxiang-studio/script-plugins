"""Frozen, cumulative worker fragments. Validation never supplies semantic conclusions."""
import copy
import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path

import execution_review as execution
from candidate_links import validate_action_refs
from source_candidates import candidates

KINDS = execution.KINDS
SCHEMA = 'asset_fragment_v1'
TEAM_SCHEMA = 'asset_team_v1'
PREFIXES = {'characters': 'CHR-', 'scenes': 'SCN-', 'props': 'PRP-'}


def _read(path):
    value = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(value, dict):
        raise ValueError(f'{Path(path).name} 顶层必须为对象')
    return value


def _hash(path):
    return execution.file_digest(path) if Path(path).exists() else None


def _issue(code, owner, location, message):
    return dict(code=code, owner=owner, location=location, message=str(message))


def _report(kind=None, scope=(), pending=(), issues=(), **extra):
    return dict(kind=kind, submitted_scope=list(scope), pending_scope=list(pending),
                issues=list(issues), **extra)


def _scene_index(data):
    return {s['scene_id']: s for e in data['episodes'] for s in e['scenes']}


def _scope(value, scenes):
    if (not isinstance(value, list) or not value or any(not isinstance(s, str) for s in value)
            or len(set(value)) != len(value) or not set(value) <= scenes.keys()):
        raise ValueError('scope 必须为非空、无重复的真实场次号数组')
    return [sid for sid in scenes if sid in value]


def _source(work):
    data = _read(work / 'scenes.json')
    errors = execution.source_errors(data)
    if errors:
        raise ValueError('\n'.join(errors))
    scenes = _scene_index(data)
    if not scenes or len(scenes) != sum(len(e['scenes']) for e in data['episodes']):
        raise ValueError('原文场次为空或重复')
    return data, scenes


def _identity(team, data):
    if (team.get('schema_version') != TEAM_SCHEMA or team.get('version') != execution.VERSION
            or team.get('source_sha256') != execution.digest(data)):
        raise ValueError('team 原文或版本已变化，须新工作目录重新建立分工')
    if not isinstance(team.get('owners'), dict) or set(team['owners']) != set(KINDS):
        raise ValueError('team 必须有三类唯一 owner')
    if any(not isinstance(team['owners'][kind], dict)
           or team['owners'][kind].get('owner') != kind for kind in KINDS):
        raise ValueError('team owner 与类别不一致')


@contextmanager
def _lock(work):
    path = work / '.team-write.lock'
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        os.close(descriptor)
        yield
    finally:
        path.unlink(missing_ok=True)


def _snapshot(paths):
    return {Path(path): _hash(path) for path in paths}


def _watch_source(work, paths):
    """Watch the DOCX too, rather than only its parsed JSON, during each mutation."""
    data = _read(work / 'scenes.json')
    source = data.get('source', {})
    if isinstance(source, dict) and isinstance(source.get('path'), str):
        paths.append(Path(source['path']))
    return _snapshot(paths)


def _transaction(updates, expected):
    """Check optimistic hashes, stage every JSON, roll back all replaced files on failure."""
    previous, staged, replaced = {}, {}, []
    try:
        for path, value in updates.items():
            path = Path(path)
            previous[path] = path.read_bytes() if path.exists() else None
            descriptor, temporary = tempfile.mkstemp(prefix='.team-state-', dir=path.parent)
            staged[path] = temporary
            with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
                json.dump(value, stream, ensure_ascii=False, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
        if any(_hash(path) != wanted for path, wanted in expected.items()):
            raise ValueError('并发修改：校验期间工作文件变化，本次未写入')
        for path, temporary in staged.items():
            os.replace(temporary, path)
            replaced.append(path)
    except Exception:
        for path in reversed(replaced):
            payload = previous[path]
            if payload is None:
                path.unlink(missing_ok=True)
            else:
                descriptor, temporary = tempfile.mkstemp(prefix='.team-rollback-', dir=path.parent)
                with os.fdopen(descriptor, 'wb') as stream:
                    stream.write(payload)
                os.replace(temporary, path)
        raise
    finally:
        for temporary in staged.values():
            if os.path.exists(temporary):
                os.unlink(temporary)


def _independent(review):
    value = review.get('independent_review')
    if (isinstance(value, dict) and isinstance(value.get('required'), bool)
            and isinstance(value.get('scenes'), dict) and isinstance(value.get('characters'), dict)
            and isinstance(value.get('issues'), list)):
        value = copy.deepcopy(value)
        value['required'] = True
        return value
    if value is not None:
        raise ValueError('独立审核状态损坏；不能重建空台账清除既有问题')
    return {'required': True, 'scenes': {}, 'characters': {}, 'issues': []}


def init_team(work):
    work = Path(work)
    try:
        with _lock(work):
            paths = [work / name for name in ('scenes.json', 'team.json', 'assets.json', 'review.json')]
            expected = _watch_source(work, paths)
            data, scenes = _source(work)
            if (work / 'team.json').exists():
                team = _read(work / 'team.json')
                _identity(team, data)
                return _report(pending=scenes, status='existing', team=team)
            review = execution.load_review(work / 'review.json')
            review['independent_review'] = _independent(review)
            team = {'schema_version': TEAM_SCHEMA, 'version': execution.VERSION,
                    'source_sha256': execution.digest(data), 'scope': list(scenes),
                    'owners': {kind: {'owner': kind, 'status': 'pending', 'submitted_scope': []}
                               for kind in KINDS}, 'status': 'pending'}
            _transaction({work / 'team.json': team, work / 'review.json': review}, expected)
            return _report(pending=scenes, status='pending', team=team)
    except (OSError, ValueError, KeyError, TypeError) as error:
        return _report(issues=[_issue('team_init', 'coordinator', 'team.json', error)])


def _belongs(candidate, kind):
    return ((kind == 'props' and candidate['kind'].startswith('prop_'))
            or (kind == 'characters' and candidate['kind'] in ('visual', 'timeline')))


def fragment_template(work, kind, scope=None):
    work = Path(work)
    try:
        if kind not in KINDS:
            raise ValueError('kind 须为 characters/scenes/props')
        data, scenes = _source(work)
        team = _read(work / 'team.json'); _identity(team, data)
        scope = _scope(list(scenes) if scope is None else scope, scenes)
        fragment = dict(schema_version=SCHEMA, source_sha256=execution.digest(data),
                        version=execution.VERSION, kind=kind, scope=scope, assets=[],
                        line_reviews=[{'scene_id': sid, 'line': i, 'quote': row['text'],
                                       'asset_ids': [], 'conclusion': ''}
                                      for sid in scope for i, row in enumerate(scenes[sid]['lines'], 1)],
                        category_reviews=[{'scene_id': sid, 'asset_ids': [], 'conclusion': ''} for sid in scope],
                        candidate_reviews=[{**c, 'decision': '', 'asset_ids': [], 'evidence_refs': [], 'reason': ''}
                                           for c in candidates(data) if _belongs(c, kind) and c['source']['scene_id'] in scope],
                        character_reviews=[])
        return _report(kind, scope, [s for s in scenes if s not in scope], fragment=fragment)
    except (OSError, ValueError, KeyError, TypeError) as error:
        return _report(kind, issues=[_issue('fragment_template', kind, 'fragment', error)])


def _business(data, fragment):
    """Validate complete owned identities against the entire source, then derive display data."""
    from asset_validation import input_errors
    from build_xlsx import validate
    from character_ledger import sync_characters
    from prop_identity import sync_props
    assets = {kind: copy.deepcopy(fragment['assets']) if kind == fragment['kind'] else [] for kind in KINDS}
    errors = input_errors(data, assets)
    if errors:
        return assets, errors, []
    kind = fragment['kind']
    if kind in ('characters', 'props'):
        errors, warnings = (sync_characters if kind == 'characters' else sync_props)(data, assets)
        if errors:
            return assets, errors, warnings
    return assets, *validate(data, assets)


def _ids(value, allowed, label, errors):
    if (not isinstance(value, list) or any(not isinstance(v, str) for v in value)
            or len(value) != len(set(value)) or not set(value) <= allowed):
        errors.append((label, 'asset_ids 无效、重复或引用其他类别/不存在资产'))
        return set()
    return set(value)


def _validate_fragment(data, scenes, fragment, previous=None, other_ids=()):
    errors, kind, scope = [], fragment.get('kind'), []
    def fail(code, location, message):
        errors.append(_issue(code, kind, location, message))
    if kind not in KINDS:
        fail('kind', 'kind', '类别不存在'); return fragment, scope, errors, []
    if fragment.get('schema_version') != SCHEMA:
        fail('schema', 'schema_version', '片段 schema 无效')
    if fragment.get('version') != execution.VERSION:
        fail('version', 'version', '片段版本已失效')
    if fragment.get('source_sha256') != execution.digest(data):
        fail('source', 'source_sha256', '片段原文快照已失效')
    try:
        scope = _scope(fragment.get('scope'), scenes)
    except ValueError as error:
        fail('scope', 'scope', error)
    if previous and not set(previous.get('scope', [])) <= set(scope):
        fail('scope_regression', 'scope', '累计快照不能删除此前已提交的场次')
    if not isinstance(fragment.get('assets'), list):
        fail('assets', 'assets', 'assets 须为本类别完整业务数组')
    for key in ('line_reviews', 'category_reviews', 'candidate_reviews', 'character_reviews'):
        if not isinstance(fragment.get(key), list) or any(not isinstance(v, dict) for v in fragment.get(key, [])):
            fail('shape', key, key + ' 须为对象数组')
    if kind != 'characters' and fragment.get('character_reviews'):
        fail('wrong_category', 'character_reviews', '人物边界复核只能由人物 owner 提供')
    if errors:
        return fragment, scope, errors, []
    assets, business, warnings = _business(data, fragment)
    for message in business:
        fail('business', 'assets', message)
    identifiers = [a['id'] for a in assets[kind]]
    if len(identifiers) != len(set(identifiers)) or set(identifiers) & set(other_ids):
        fail('duplicate_id', 'assets', '资产 ID 重复或与其他类别冲突')
    if any(not aid.startswith(PREFIXES[kind]) for aid in identifiers):
        fail('wrong_category', 'assets', '资产 ID 前缀与 owner 类别不一致')
    if errors:
        return fragment, scope, errors, warnings
    fragment = copy.deepcopy(fragment); fragment['assets'] = assets[kind]; fragment['scope'] = scope
    allowed = set(identifiers)
    local_errors = []
    lines, categories = {}, {}
    for item in fragment['line_reviews']:
        sid, number = item.get('scene_id'), item.get('line')
        location = f'{sid}:L{number}'
        if sid not in scope or type(number) is not int or not 1 <= number <= len(scenes[sid]['lines']):
            fail('line_location', location, '逐行复核必须定位本批真实原文行'); continue
        if (sid, number) in lines:
            fail('duplicate_line', location, '逐行复核重复')
        if item.get('quote') != scenes[sid]['lines'][number - 1]['text']:
            fail('quote', location, '引文须等于完整原文行')
        if not execution.concrete(item.get('conclusion')):
            fail('conclusion', location, '缺少具体逐行判读')
        ids = _ids(item.get('asset_ids'), allowed, location, local_errors)
        expected = execution.scene_assets(assets, sid)[kind]
        if not ids <= expected:
            fail('line_reference', location, '行引用不在本场资产集合')
        # Only calculated source locations of already supplied records may be added.
        for asset in assets[kind]:
            if kind == 'props' and any(m.get('visibility') == 'visible' and m['source']['scene_id'] == sid
                    and m['source']['line'] == number for m in asset.get('mentions', [])):
                ids.add(asset['id'])
            if kind == 'characters' and any(rec['scene_id'] == sid
                    and rec['start_line'] <= number <= rec['end_line'] for rec in asset.get('appearances', [])):
                ids.add(asset['id'])
        item['asset_ids'] = sorted(ids)
        lines[sid, number] = ids
    for sid in scope:
        missing = [i for i in range(1, len(scenes[sid]['lines']) + 1) if (sid, i) not in lines]
        if missing:
            fail('missing_line', sid, f'漏审原文行：{missing}')
    for item in fragment['category_reviews']:
        sid = item.get('scene_id')
        if sid not in scope or sid in categories:
            fail('category_location', str(sid), '类别复核场次无效或重复'); continue
        _ids(item.get('asset_ids'), allowed, sid, local_errors)
        if not execution.concrete(item.get('conclusion')):
            fail('conclusion', sid, '缺少具体类别判读')
        item['asset_ids'] = sorted(execution.scene_assets(assets, sid)[kind])
        categories[sid] = item
    for sid in set(scope) - categories.keys():
        fail('missing_category', sid, '缺少本场类别复核')
    expected_candidates = {c['candidate_id']: c for c in candidates(data)
                           if _belongs(c, kind) and c['source']['scene_id'] in scope}
    seen = set()
    for item in fragment['candidate_reviews']:
        cid = item.get('candidate_id'); candidate = expected_candidates.get(cid)
        if candidate is None or cid in seen:
            fail('candidate_location', str(cid), '候选不存在、重复、错类别或超出本批'); continue
        seen.add(cid)
        if any(item.get(key) != candidate[key] for key in ('source', 'kind', 'start_offset', 'end_offset', 'cue')):
            fail('candidate_source', cid, '候选原文定位或引文变化')
        ref = candidate['source']; sid, number = ref['scene_id'], ref['line']
        ids = _ids(item.get('asset_ids'), allowed, cid, local_errors)
        if not execution.concrete(item.get('reason')):
            fail('candidate_reason', cid, '缺少具体候选判读原因')
        refs = item.get('evidence_refs')
        valid_refs = isinstance(refs, list) and bool(refs)
        if valid_refs:
            valid_refs = all(isinstance(r, dict) and r.get('scene_id') == sid and r.get('line') == number
                             and isinstance(r.get('quote'), str) and bool(r['quote'])
                             and r['quote'] in ref['quote'] and candidate['cue'] in r['quote'] for r in refs)
        if not valid_refs:
            fail('candidate_evidence', cid, '证据须为本行覆盖线索的实际原文')
        decision = item.get('decision')
        action_ids, action_errors = validate_action_refs(candidate, item, assets, scenes[sid])
        for message in action_errors:
            fail('action_reference', cid, message)
        if decision == 'recorded':
            if not ids or not ids <= lines.get((sid, number), set()):
                fail('candidate_reference', cid, '已收录候选须关联本行实际资产')
            matched = False
            if kind == 'props':
                for prop in assets[kind]:
                    for mention in prop.get('mentions', []):
                        if prop['id'] not in ids or mention['visibility'] != 'visible' or mention['source']['scene_id'] != sid or mention['source']['line'] != number:
                            continue
                        low, high = mention['start_offset'], mention['end_offset']
                        if candidate['kind'] == 'prop_term':
                            matched |= low <= candidate['start_offset'] and high >= candidate['end_offset']
                        else:
                            matched |= candidate['start_offset'] <= low < high <= candidate['end_offset']
                matched |= bool(action_ids)
            else:
                matched = any(a['id'] in ids and any(r['scene_id'] == sid and r['start_line'] <= number <= r['end_line']
                              for r in a['appearances']) for a in assets[kind])
            if not matched:
                fail('candidate_record', cid, '候选须由同位置 visible mentions 或人物阶段覆盖')
        elif decision == 'excluded':
            if ids:
                fail('candidate_reference', cid, '排除候选不可引用收录资产')
        else:
            fail('candidate_pending', cid, '候选 decision 必须完成 recorded/excluded 判读')
    for cid in expected_candidates.keys() - seen:
        fail('missing_candidate', cid, '漏审原文候选')
    required = {a['id']: a for a in assets['characters'] if len(a.get('states', [])) > 1
                or any(r['boundary'] == 'reset' or r['basis'] == 'inherited' for r in a.get('appearances', []))}
    char_seen = set()
    for item in fragment['character_reviews']:
        cid = item.get('character_id')
        if cid not in required or cid in char_seen:
            fail('character_review', str(cid), '人物边界复核引用无效或重复'); continue
        char_seen.add(cid)
        ids = _ids(item.get('appearance_ids'), {r['id'] for r in required[cid]['appearances']}, cid, local_errors)
        if ids != {r['id'] for r in required[cid]['appearances']} or not execution.concrete(item.get('conclusion')):
            fail('character_review', cid, '人物复核须有具体结论并覆盖全剧所有阶段')
    for cid in required.keys() - char_seen:
        fail('missing_character_review', cid, '缺少全剧人物边界复核')
    for location, message in local_errors:
        fail('reference', location, message)
    return fragment, scope, errors, warnings


def submit_fragment(work, path):
    work, path = Path(work), Path(path)
    kind, scope, pending = None, [], []
    try:
        with _lock(work):
            paths = [work / n for n in ('scenes.json', 'team.json', 'assets.json', 'review.json')]
            paths += [work / 'fragments' / f'{k}.json' for k in KINDS]
            paths.append(path)
            expected = _watch_source(work, paths)
            data, scenes = _source(work)
            team = _read(work / 'team.json'); _identity(team, data)
            fragment = _read(path); kind = fragment.get('kind')
            previous, other_ids = None, []
            if kind in KINDS:
                previous = {'scope': team['owners'][kind].get('submitted_scope', [])}
            for other in KINDS:
                target = work / 'fragments' / f'{other}.json'
                if target.exists():
                    value = _read(target)
                    if other != kind:
                        other_ids.extend(a.get('id') for a in value.get('assets', []) if isinstance(a, dict))
            fragment, scope, issues, warnings = _validate_fragment(data, scenes, fragment, previous, other_ids)
            pending = [sid for sid in scenes if sid not in scope]
            if issues:
                return _report(kind, scope, pending, issues, status='rejected', warnings=warnings)
            directory = work / 'fragments'; directory.mkdir(exist_ok=True)
            team['owners'][kind] = {'owner': kind, 'status': 'validated', 'submitted_scope': scope,
                                     'fragment_sha256': execution.digest(fragment), 'run': {'status': 'completed', 'attempts': 0}}
            team['status'] = 'pending'
            _transaction({directory / f'{kind}.json': fragment, work / 'team.json': team}, expected)
            return _report(kind, scope, pending, status='validated', warnings=warnings,
                           global_complete=False)
    except (OSError, ValueError, KeyError, TypeError) as error:
        return _report(kind, scope, pending, [_issue('submit', kind, str(path), error)], status='rejected')


def _combined_review(data, fragments, old):
    review = execution.skeleton(data)
    for key in ('parse_reviews', 'scope_snapshots', 'delivery_review'):
        if key in old:
            review[key] = copy.deepcopy(old[key])
    review['independent_review'] = _independent(old)
    maps = {kind: ({(r['scene_id'], r['line']): r for r in f['line_reviews']},
                   {r['scene_id']: r for r in f['category_reviews']}) for kind, f in fragments.items()}
    for record in review['scenes']:
        sid = record['scene_id']
        for kind in KINDS:
            row = maps[kind][1][sid]
            record['categories'][kind] = {key: copy.deepcopy(row[key]) for key in ('asset_ids', 'conclusion')}
        for row in record['lines']:
            supplied = [maps[kind][0][sid, row['line']] for kind in KINDS]
            row['asset_ids'] = sorted({aid for r in supplied for aid in r['asset_ids']})
            row['conclusion'] = '\n'.join(f'{kind}：{r["conclusion"]}' for kind, r in zip(KINDS, supplied))
    review['candidate_reviews'] = [copy.deepcopy(row) for kind in KINDS for row in fragments[kind]['candidate_reviews']]
    review['character_reviews'] = copy.deepcopy(fragments['characters']['character_reviews'])
    return review


def merge_fragments(work):
    work = Path(work)
    pending, issues = {}, []
    try:
        with _lock(work):
            paths = [work / n for n in ('scenes.json', 'team.json', 'assets.json', 'review.json')]
            paths += [work / 'fragments' / f'{k}.json' for k in KINDS]
            expected = _watch_source(work, paths)
            data, scenes = _source(work)
            team = _read(work / 'team.json'); _identity(team, data)
            fragments, all_ids = {}, set()
            for kind in KINDS:
                path = work / 'fragments' / f'{kind}.json'
                if not path.exists():
                    pending[kind] = list(scenes)
                    issues.append(_issue('missing_fragment', kind, str(path), '缺少该类已验证片段')); continue
                value = _read(path)
                if value.get('kind') != kind:
                    issues.append(_issue('wrong_category', kind, str(path), '片段文件与类别不一致')); continue
                value, scope, found, warnings = _validate_fragment(data, scenes, value, other_ids=all_ids)
                issues.extend(found)
                pending[kind] = [sid for sid in scenes if sid not in scope]
                owner = team['owners'][kind]
                if owner.get('run', {}).get('status') in ('running','failed'):
                    issues.append(_issue('agent_incomplete',kind,'team.json','本次执行未成功提交；禁止用旧片段冒充完成'))
                if owner.get('status') != 'validated' or owner.get('fragment_sha256') != execution.digest(value):
                    issues.append(_issue('unsubmitted_fragment', kind, str(path), '片段内容须通过 submit，禁止直接写最终结果'))
                if pending[kind]:
                    issues.append(_issue('pending_scope', kind, 'scope', f'尚未审核：{pending[kind]}'))
                fragments[kind] = value
                all_ids.update(a['id'] for a in value.get('assets', []) if isinstance(a, dict) and 'id' in a)
            if issues:
                return dict(status='pending', submitted_scope={k: f['scope'] for k, f in fragments.items()}, pending_scope=pending, issues=issues)
            assets = {kind: fragments[kind]['assets'] for kind in KINDS}
            from build_xlsx import validate
            errors, warnings = validate(data, assets)
            old = execution.load_review(work / 'review.json')
            review = _combined_review(data, fragments, old)
            errors.extend(execution.validate_review(data, assets, review, bound=False))
            if errors:
                return dict(status='rejected', submitted_scope={k: list(scenes) for k in KINDS}, pending_scope=pending,
                            issues=[_issue('merge_validation', 'coordinator', 'assets/review', e) for e in errors], warnings=warnings)
            # Keep final binding empty: bind must perform independent review and warning approval.
            team['status'] = 'merged_pending_bind'
            _transaction({work / 'assets.json': assets, work / 'review.json': review,
                          work / 'team.json': team}, expected)
            return dict(status='merged_pending_bind', submitted_scope={k: list(scenes) for k in KINDS},
                        pending_scope=pending, issues=[], warnings=warnings, global_complete=False)
    except (OSError, ValueError, KeyError, TypeError) as error:
        return dict(status='rejected', submitted_scope={}, pending_scope=pending,
                    issues=[_issue('merge', 'coordinator', 'assets/review', error)])


def check_batch(work, scope, kind=None):
    """Read-only diagnostics of existing cumulative fragments; no pending scope is passed off as complete."""
    work = Path(work)
    try:
        data, scenes = _source(work)
        team = _read(work / 'team.json'); _identity(team, data)
        scope = _scope(scope, scenes)
        if kind is not None and kind not in KINDS:
            raise ValueError('kind 须为 characters/scenes/props')
        issues, submitted, pending = [], {}, {}
        for owner in (KINDS if kind is None else (kind,)):
            path = work / 'fragments' / f'{owner}.json'
            if not path.exists():
                pending[owner] = scope
                issues.append(_issue('missing_fragment', owner, str(path), '尚未提交片段')); continue
            value, actual, found, warnings = _validate_fragment(data, scenes, _read(path))
            issues.extend(found)
            if team['owners'][owner].get('run', {}).get('status') in ('running', 'failed'):
                issues.append(_issue('agent_incomplete', owner, 'team.json',
                                     '本次执行尚未成功提交；所列片段为旧提交，不能作为本次完成证明'))
            if (value.get('kind') != owner or team['owners'][owner].get('status') != 'validated'
                    or team['owners'][owner].get('fragment_sha256') != execution.digest(value)):
                issues.append(_issue('unsubmitted_fragment', owner, str(path), '当前片段未通过该 owner 的 submit'))
            submitted[owner] = [sid for sid in scope if sid in actual]
            pending[owner] = [sid for sid in scope if sid not in actual]
        return dict(submitted_scope=submitted, pending_scope=pending, issues=issues, global_complete=False)
    except (OSError, ValueError, KeyError, TypeError) as error:
        return _report(kind, issues=[_issue('batch', kind or 'coordinator', 'scope', error)])


def record_run(work, kind, status, agent_id='', error=''):
    """Record agent lifecycle; only a validated submit can mark a worker completed."""
    from datetime import datetime, timezone
    work=Path(work)
    try:
        with _lock(work):
            expected=_watch_source(work,[work/'team.json',work/'scenes.json'])
            data,_=_source(work)
            team=_read(work/'team.json');_identity(team,data)
            if kind not in KINDS or status not in ('running','failed'):
                raise ValueError('run 类别/状态无效；完成由 submit 验证，不由 agent 自报')
            owner=team['owners'][kind]
            run=owner.get('run',{})
            attempts=run.get('attempts',0)
            if type(attempts) is not int or attempts<0:
                raise ValueError('run 重试状态损坏')
            if status=='running':
                if run.get('status')=='running':
                    raise ValueError('该类别已有执行中的 agent，不能重复启动')
                if attempts>=3:
                    raise ValueError('连续执行已达3次；先处理阻塞原因，保留当前片段，不无限重试')
                attempts+=1
            elif run.get('status')!='running' or not isinstance(error,str) or not error.strip():
                raise ValueError('failed 须记录当前 running 任务的真实错误')
            owner['run']={'status':status,'attempts':attempts,'agent_id':agent_id,'error':error}
            team.setdefault('runs',[]).append({'kind':kind,**owner['run'],'at':datetime.now(timezone.utc).isoformat()})
            team['status']='pending'
            _transaction({work/'team.json':team},expected)
            return _report(kind,status=status,attempts=attempts)
    except (OSError,ValueError,KeyError,TypeError) as exc:
        return _report(kind,status='rejected',issues=[_issue('agent_run',kind,'team.json',exc)])
