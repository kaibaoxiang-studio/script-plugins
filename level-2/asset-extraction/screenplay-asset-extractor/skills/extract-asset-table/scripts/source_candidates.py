"""从原文独立扫描待复核线索；不从资产清单反推，不自动决定资产身份。"""
import hashlib
import re
from character_changes import VISUAL_CUES

# 这不是完整道具词典；未命中表达仍由逐行阅读发现。
PROP_TERMS = re.compile(r'手机|电话|钥匙|匕首|手枪|步枪|枪支|宝剑|长剑|令牌|玉佩|戒指|项链|手镯|酒杯|水杯|茶杯|药瓶|药盒|药丸|信封|信件|合同|账本|登记本|钱包|银行卡|手提箱|行李箱|雨伞|汽车|轿车|马车|摩托车|自行车|货车|船只')
PROP_ACTIONS = re.compile(r'拿起|拿着|取出|掏出|递给|递交|交给|接过|放下|放在|握住|握着|拔出|捡起|举起|持着|驾驶|点燃|折断|砸碎')
BOUNDARIES = re.compile(r'闪回|返回现实|回到现实|梦境|蒙太奇|多年后|数年后|次日|翌日|时间跳跃')


def candidates(data):
    output = []
    for ep in data.get('episodes', []):
        for scene in ep.get('scenes', []):
            sid = scene['scene_id']
            for number, line in enumerate(scene.get('lines', []), 1):
                if line.get('type') not in ('action', 'other'):
                    continue
                text = line['text']
                digest = hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]
                spans = []
                for match in PROP_TERMS.finditer(text):
                    spans.append(('prop_term', match.start(), match.end()))
                for clause in re.finditer(r'[^，,。；;！？!?]+', text):
                    if PROP_ACTIONS.search(clause.group()):
                        spans.append(('prop_action', clause.start(), clause.end()))
                for pattern, kind in ((VISUAL_CUES, 'visual'), (BOUNDARIES, 'timeline')):
                    for match in pattern.finditer(text):
                        spans.append((kind, match.start(), match.end()))
                for kind, low, high in sorted(set(spans), key=lambda s: (s[1], s[2], s[0])):
                    output.append({'candidate_id': f'{sid}:L{number}:{kind}:{low}-{high}:{digest}',
                                   'kind': kind, 'start_offset': low, 'end_offset': high,
                                   'cue': text[low:high],
                                   'source': {'scene_id': sid, 'line': number, 'quote': text}})
    return output
