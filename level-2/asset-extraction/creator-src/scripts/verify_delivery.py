#!/usr/bin/env python3
"""Verify either the legacy JSON run or the packaged DOCX/Markdown workflow."""
import argparse, json
from pathlib import Path
import sys

from asset_core import asset_payload, read_json, require, validate_work
from execution_review import digest, asset_digest


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


def sha256_file(path: Path) -> str:
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()

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
    # 保存后重新计算快照，防止旧验收文件或其他工作目录的产物冒充当前交付。
    expected_source = acceptance.get("source_sha256")
    expected_assets = acceptance.get("assets_sha256")
    require(expected_source == digest(source), "acceptance.source_sha256 与当前 scenes.json 不一致")
    require(expected_assets == asset_digest(result), "acceptance.assets_sha256 与当前 assets.json 不一致")
    output = acceptance.get("output")
    require(isinstance(output, str) and output, "acceptance.output 缺失")
    output_path = Path(output)
    if not output_path.is_absolute():
        output_path = directory / output_path
    require(output_path.resolve().parent == directory.resolve(), "acceptance.output 必须位于当前 artifact_dir")
    require(output_path.resolve() == (directory / "screenplay-asset-table.xlsx").resolve(), "acceptance.output 不是当前交付工作簿")
    require(acceptance.get("workbook_sha256") == sha256_file(directory / "screenplay-asset-table.xlsx"), "工作簿哈希与 acceptance 不一致")
    require(acceptance.get("assets_file_sha256") == sha256_file(directory / "assets.json"), "assets.json 哈希与 acceptance 不一致")
    require(acceptance.get("review_file_sha256") == sha256_file(directory / "review.json"), "review.json 哈希与 acceptance 不一致")
    visual_rows = (read_json(directory / "review.json").get("delivery_review") or {}).get("visual", [])
    require(isinstance(visual_rows, list) and visual_rows, "review.json 缺少视觉证据列表")
    for row in visual_rows:
        evidence = row.get("evidence_file") if isinstance(row, dict) else None
        digest = row.get("evidence_sha256") if isinstance(row, dict) else None
        require(isinstance(evidence, str) and evidence, "视觉证据路径缺失")
        evidence_path = Path(evidence)
        if not evidence_path.is_absolute(): evidence_path = directory / evidence_path
        require(evidence_path.resolve().is_file() and evidence_path.resolve().is_relative_to(directory.resolve()), "视觉证据文件不在当前 artifact_dir")
        require(digest == sha256_file(evidence_path), "视觉证据哈希与 review.json 不一致")
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
