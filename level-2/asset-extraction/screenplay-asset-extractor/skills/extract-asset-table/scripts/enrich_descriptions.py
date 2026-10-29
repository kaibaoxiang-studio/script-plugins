#!/usr/bin/env python3
"""
只读回查道具/场景原文；命中只是提及候选，不自动补写或合并道具。
"""
import json
import sys
from prop_identity import prop_candidates
from asset_validation import input_errors

def load_json(path):
    with open(path, 'r') as f:
        return json.load(f)

def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def extract_action_lines(scenes_data):
    """提取所有场次的动作行，按场次ID索引"""
    action_by_scene = {}
    for ep in scenes_data['episodes']:
        for scene in ep['scenes']:
            sid = scene['scene_id']
            actions = []
            for line in scene.get('lines', []):
                if line['type'] == 'action':
                    text = line['text'].strip()
                    if text:
                        actions.append(text)
            action_by_scene[sid] = {
                'location': scene['location'],
                'int_ext': scene['int_ext'],
                'time': scene['time'],
                'characters': scene['characters'],
                'actions': actions
            }
    return action_by_scene

def find_prop_mentions(prop_name, aliases, action_by_scene):
    """查找道具在剧本中的所有提及"""
    mentions = []
    all_names = [prop_name] + list(aliases)

    for sid, scene_data in action_by_scene.items():
        for action in scene_data['actions']:
            for name in all_names:
                if name in action:
                    mentions.append({
                        'scene_id': sid,
                        'text': action
                    })
                    break  # 一行只记录一次
    return mentions

def find_scene_descriptions(scene_name, aliases, action_by_scene):
    """查找场景在剧本中的所有描述"""
    descriptions = []
    all_names = [scene_name] + list(aliases)

    for sid, scene_data in action_by_scene.items():
        # 检查是否是该场景
        is_target = any(name in scene_data['location'] for name in all_names)
        if is_target:
            descriptions.append({
                'scene_id': sid,
                'location': scene_data['location'],
                'actions': scene_data['actions']
            })
    return descriptions

def main():
    if len(sys.argv) != 3:
        print("用法: python3 enrich_descriptions.py scenes.json assets.json")
        sys.exit(1)

    scenes_path = sys.argv[1]
    assets_path = sys.argv[2]

    print("读取剧本和资产数据...")
    scenes_data = load_json(scenes_path)
    assets_data = load_json(assets_path)
    errors = input_errors(scenes_data, assets_data)
    if errors:
        for error in errors:
            print('错误:', error)
        sys.exit(1)

    print("提取所有动作行...")
    action_by_scene = extract_action_lines(scenes_data)

    print("\n" + "="*80)
    print("道具详细描述提取")
    print("="*80)

    # 为每个道具提取描述
    for prop in assets_data['props']:
        prop_name = prop['name']
        aliases = prop.get('aliases', [])

        mentions = [{'scene_id': match['source']['scene_id'], 'text': match['source']['quote'],
                     'line': match['source']['line'], 'raw_name': match['raw_name'], 'line_type': match['line_type']}
                    for match in prop_candidates(scenes_data, prop)]

        if mentions:
            print(f"\n【{prop['id']} {prop_name}】")
            print(f"  当前描述: {prop.get('description', '(空)')}")
            print(f"  剧本提及 {len(mentions)} 次:")
            for m in mentions:
                print(f"    {m['scene_id']}:L{m['line']} [{m['line_type']}]「{m['raw_name']}」: {m['text']}")
            print('  名称命中不证明实物身份，须核对指代记录与异称证据。')

            # 合并提取详细描述
            full_desc = "\n".join([m['text'] for m in mentions])
            print(f"\n  建议详细描述: (需要人工提炼)")
            print(f"    {full_desc[:150]}...")

    print("\n" + "="*80)
    print("场景详细描述提取")
    print("="*80)

    # 为每个场景提取描述
    for scene in assets_data['scenes']:
        scene_name = scene['name']
        aliases = scene.get('aliases', [])

        descriptions = find_scene_descriptions(scene_name, aliases, action_by_scene)

        if descriptions:
            print(f"\n【{scene['id']} {scene_name}】")
            print(f"  当前描述: {scene.get('description', '(空)')[:60]}...")
            print(f"  剧本出现 {len(descriptions)} 次:")

            # 合并所有动作行
            all_actions = []
            for desc in descriptions:
                all_actions.extend(desc['actions'])

            print(f"  建议详细描述: (需要人工提炼)")
            for i, action in enumerate(all_actions[:5], 1):  # 只显示前5条
                print(f"    {i}. {action[:70]}...")

    print("\n" + "="*80)
    print("提示: 以上是从剧本提取的原文，需要人工提炼成精细的视觉描述")
    print("="*80)

if __name__ == '__main__':
    main()
