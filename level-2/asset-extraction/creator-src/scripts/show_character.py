#!/usr/bin/env python3
"""输出人物全剧候选场次及带行号原文。命中不代表出镜，须人工判读。

用法: python3 show_character.py <scenes.json> <人物名> [别名 ...]
"""
import json
import sys
import argparse
from character_changes import change_candidates


def candidates(data, names):
    for ep in data['episodes']:
        for scene in ep['scenes']:
            reasons = []
            if set(names) & set(scene.get('characters', [])):
                reasons.append('人物行')
            if any(line.get('speaker') in names for line in scene.get('lines', [])):
                reasons.append('对白/画外音（须判读）')
            if any(any(name in line.get('text', '') for name in names)
                   for line in scene.get('lines', [])):
                reasons.append('正文提及（须判读）')
            if reasons:
                yield ep, scene, reasons


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('scenes_file')
    parser.add_argument('names', nargs='+')
    parser.add_argument('--changes', action='store_true', help='输出独立外观候选 JSON，供填写 change_reviews')
    args = parser.parse_args()
    with open(args.scenes_file, encoding='utf-8') as stream:
        data = json.load(stream)
    names = args.names
    if args.changes:
        char = {'name': names[0], 'aliases': names[1:]}
        print(json.dumps(list(change_candidates(data, char)), ensure_ascii=False, indent=2))
        return
    for ep, scene, reasons in candidates(data, names):
        print(f'\n# 第{ep["episode"]}集 {scene["scene_id"]} {scene["location"]} {scene["int_ext"]} {scene["time"]}')
        print('命中：' + '、'.join(reasons))
        print('人物：' + '、'.join(scene.get('characters', [])))
        for i, line in enumerate(scene.get('lines', []), 1):
            if line['type'] == 'dialog':
                voice = f'[{line.get("voice")}]' if line.get('voice') else ''
                print(f'L{i} {line["speaker"]}{voice}：{line["text"]}')
            else:
                prefix = '▲ ' if line['type'] == 'action' else ''
                print(f'L{i} {prefix}{line["text"]}')


if __name__ == '__main__':
    main()
