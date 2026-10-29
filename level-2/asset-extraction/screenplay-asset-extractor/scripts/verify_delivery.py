#!/usr/bin/env python3
"""Verify either the legacy JSON run or the packaged DOCX/Markdown workflow."""
import argparse, json
from pathlib import Path
import sys

from asset_core import asset_payload, read_json, require, validate_work


def verify_legacy(directory: Path, expected_counts: dict | None):
    work = read_json(directory / "work.json")
    scene_map, warnings = validate_work(work)
    result = read_json(directory / "assets.json")
    require(result == asset_payload(work, scene_map), "assets.json 与已审核工作文件不一致")
    findings = read_json(directory / "asset_findings.json")
    require(findings.get("source") == work["source"], "疑点报告来源不一致")
    counts = {key: len(result[key]) for key in ("characters", "locations", "props", "effects", "scenes")}
    counts["findings"] = len(findings.get("findings", []))
    if expected_counts is not None:
        require(counts == expected_counts, "返回计数与实际交付文件不一致")
    return {"verified": True, "mode": "standardized_screenplay_v1", "counts": counts}


def verify_workflow(directory: Path, expected_counts: dict | None):
    required = ("scenes.json", "assets.json", "review.json", "acceptance.json", "screenplay-asset-table.xlsx")
    for name in required:
        require((directory / name).is_file(), f"缺少正式流程文件：{name}")
    progress = read_json(directory / "progress.json") if (directory / "progress.json").is_file() else {}
    require(progress.get("stage") == "complete", "workflow 未完成 finalize，禁止交付")
    acceptance = read_json(directory / "acceptance.json")
    require(acceptance.get("schema_version") == "asset_acceptance_v1", "acceptance.json 版本不匹配")
    require(acceptance.get("errors") == 0 and acceptance.get("unconfirmed_warnings") == 0,
            "workflow 验收仍有错误或未确认警告")
    require(acceptance.get("checks", {}).get("workbook") == "passed", "工作簿未通过保存后验收")
    require(acceptance.get("checks", {}).get("visual") == "evidence_recorded", "缺少视觉复核证据")
    result = read_json(directory / "assets.json")
    source = read_json(directory / "scenes.json")
    scene_count = len(source.get("scenes", [])) or sum(len(ep.get("scenes", [])) for ep in source.get("episodes", []))
    findings = acceptance.get("confirmed_warning_details", [])
    counts = {"characters": len(result.get("characters", [])), "locations": len(result.get("scenes", [])),
              "props": len(result.get("props", [])), "effects": len(result.get("effects", [])),
              "scenes": scene_count, "findings": len(findings)}
    if expected_counts is not None:
        require(counts == expected_counts, "返回计数与实际工作流交付不一致")
    return {"verified": True, "mode": "docx_markdown_workflow", "counts": counts}


def verify_delivery(directory: Path, expected_counts: dict | None = None):
    if (directory / "work.json").is_file():
        return verify_legacy(directory, expected_counts)
    return verify_workflow(directory, expected_counts)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--expected-counts", type=json.loads)
    args = parser.parse_args()
    try:
        print(json.dumps(verify_delivery(args.directory, args.expected_counts), ensure_ascii=False))
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(str(exc), file=sys.stderr); raise SystemExit(1)


if __name__ == "__main__": main()
