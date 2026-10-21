"""One-call whole-series runner using the plugin's bundled Harness Engine."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT / "runtime"))
from harness_core.engine import Engine  # noqa: E402

from scene_log_core import load_source, prepare_scenes  # noqa: E402


def _node(node_id: str, capability: str, dependencies: list[str], bindings: dict,
          timeout: int = 900) -> dict:
    return {"id": node_id, "capability": capability, "depends_on": dependencies,
            "bindings": bindings, "idempotent": True, "retries": 1, "timeout_seconds": timeout}


def create_graph(scene_count: int) -> dict:
    nodes = []
    enrich_ids = []
    for index in range(1, scene_count + 1):
        key = f"scene_{index:03d}"
        segment_id = f"segment-{index:03d}"
        enrich_id = f"enrich-{index:03d}"
        nodes.append(_node(segment_id, "segment-scene", [], {
            "scene": {"from": f"inputs.{key}"}, "preferences": {"from": "inputs.preferences"}}))
        nodes.append(_node(enrich_id, "enrich-scene", [segment_id], {
            "scene": {"from": f"inputs.{key}"}, "preferences": {"from": "inputs.preferences"},
            "segmentation": {"from": segment_id}}))
        enrich_ids.append(enrich_id)
    bindings = {"source_path": {"from": "inputs.source_path"},
                "selected_episodes": {"from": "inputs.selected_episodes"}}
    for index, enrich_id in enumerate(enrich_ids, 1):
        bindings[f"scene_{index:03d}"] = {"from": enrich_id}
    nodes.append(_node("assemble", "assemble-scene-log", enrich_ids, bindings, 1200))
    nodes.append(_node("review", "review-continuity", ["assemble"], {
        "scene_log_path": {"from": "assemble.scene_log_path"},
        "source_path": {"from": "inputs.source_path"}}, 1200))
    nodes.append(_node("finalize", "finalize-scene-log", ["assemble", "review"], {
        "scene_log_path": {"from": "assemble.scene_log_path"},
        "workbook_path": {"from": "assemble.workbook_path"},
        "review": {"from": "review"}}, 600))
    return {"id": "extract-scene-log", "max_concurrency": 3, "nodes": nodes}


def run_pipeline(source_path: str | None, workspace: str | Path, output: str | Path,
                 selected_episodes: list[int] | None = None, resume: str | None = None,
                 preferences: dict | None = None) -> dict:
    workspace = Path(workspace).resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    engine = Engine(PLUGIN_ROOT, workspace)
    if resume:
        run_id = resume
    else:
        if not source_path:
            raise ValueError("首次运行必须提供 --source")
        source = Path(source_path).resolve()
        data = load_source(source)
        scenes = prepare_scenes(data, selected_episodes)
        inputs = {"source_path": str(source), "selected_episodes": selected_episodes or [],
                  "preferences": preferences or {}}
        for index, scene in enumerate(scenes, 1):
            inputs[f"scene_{index:03d}"] = scene
        run_id = engine.create(create_graph(len(scenes)), inputs)
    state = engine.execute(run_id)
    result = {"run_id": run_id, "status": state["status"], "workspace": str(workspace)}
    if state["status"] == "completed":
        destination = Path(output).resolve()
        destination.mkdir(parents=True, exist_ok=True)
        paths = []
        for item in state["nodes"]["finalize"]["artifacts"]:
            source_file = Path(item["path"])
            target = destination / source_file.name
            shutil.copy2(source_file, target)
            paths.append(str(target))
        result["artifacts"] = paths
        result["summary"] = state["nodes"]["finalize"]["output"]["result"]
    else:
        result["failed_nodes"] = {key: value.get("error") for key, value in state["nodes"].items()
                                  if value["status"] in {"failed", "blocked"}}
        result["questions"] = state.get("questions", [])
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="从一级剧本 JSON 提取整剧场记表")
    parser.add_argument("--source", help="standardized_screenplay_v1 JSON 文件")
    parser.add_argument("--workspace", required=True, help="Harness 状态目录")
    parser.add_argument("--output", required=True, help="交付目录")
    parser.add_argument("--episodes", help="指定集重跑，如 2,3")
    parser.add_argument("--resume", help="续跑已有 run_id")
    parser.add_argument("--model")
    parser.add_argument("--aspect-ratio")
    parser.add_argument("--lighting-preference")
    args = parser.parse_args()
    try:
        selected = [int(item) for item in args.episodes.split(",")] if args.episodes else None
        prefs = {key: value for key, value in {
            "model": args.model, "aspect_ratio": args.aspect_ratio,
            "lighting_preference": args.lighting_preference}.items() if value}
        result = run_pipeline(args.source, args.workspace, args.output, selected, args.resume, prefs)
    except (ValueError, OSError) as exc:
        result = {"status": "error", "error": str(exc)}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
