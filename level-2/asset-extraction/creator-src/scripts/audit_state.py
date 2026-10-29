"""独立审查的范围绑定；指纹证明记录对应当前数据，不证明实际通读或语义正确。"""
import copy
from pathlib import Path
from execution_review import VERSION, digest, asset_digest, concrete, source_errors

SCHEMA = 'asset_independent_audit_v1'
OWNERS = {'characters', 'props', 'scenes', 'validator', 'coordinator'}


def all_scenes(data):
    return {s['scene_id']: s for ep in data['episodes'] for s in ep['scenes']}


def review_digest(review):
    return digest({k: review.get(k, []) for k in ('scenes', 'candidate_reviews', 'character_reviews', 'parse_reviews')})


def scene_fingerprint(data, assets, review, sid):
    from execution_review import scene_assets
    groups = scene_assets(assets, sid)
    related = {k: [a for a in assets[k] if a['id'] in groups[k]] for k in groups}
    return digest({'version': VERSION, 'source': digest(data), 'scene': all_scenes(data)[sid],
                   'assets': related, 'review': [r for r in review.get('scenes', []) if r.get('scene_id') == sid],
                   'candidates': [r for r in review.get('candidate_reviews', []) if r.get('source', {}).get('scene_id') == sid],
                   'parse_reviews': review.get('parse_reviews', [])})


def character_fingerprint(data, assets, review, cid):
    char = next(c for c in assets['characters'] if c['id'] == cid)
    sids = {r['scene_id'] for r in char.get('appearances', [])}
    return digest({'version': VERSION, 'source': digest(data), 'character': char,
                   'scenes': {sid: scene_fingerprint(data, assets, review, sid) for sid in sorted(sids)},
                   'review': [r for r in review.get('character_reviews', []) if r.get('character_id') == cid]})


def scope_snapshots(data, assets, review):
    return {'scenes': {sid: scene_fingerprint(data, assets, review, sid) for sid in all_scenes(data)},
            'characters': {c['id']: character_fingerprint(data, assets, review, c['id']) for c in assets['characters']}}


def changed_scopes(data, assets, review):
    current = scope_snapshots(data, assets, review)
    prior = review.get('scope_snapshots')
    if not isinstance(prior, dict):
        prior = {}
    return {kind: [key for key, value in rows.items() if not isinstance(prior.get(kind), dict) or prior[kind].get(key) != value]
            for kind, rows in current.items()}


def audit_errors(data, assets, review):
    state = review.get('independent_review')
    if state is None:
        return []  # 原单agent台账兼容；team-init/merge才启用独立审查门槛。
    if not isinstance(state, dict) or state.get('required') is not True:
        return ['独立审核配置无效；不能用关闭标记绕过已启用的审核']
    errors = []
    snapshots = scope_snapshots(data, assets, review)
    for kind, expected in snapshots.items():
        records = state.get(kind)
        if not isinstance(records, dict):
            errors.append(f'独立审核 {kind} 必须为范围记录对象')
            continue
        for key, wanted in expected.items():
            record = records.get(key)
            if (not isinstance(record, dict) or record.get('snapshot_sha256') != wanted
                    or not concrete(record.get('conclusion')) or not concrete(record.get('reviewer_id'))):
                errors.append(f'独立审核待完成或已过期：{kind}/{key}')
        if set(records) - set(expected):
            errors.append(f'独立审核引用失效范围：{kind}/{sorted(set(records)-set(expected))}')
    issues = state.get('issues')
    if not isinstance(issues, list):
        return errors + ['独立审核 issues 必须为数组']
    for issue in issues:
        if not isinstance(issue, dict) or not concrete(issue.get('issue_id')):
            errors.append('独立审核问题记录无效')
        elif issue.get('status') != 'resolved':
            errors.append(f'独立审核问题未解决：{issue["issue_id"]} / {issue.get("owner", "coordinator")} / {issue.get("message", "")}')
    return errors


