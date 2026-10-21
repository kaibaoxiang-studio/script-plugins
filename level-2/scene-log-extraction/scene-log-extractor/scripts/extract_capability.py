"""Harness public capability adapter for the dynamic whole-series runner."""

import argparse
import json
from pathlib import Path

from run_scene_log import run_pipeline


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    task = json.loads(Path(args.input).read_text(encoding="utf-8"))
    inputs = task["inputs"]
    directory = Path(task["artifact_dir"])
    try:
        result = run_pipeline(inputs["source_path"], directory / "work", directory,
                              inputs.get("selected_episodes"), None, inputs.get("preferences"))
    except (ValueError, OSError) as exc:
        result = {"status": "error", "error": str(exc)}
    if result["status"] != "completed":
        envelope = {"status": "failed", "result": {}, "artifacts": [], "questions": [],
                    "error": f"按场运行未完成；run_id={result.get('run_id')}；{result.get('failed_nodes', result.get('error'))}"}
    else:
        envelope = {"status": "succeeded", "result": {**result["summary"], "run_id": result["run_id"]},
                    "artifacts": [Path(path).name for path in result["artifacts"]],
                    "questions": [], "error": None}
    Path(args.output).write_text(json.dumps(envelope, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
