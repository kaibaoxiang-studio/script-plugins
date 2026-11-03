"""Group current warnings into reviewable rule families; never approves them."""
import json, re
from warning_approvals import warning_report

RULES=[('audio_only','广播|AI|ai音|通讯|声音'),('group_role','若干|小队|群体'),('missing_state','没有分配到任何状态')]
def group_warnings(data, assets):
    from build_xlsx import validate
    _, warnings=validate(data, assets)
    groups={key:[] for key,_ in RULES}; groups['other']=[]
    for message in warnings:
        key='other'
        for name, pattern in RULES:
            if re.search(pattern,message): key=name; break
        groups[key].append(message)
    return {'source_digest':warning_report(data,assets,warnings)['source_digest'], 'groups':groups,
            'warning_count':len(warnings), 'note':'分组仅用于人工复核，不代表已确认。'}

def approval_draft(data, assets):
    grouped=group_warnings(data,assets)
    approvals=[]
    from warning_approvals import warning_id
    for key,messages in grouped['groups'].items():
        for message in messages:
            approvals.append({'warning_id':warning_id(message),'message':message,'rule_group':key,
                              'reason':'','confirmed_by':''})
    return {'source_digest':grouped['source_digest'],'approvals':approvals,
            'note':'填写 reason 和 confirmed_by 后，人工检查每条消息，再作为 warning_approvals.json 使用。'}
