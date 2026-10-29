#!/usr/bin/env python3
"""按集范围输出紧凑剧本文本，供分批提取资产时阅读。

用法:
    python3 show_episodes.py <scenes.json> <起始集> <结束集>
"""
import json
import sys


def main():
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    with open(sys.argv[1], encoding='utf-8') as f:
        data = json.load(f)
    start, end = int(sys.argv[2]), int(sys.argv[3])

    for ep in data['episodes']:
        if not start <= ep['episode'] <= end:
            continue
        print(f'# 第{ep["episode"]}集｜{ep["title"]}')
        print(f'概要：{ep["summary"]}')
        for s in ep['scenes']:
            print(f'\n## {s["scene_id"]} {s["location"]} {s["int_ext"]} {s["time"]}')
            print(f'人物：{"、".join(s["characters"])}')
            for line_no, ln in enumerate(s['lines'], 1):
                if ln['type'] == 'action':
                    print(f'L{line_no} ▲ {ln["text"]}')
                elif ln['type'] == 'dialog':
                    # 保留情绪括号和 VO/OS 标记：情绪可能提示剧变（比如情绪剧变常伴随外观
                    # 剧变），VO 画外音不代表角色在画面中
                    emo = f'（{ln["emotion"]}）' if ln.get('emotion') else ''
                    tag = f' [{ln["voice"]}]' if ln['voice'] else ''
                    print(f'L{line_no} {ln["speaker"]}{emo}{tag}：{ln["text"]}')
                else:
                    print(f'L{line_no} {ln["text"]}')
        print()


if __name__ == '__main__':
    main()
