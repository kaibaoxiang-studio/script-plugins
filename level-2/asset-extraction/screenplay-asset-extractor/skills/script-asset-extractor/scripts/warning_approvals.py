"""以精确警告和输入快照绑定确认记录，不支持一键忽略所有警告。"""
import hashlib
import json


def source_digest(data, assets):
    content = json.dumps({'script': data, 'assets': assets}, sort_keys=True,
                         ensure_ascii=False, separators=(',', ':'))
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def warning_id(message):
    return 'W-' + hashlib.sha256(message.encode('utf-8')).hexdigest()[:20]


def warning_report(data, assets, warnings):
    return {'source_digest': source_digest(data, assets), 'approvals': [],
            'warnings': [{'warning_id': warning_id(message), 'message': message}
                         for message in warnings]}


def apply_approvals(data, assets, warnings, document=None):
    if document is None:
        return warnings, [], []
    errors, accepted = [], []
    if not isinstance(document, dict) or not isinstance(document.get('approvals'), list):
        return warnings, [], ['警告确认文件必须为含 approvals 数组的对象']
    if document.get('source_digest') != source_digest(data, assets):
        return warnings, [], ['警告确认已失效：输入数据发生变化，须重新回查并确认']
    current = {warning_id(message): message for message in warnings}
    seen = set()
    for item in document['approvals']:
        if not isinstance(item, dict) or not all(isinstance(item.get(key), str) and item[key].strip()
                                               for key in ('warning_id', 'message', 'reason', 'confirmed_by')):
            errors.append('每条警告确认须含 warning_id、message、reason 和 confirmed_by 非空字符串')
            continue
        wid = item['warning_id']
        if wid in seen:
            errors.append(f'警告确认重复: {wid}')
        seen.add(wid)
        if current.get(wid) != item['message']:
            errors.append(f'警告确认不匹配当前警告: {wid}')
        else:
            accepted.append(item)
    if errors:
        return warnings, [], errors
    return [message for message in warnings if warning_id(message) not in seen], accepted, []


def approval_text(item):
    return f'{item["warning_id"]} {item["message"]}；确认人：{item["confirmed_by"]}；依据：{item["reason"]}'
