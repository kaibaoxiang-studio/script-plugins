#!/usr/bin/env python3
"""Verify the reviewed work and exported data before a Harness success result."""
import argparse
import json
from pathlib import Path
import sys

from asset_core import asset_payload, read_json, require, validate_work


def verify_delivery(directory: Path, expected_counts: dict | None = None) -> dict:
    work = read_json(directory / "work.json")
    scene_map, warnings = validate_work(work)
    result = read_json(directory / "assets.json")
    require(result == asset_payload(work, scene_map),
            "assets.json 与本版本已审核工作文件不一致，不能使用旧缓存或未审结果")
    findings = read_json(directory / "asset_findings.json")
    require(findings.get("source") == work["source"]
            and findings.get("findings") == [*work.get("findings", []), *warnings],
            "疑点报告与本次已审核工作文件不一致")
    counts = {key: len(result[key]) for key in ("characters", "locations", "props", "effects", "scenes")}
    counts["findings"] = len(findings["findings"])
    if expected_counts is not None:
        require(counts == expected_counts, "返回计数与实际交付文件不一致")
    return {"verified": True, "counts": counts,
            "reviewed_scenes": len(work["semantic_review"]["scenes"])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--expected-counts", type=json.loads)
    args = parser.parse_args()
    try:
        print(json.dumps(verify_delivery(args.directory, args.expected_counts), ensure_ascii=False))
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
