"""可回查的省略宾语动作关联；结构成立仍须人工审查指代语义。

action_refs 的区间和 quote 指完整候选动作分句，mention_id 指同资产的
实际先行称呼。只支持同一行逗号连接的相邻分句，不自动寻找/生成关联。
"""
import re
from source_candidates import PROP_ACTIONS, PROP_TERMS

_PLACEHOLDER = re.compile(r'^(?:已完成|完成|已检查|已审核|已审阅|已读|全部已读|已核对|无|暂无|无问题|通过|ok|done|待填写|待补充|未说明)[。.!！\s]*$', re.I)


def validate_action_refs(candidate, item, assets, scene=None):
    """返回 (关联到的资产 ID 集合, 错误列表)。缺少字段兼容旧直接匹配。

    candidate 须为从原文重算的候选，不能将台账自己声明的 source 作为原文。
    scene 可提供原场次人物名称，以补充尚未建资产的人物干扰检查。
    """
    refs = item.get('action_refs', [])
    cid = candidate.get('candidate_id', '候选')
    if not isinstance(refs, list):
        return set(), [f'{cid} action_refs 必须为数组']
    if not refs:
        return set(), []
    if candidate.get('kind') != 'prop_action' or item.get('decision') != 'recorded':
        return set(), [f'{cid} action_refs 仅用于 recorded prop_action']
    if len(refs) != 1:
        return set(), [f'{cid} 省略宾语 action_refs 须只关联一个局部先行实物']
    ref = refs[0]
    if not isinstance(ref, dict):
        return set(), [f'{cid} action_refs 引用必须为对象']
    source = candidate['source']
    sid, line, text = source['scene_id'], source['line'], source['quote']
    low, high = candidate['start_offset'], candidate['end_offset']
    if (type(low) is not int or type(high) is not int or not 0 <= low < high <= len(text)
            or text[low:high] != candidate['cue']):
        return set(), [f'{cid} 动作候选须由完整原文真实区间重算']
    if (ref.get('scene_id') != sid or type(ref.get('line')) is not int or ref['line'] != line
            or type(ref.get('start_offset')) is not int or type(ref.get('end_offset')) is not int
            or ref['start_offset'] != low or ref['end_offset'] != high
            or ref.get('quote') != text[low:high]):
        return set(), [f'{cid} action_refs 定位和引文须精确覆盖完整动作候选']
    reason = ref.get('reason')
    if not isinstance(reason, str) or not reason.strip() or _PLACEHOLDER.fullmatch(reason.strip()):
        return set(), [f'{cid} action_refs 缺少具体局部指代理由']
    aid, mid = ref.get('asset_id'), ref.get('mention_id')
    ids = item.get('asset_ids')
    if (not isinstance(aid, str) or not aid.strip() or not isinstance(mid, str) or not mid.strip()
            or not isinstance(ids, list) or any(not isinstance(value, str) for value in ids) or aid not in ids):
        return set(), [f'{cid} action_refs 须引用本候选关联道具和真实 mention_id']
    props = [p for p in assets.get('props', []) if p.get('id') == aid]
    if len(props) != 1:
        return set(), [f'{cid} action_refs 引用道具不存在或 ID 重复']
    mentions = [m for m in props[0].get('mentions', []) if m.get('id') == mid]
    if len(mentions) != 1:
        return set(), [f'{cid} action_refs mention_id 不属于该道具或重复']
    mention = mentions[0]
    msource = mention.get('source', {})
    ml, mh = mention.get('start_offset'), mention.get('end_offset')
    if (msource.get('scene_id') != sid or type(msource.get('line')) is not int or msource['line'] != line
            or mention.get('visibility') != 'visible' or not mention.get('state_id')
            or type(ml) is not int or type(mh) is not int or not 0 <= ml < mh <= low
            or text[ml:mh] != mention.get('raw_name')
            or not isinstance(msource.get('quote'), str) or not msource['quote']
            or msource['quote'] not in text or mention['raw_name'] not in msource['quote']
            or mention['state_id'] not in {s.get('id') for s in props[0].get('states', [])}):
        return set(), [f'{cid} action_refs 须回查同一行先行 visible mention 的真实称呼/区间/状态']
    bridge = text[mh:low]
    if re.search(r'[。；;！？!?\n\r]', bridge) or len(re.findall(r'[，,]', bridge)) != 1:
        return set(), [f'{cid} action_refs 只允许同句逗号连接的相邻局部分句']
    # 最近位置包含所有已登记称呼，reference 也不能被跳过；未登记常见
    # 道具线索同样阻断。词典并不完整，因此这里只是保守结构门槛。
    for prop in assets.get('props', []):
        for other in prop.get('mentions', []):
            other_source = other.get('source', {})
            ol, oh = other.get('start_offset'), other.get('end_offset')
            if (other_source.get('scene_id') == sid and other_source.get('line') == line
                    and type(ol) is int and type(oh) is int
                    and ol < high and oh > mh and (prop.get('id'), other.get('id')) != (aid, mid)):
                return set(), [f'{cid} action_refs 先行称呼与动作之间存在其他物件称呼，不能跳借']
    if PROP_TERMS.search(text[mh:high]):
        return set(), [f'{cid} action_refs 间隔或动作内仍有其他道具线索，须单独回查实物']
    names = set(scene.get('characters', []) if isinstance(scene, dict) else [])
    for char in assets.get('characters', []):
        names.update([char.get('name', ''), *char.get('aliases', [])])
    action = PROP_ACTIONS.search(text[low:high])
    if not action:
        return set(), [f'{cid} action_refs 缺少实际动作线索']
    # 接收者可出现在动作后（交给周衡）；先行称呼后的新人物、或动作
    # 之前的新主语须保守拒绝，不由字符距离决定其仍沿用同一实物。
    before_action = text[mh:low + action.start()]
    if any(name and name in before_action for name in names):
        return set(), [f'{cid} action_refs 最近称呼到动作前存在人物干扰，须另行语义回查']
    return {aid}, []