def audit_template(data, assets, review, scene_ids=None, character_ids=None):
    state = review.get('independent_review', {})
    snaps = scope_snapshots(data, assets, review)
    def missing(kind):
        records = state.get(kind, {}) if isinstance(state, dict) else {}
        if not isinstance(records, dict):
            records = {}
        return [key for key, val in snaps[kind].items() if not isinstance(records.get(key), dict)
                or records[key].get('snapshot_sha256') != val]
    # 未改业务数据也可能需解决审核误判；不要只由过期指纹生成待办。
    issues = state.get('issues', []) if isinstance(state, dict) else []
    if not isinstance(issues, list) or any(not isinstance(i, dict) for i in issues):
        raise ValueError('独立审核问题状态损坏，不能生成空复查模板')
    open_issues = [i for i in issues if i.get('status') != 'resolved']
    pending_sids = set(missing('scenes'))
    pending_cids = set(missing('characters'))
    for issue in open_issues:
        sid = issue.get('scene_id')
        if sid not in snaps['scenes']:
            raise ValueError('未解决审核问题引用失效场次')
        pending_sids.add(sid)
        if issue.get('owner') == 'characters' and issue.get('asset_id') in snaps['characters']:
            pending_cids.add(issue['asset_id'])
    sids = [sid for sid in snaps['scenes'] if sid in pending_sids] if scene_ids is None else scene_ids
    cids = [cid for cid in snaps['characters'] if cid in pending_cids] if character_ids is None else character_ids
    if len(set(sids)) != len(sids) or not set(sids) <= set(snaps['scenes']):
        raise ValueError('独立审核范围包含未知或重复场次')
    if len(set(cids)) != len(cids) or not set(cids) <= set(snaps['characters']):
        raise ValueError('独立审核范围包含未知或重复人物')
    return {'schema_version': SCHEMA, 'version': VERSION, 'source_sha256': digest(data),
            'assets_sha256': asset_digest(assets), 'review_sha256': review_digest(review),
            'audit_state_sha256': digest(review.get('independent_review')),
            'reviewer_id': '', 'scene_reviews': [{'scene_id': sid, 'conclusion': ''} for sid in sids],
            'character_reviews': [{'character_id': cid, 'conclusion': ''} for cid in cids],
            'issues': [], 'resolved_issue_ids': [],
            'open_issue_ids': [i.get('issue_id') for i in open_issues]}


def _check_issue(issue, data, assets):
    if not isinstance(issue, dict) or not concrete(issue.get('issue_id')) or not concrete(issue.get('message')):
        raise ValueError('审核问题须有 issue_id 与具体 message')
    if issue.get('owner') not in OWNERS:
        raise ValueError('审核问题 owner 无效')
    sid, line = issue.get('scene_id'), issue.get('line')
    scene = all_scenes(data).get(sid)
    if scene is None or type(line) is not int or not 1 <= line <= len(scene['lines']):
        raise ValueError('审核问题须定位真实场次及原文行')
    refs = issue.get('evidence_refs')
    if not isinstance(refs, list) or not refs:
        raise ValueError('审核问题须有实际原文 evidence_refs')
    for ref in refs:
        if not isinstance(ref, dict):
            raise ValueError('审核问题原文引用无效')
        s = all_scenes(data).get(ref.get('scene_id'))
        n = ref.get('line')
        if (s is None or type(n) is not int or not 1 <= n <= len(s['lines'])
                or not isinstance(ref.get('quote'), str) or not ref['quote']
                or ref['quote'] not in s['lines'][n-1]['text']):
            raise ValueError('审核问题原文引用过期或不匹配')
    if not any(ref.get('scene_id') == sid and ref.get('line') == line for ref in refs):
        raise ValueError('审核问题须有问题所在原文行的依据')
    aid = issue.get('asset_id')
    if issue.get('owner') == 'characters' and aid not in {c['id'] for c in assets['characters']}:
        raise ValueError('人物问题须引用该人物的真实 asset_id，才能全剧复查关闭')
    prefix = {'characters': 'CHR-', 'props': 'PRP-', 'scenes': 'SCN-'}.get(issue.get('owner'))
    if aid is not None and prefix and (not isinstance(aid, str) or not aid.startswith(prefix)):
        raise ValueError('审核问题资产与责任类别不匹配')
    if aid is not None and aid not in {a['id'] for k in assets for a in assets[k]}:
        raise ValueError('审核问题引用未知资产')


