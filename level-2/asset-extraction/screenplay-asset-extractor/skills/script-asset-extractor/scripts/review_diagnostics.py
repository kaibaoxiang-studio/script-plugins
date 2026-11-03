"""完整诊断及候选阅读分组；分组不删除线索、不生成审查结论。"""
import re
from execution_review import digest, source_errors, validate_review
from source_candidates import candidates

LOCATION = re.compile(r'(?<!\d)(\d+-\d+)(?::L(\d+))?')
ASSET = re.compile(r'\b(?:CHR|PRP|SCN)-\d+\b')


def classify(message):
    message = str(message)
    position = LOCATION.search(message)
    aid = ASSET.search(message)
    code, owner = 'data', 'coordinator'
    if 'DOCX' in message or '原文快照' in message or '重解析' in message:
        code = 'source'
    elif '资产快照' in message or '哈希' in message:
        code = 'snapshot'
    elif '独立审核' in message:
        code = 'independent_review'
    elif '漏审' in message or '未完成' in message:
        code = 'coverage'
    elif 'action_refs' in message or '动作引用' in message:
        code, owner = 'candidate_link', 'props'
    elif 'visible mentions' in message:
        code, owner = 'candidate_link', 'props'
    elif '候选' in message:
        code = 'candidate'
        if 'prop_' in message: owner = 'props'
        elif 'visual:' in message or 'timeline:' in message: owner = 'characters'
    if aid:
        prefix=aid.group().split('-')[0]
        owner={'CHR':'characters','PRP':'props','SCN':'scenes'}[prefix]
    elif '人物' in message and code=='data': owner='characters'
    elif '道具' in message and code=='data': owner='props'
    return {'code':code,'owner':owner,'scene_id':position.group(1) if position else None,
            'line':int(position.group(2)) if position and position.group(2) else None,
            'asset_id':aid.group() if aid else None,'message':message}


def report_errors(errors, stage='full_check'):
    rows=[classify(message) for message in errors]
    return {'stage':stage,'errors':rows,'counts':{'errors':len(rows)},'global_complete':False}


def candidate_groups(data):
    """Only group contained noun cues with their action clause; preserve every original ID once."""
    source=candidates(data)
    groups=[]; consumed=set()
    for action in (c for c in source if c['kind']=='prop_action'):
        members=[action]
        for term in source:
            if (term['kind']=='prop_term' and term['candidate_id'] not in consumed
                    and term['source']==action['source']
                    and action['start_offset']<=term['start_offset']<term['end_offset']<=action['end_offset']):
                members.append(term);consumed.add(term['candidate_id'])
        consumed.add(action['candidate_id'])
        groups.append({'group_id':'G-'+digest([m['candidate_id'] for m in members])[:16],
                       'kind':'prop_clause','source':action['source'],
                       'candidate_ids':[m['candidate_id'] for m in members],'candidates':members})
    for item in source:
        if item['candidate_id'] not in consumed:
            groups.append({'group_id':'G-'+digest(item['candidate_id'])[:16],'kind':item['kind'],
                           'source':item['source'],'candidate_ids':[item['candidate_id']],'candidates':[item]})
    return groups


def diagnostics(data,assets,review,bound=False,scene_ids=None):
    from build_xlsx import validate
    source=source_errors(data)
    business,warnings=validate(data,assets)
    try:
        execution=validate_review(data,assets,review,bound=bound) if not business else []
    except (ValueError,KeyError,TypeError) as error:
        execution=[str(error)]
    from audit_state import audit_errors
    semantic=audit_errors(data,assets,review) if not business else []
    messages=list(dict.fromkeys(source+business+execution+semantic))
    report=report_errors(messages,'batch_diagnostic' if scene_ids is not None else 'full_check')
    report['warnings']=[classify(w) for w in warnings]
    if scene_ids is not None:
        scope=set(scene_ids)
        allids={s['scene_id'] for ep in data['episodes'] for s in ep['scenes']}
        if not scope<=allids:
            report['errors'].append(classify('批次包含未知场次'))
        selected=[];global_issues=[]
        for error in report['errors']:
            if error['scene_id'] in scope: selected.append(error)
            else: global_issues.append(error)  # 不将无法定位/其他批次问题过滤成通过。
        report['errors']=selected;report['global_issues']=global_issues
        report['pending_scope']=sorted(allids-scope)
    report['counts']['errors']=len(messages)
    report['counts']['warnings']=len(warnings)
    report['global_complete']=False
    return report
