#!/usr/bin/env python3
"""Export the normalizer's scene map as a basic, evidence-linked CSV index."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


FIELDS = (
    "source_id", "draft_id", "scene_id", "scene_number", "heading",
    "int_ext", "location", "time_of_day", "certainty",
    "source_refs", "source_start", "source_end", "source_unit", "text",
)


def safe_cell(value: object) -> str:
    if value is None:
        return ""
    result = value if isinstance(value, str) else str(value)
    return "'" + result if result.lstrip().startswith(("=", "+", "-", "@")) else result


def export(data: dict) -> list[dict[str, str]]:
    manifest = data.get("source_manifest")
    scenes = data.get("scenes")
    if not isinstance(manifest, dict) or not isinstance(scenes, list) or not scenes:
        raise ValueError("Expected a nonempty normalizer scene map")
    rows = []
    for scene in scenes:
        if not isinstance(scene, dict) or not scene.get("id") or not scene.get("source_refs"):
            raise ValueError("Every scene needs an id and source_refs")
        span = scene.get("source_range") or {}
        if not isinstance(span, dict):
            raise ValueError("source_range must be an object")
        row = {
            "source_id": manifest.get("source_id"),
            "draft_id": manifest.get("draft_id"),
            "scene_id": scene["id"],
            "scene_number": scene.get("scene_number"),
            "heading": scene.get("heading"),
            "int_ext": scene.get("int_ext"),
            "location": scene.get("location"),
            "time_of_day": scene.get("time_of_day"),
            "certainty": scene.get("certainty"),
            "source_refs": json.dumps(scene["source_refs"], ensure_ascii=False),
            "source_start": span.get("start"),
            "source_end": span.get("end"),
            "source_unit": span.get("unit"),
            "text": scene.get("text"),
        }
        rows.append({key: safe_cell(row[key]) for key in FIELDS})
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scene_map", type=Path)
    parser.add_argument("output_csv", type=Path)
    args = parser.parse_args()
    try:
        data = json.loads(args.scene_map.read_text(encoding="utf-8"))
        rows = export(data)
        args.output_csv.parent.mkdir(parents=True, exist_ok=True)
        with args.output_csv.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        parser.exit(1, f"ERROR: {exc}\n")
    print(f"Exported {len(rows)} scene rows to {args.output_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