def apply_audit(data, assets, review, document):
    from execution_review import validate_review
    from build_xlsx import validate
    if not isinstance(document, dict):
        raise ValueError('独立审核提交必须为对象')
    errors, _ = validate(data, assets)
    errors += source_errors(data) + validate_review(data, assets, review, bound=False)
    if errors:
        raise ValueError('\n'.join(errors))
    expected = {'schema_version': SCHEMA, 'version': VERSION, 'source_sha256': digest(data),
                'assets_sha256': asset_digest(assets), 'review_sha256': review_digest(review),
                'audit_state_sha256': digest(review.get('independent_review'))}
    if any(document.get(k) != value for k, value in expected.items()):
        raise ValueError('独立审核提交来源、规则版本或数据快照已过期；重新读取当前数据')
    reviewer = document.get('reviewer_id')
    if not concrete(reviewer):
        raise ValueError('独立审核 reviewer_id 须标识实际审核者')
    result = copy.deepcopy(review)
    state = result.setdefault('independent_review', {'required': True, 'scenes': {}, 'characters': {}, 'issues': []})
    if not isinstance(state, dict) or state.get('required') is not True:
        raise ValueError('独立审核状态无效')
    snaps = scope_snapshots(data, assets, review)
    reviewed = {}
    for kind, label, idkey in (('scenes', 'scene_reviews', 'scene_id'), ('characters', 'character_reviews', 'character_id')):
        rows = document.get(label)
        if not isinstance(rows, list):
            raise ValueError(label + ' 必须为数组')
        seen = set()
        for row in rows:
            if not isinstance(row, dict) or row.get(idkey) not in snaps[kind] or row[idkey] in seen:
                raise ValueError(label + ' 包含未知或重复范围')
            key = row[idkey]
            seen.add(key)
            if not concrete(row.get('conclusion')):
                raise ValueError(key + ' 缺少独立回查的具体结论')
            state.setdefault(kind, {})[key] = {'snapshot_sha256': snaps[kind][key], 'reviewer_id': reviewer,
                                              'conclusion': row['conclusion']}
        reviewed[kind] = seen
    if not any(reviewed.values()):
        raise ValueError('独立审核提交未包含实际复查范围')
    issues = document.get('issues')
    resolved = document.get('resolved_issue_ids')
    if not isinstance(issues, list) or not isinstance(resolved, list) or any(not isinstance(k, str) for k in resolved):
        raise ValueError('issues/resolved_issue_ids 须为数组')
    previous = state.get('issues', [])
    if not isinstance(previous, list):
        raise ValueError('已存审核问题状态损坏')
    by_id = {i['issue_id']: i for i in previous}
    if len(resolved) != len(set(resolved)) or not set(resolved) <= set(by_id):
        raise ValueError('复查解决记录引用未知或重复问题')
    for key in resolved:
        issue = by_id[key]
        if issue['scene_id'] not in reviewed['scenes']:
            raise ValueError('解决问题必须重新审核问题所在场次')
        if issue.get('owner') == 'characters' and issue.get('asset_id') not in reviewed['characters']:
            raise ValueError('人物问题解决须完成该人物全剧边界复查')
        issue['status'] = 'resolved'
        issue['resolved_by'] = reviewer
    seen = set()
    for issue in issues:
        _check_issue(issue, data, assets)
        key = issue['issue_id']
        if key in seen or key in resolved:
            raise ValueError('审核问题ID重复或同时声称解决')
        seen.add(key)
        if issue['scene_id'] not in reviewed['scenes']:
            raise ValueError('新问题必须属于本次真实复查场次')
        if key in by_id:
            if any(by_id[key].get(k) != issue.get(k) for k in ('owner', 'scene_id', 'line', 'asset_id', 'message', 'evidence_refs')):
                raise ValueError('审核问题ID不可被改写为不同问题')
            by_id[key]['status'] = 'open'
        else:
            by_id[key] = {**issue, 'status': 'open', 'reported_by': reviewer}
    state['issues'] = list(by_id.values())
    # 删除已经不再存在的范围，但不能借删资产清除尚未解决的问题。
    for kind in snaps:
        state[kind] = {key: val for key, val in state[kind].items() if key in snaps[kind]}
    return result


def submit_audit(work, path):
    from workflow import read
    from team_workflow import _lock, _watch_source, _transaction
    work = Path(work)
    with _lock(work):
        paths = [work/name for name in ('scenes.json', 'assets.json', 'review.json', 'team.json')]
        paths.append(Path(path))
        expected = _watch_source(work, paths)
        data, assets, review = (read(work/name) for name in ('scenes.json', 'assets.json', 'review.json'))
        if (work/'team.json').exists():
            from team_workflow import _identity
            team=read(work/'team.json')
            _identity(team,data)
            if team.get('status') != 'merged_pending_bind':
                raise ValueError('片段尚未合并为当前结果；先完成 merge 再独立审核')
        result = apply_audit(data, assets, review, read(path))
        _transaction({work/'review.json': result}, expected)
        return {'stage': 'independent_review', 'issues': audit_errors(data, assets, result)}


def team_mode_errors(data, review, roots):
    """Standalone export/check commands must honor the same enabled team gate."""
    import json
    from team_workflow import _identity
    errors=[]
    for root in {Path(path).resolve() for path in roots}:
        path=root/'team.json'
        if not path.exists():
            continue
        try:
            team=json.loads(path.read_text(encoding='utf-8'))
            if not isinstance(team,dict):
                raise ValueError('team.json 顶层须为对象')
            _identity(team,data)
            state=review.get('independent_review')
            if (team.get('status')!='merged_pending_bind' or not isinstance(state,dict)
                    or state.get('required') is not True):
                errors.append('分工未合并或独立审核配置缺失；不能绕过已启用的审核')
        except (OSError,ValueError,KeyError,TypeError) as error:
            errors.append(str(error))
    return errors
