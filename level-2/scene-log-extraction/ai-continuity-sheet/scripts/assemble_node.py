"""Harness Python node: validate scene results and assemble the 13-column output."""

import argparse
import json
from pathlib import Path

from scene_log_core import assemble, load_source, prepare_scenes, write_workbook


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    task = json.loads(Path(args.input).read_text(encoding="utf-8"))
    inputs = task["inputs"]
    data = load_source(inputs["source_path"])
    scenes = prepare_scenes(data, inputs.get("selected_episodes"))
    results = {scene["scene_id"]: inputs[f"scene_{index:03d}"] for index, scene in enumerate(scenes, 1)}
    log = assemble(data, scenes, results)
    directory = Path(task["artifact_dir"])
    directory.mkdir(parents=True, exist_ok=True)
    json_path = directory / "scene_log.json"
    xlsx_path = directory / "scene_log.xlsx"
    json_path.write_text(json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_workbook(log, data, xlsx_path)
    result = {
        "status": "succeeded",
        "result": {"scene_log_path": str(json_path), "workbook_path": str(xlsx_path),
                   "episodes": len(log["episodes"]),
                   "scenes": sum(len(ep["scenes"]) for ep in log["episodes"]),
                   "beats": sum(len(scene["beats"]) for ep in log["episodes"] for scene in ep["scenes"])},
        "artifacts": ["scene_log.json", "scene_log.xlsx"], "questions": [], "error": None,
    }
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
