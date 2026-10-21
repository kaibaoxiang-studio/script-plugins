#!/usr/bin/env python3
"""Print a bounded episode batch from an asset-extraction work file."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("work")
    parser.add_argument("start", type=int)
    parser.add_argument("end", type=int)
    args = parser.parse_args()
    if args.start < 1 or args.end < args.start or args.end - args.start > 4:
        raise SystemExit("一次读取 1 至 5 集")
    data = json.loads(Path(args.work).read_text(encoding="utf-8"))
    for scene in data["scenes"]:
        if not args.start <= scene["episode"] <= args.end:
            continue
        print(f"\n{scene['scene_id']} {scene['location']} {scene['interior_exterior']} {scene['time']}")
        print("人物：" + "、".join(scene["characters"]))
        for block in scene["blocks"]:
            speaker = block.get("speaker", "")
            print(f"[{block['type']} {speaker} {block['origin']} {','.join(block['source_refs'])}] {block['text']}")


if __name__ == "__main__":
    main()
