#!/usr/bin/env python3
"""回查道具的异称与指代上下文；仅输出候选，不自动认定同一实物。"""
import argparse
import json
from asset_validation import input_errors
from prop_identity import prop_candidates, related_props


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('scenes_file')
    parser.add_argument('assets_file')
    parser.add_argument('prop_id', nargs='?')
    parser.add_argument('--terms', nargs='*', default=[], help='补充疑似异称/简称，仅供本次回查')
    parser.add_argument('--related', action='store_true', help='列出可能重复的道具对，不直接合并')
    parser.add_argument('--json', action='store_true', help='以 JSON 输出原文候选位置')
    args = parser.parse_args()
    try:
        with open(args.scenes_file, encoding='utf-8') as stream:
            data = json.load(stream)
        with open(args.assets_file, encoding='utf-8') as stream:
            assets = json.load(stream)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        parser.exit(1, f'错误: 无法读取 JSON：{error}\n')
    errors = input_errors(data, assets)
    if errors:
        parser.exit(1, '\n'.join(errors) + '\n')
    if args.related:
        print(json.dumps(list(related_props(assets)), ensure_ascii=False, indent=2))
        return
    prop = next((item for item in assets['props'] if item['id'] == args.prop_id), None)
    if prop is None:
        parser.error('指定有效的道具 ID，或使用 --related')
    matches = list(prop_candidates(data, prop, args.terms))
    if args.json:
        print(json.dumps(matches, ensure_ascii=False, indent=2))
        return
    by_scene = {}
    for item in matches:
        by_scene.setdefault(item['source']['scene_id'], []).append(item)
    for ep in data['episodes']:
        for scene in ep['scenes']:
            if scene['scene_id'] not in by_scene:
                continue
            print(f'\n# {scene["scene_id"]} {scene["location"]} {scene["int_ext"]} {scene["time"]}')
            print('候选称呼：' + '、'.join(dict.fromkeys(item['raw_name'] for item in by_scene[scene['scene_id']])))
            print('人物：' + '、'.join(scene['characters']))
            for line_no, line in enumerate(scene['lines'], 1):
                prefix = '▲ ' if line['type'] == 'action' else (line.get('speaker', '') + '：' if line['type'] == 'dialog' else '')
                print(f'L{line_no} {prefix}{line["text"]}')


if __name__ == '__main__':
    main()
