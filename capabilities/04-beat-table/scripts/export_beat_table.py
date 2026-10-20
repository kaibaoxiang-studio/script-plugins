#!/usr/bin/env python3
"""Export an existing screenplay breakdown's beats to a reviewable CSV table."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


FIELDS = (
    "project_id", "draft_id", "coverage_status", "beat_id", "scene_id",
    "source_refs", "change", "entry_state", "exit_state",
)


def safe_cell(value: object) -> str:
    if value is None:
        return ""
    result = value if isinstance(value, str) else str(value)
    return "'" + result if result.lstrip().startswith(("=", "+", "-", "@")) else result


def export(data: dict, allow_partial: bool = False) -> list[dict[str, str]]:
    coverage = data.get("coverage")
    beats = data.get("beats")
    scenes = data.get("scenes")
    if not isinstance(coverage, dict) or not isinstance(beats, list) or not isinstance(scenes, list):
        raise ValueError("Expected a screenplay breakdown with coverage, scenes and beats")
    status = coverage.get("status")
    if status != "completed" and not (allow_partial and status == "partial"):
        raise ValueError("Breakdown coverage must be completed, or partial with --allow-partial")
    scene_ids = {scene.get("id") for scene in scenes if isinstance(scene, dict)}
    rows = []
    for beat in beats:
        if not isinstance(beat, dict) or not beat.get("id") or beat.get("scene_id") not in scene_ids:
            raise ValueError("Every beat needs an id and a known scene_id")
        if not beat.get("source_refs") or not beat.get("change"):
            raise ValueError("Every beat needs source_refs and a change")
        row = {
            "project_id": (data.get("project") or {}).get("id"),
            "draft_id": (data.get("source_manifest") or {}).get("draft_id"),
            "coverage_status": status,
            "beat_id": beat["id"],
            "scene_id": beat["scene_id"],
            "source_refs": json.dumps(beat["source_refs"], ensure_ascii=False),
            "change": beat["change"],
            "entry_state": json.dumps(beat.get("entry_state") or {}, ensure_ascii=False),
            "exit_state": json.dumps(beat.get("exit_state") or {}, ensure_ascii=False),
        }
        rows.append({key: safe_cell(row[key]) for key in FIELDS})
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("breakdown", type=Path)
    parser.add_argument("output_csv", type=Path)
    parser.add_argument("--allow-partial", action="store_true")
    args = parser.parse_args()
    try:
        data = json.loads(args.breakdown.read_text(encoding="utf-8"))
        rows = export(data, args.allow_partial)
        args.output_csv.parent.mkdir(parents=True, exist_ok=True)
        with args.output_csv.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        parser.exit(1, f"ERROR: {exc}\n")
    print(f"Exported {len(rows)} beat rows to {args.output_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
