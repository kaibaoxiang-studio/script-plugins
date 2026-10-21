"""Harness Python node: merge continuity findings and publish four artifacts."""

import argparse
import json
import shutil
from pathlib import Path

from scene_log_core import structural_findings, write_report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    task = json.loads(Path(args.input).read_text(encoding="utf-8"))
    inputs = task["inputs"]
    directory = Path(task["artifact_dir"])
    directory.mkdir(parents=True, exist_ok=True)
    for key, name in (("scene_log_path", "scene_log.json"), ("workbook_path", "scene_log.xlsx")):
        shutil.copy2(inputs[key], directory / name)
    log = json.loads((directory / "scene_log.json").read_text(encoding="utf-8"))
    review = inputs.get("review", {})
    findings = structural_findings(log) + review.get("findings", [])
    write_report(log, findings, directory / "scene_log_report.json", directory / "scene_log_report.md")
    result = {
        "status": "succeeded",
        "result": {"episodes": len(log["episodes"]),
                   "scenes": sum(len(ep["scenes"]) for ep in log["episodes"]),
                   "beats": sum(len(sc["beats"]) for ep in log["episodes"] for sc in ep["scenes"]),
                   "findings": len(findings)},
        "artifacts": ["scene_log.json", "scene_log.xlsx", "scene_log_report.json", "scene_log_report.md"],
        "questions": [], "error": None,
    }
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
