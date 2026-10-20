#!/usr/bin/env python3
"""Export an existing AssetCatalogV1 to a reviewable CSV table."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


FIELDS = (
    "project_id", "draft_id", "asset_id", "asset_type", "name", "aliases",
    "scene_ids", "source_refs", "certainty", "state_candidate_ids",
)


def safe_cell(value: object) -> str:
    if value is None:
        return ""
    result = value if isinstance(value, str) else str(value)
    return "'" + result if result.lstrip().startswith(("=", "+", "-", "@")) else result


def export(data: dict) -> list[dict[str, str]]:
    if data.get("schema_version") != "AssetCatalogV1":
        raise ValueError("Expected AssetCatalogV1")
    assets = data.get("assets")
    project = data.get("project")
    if not isinstance(assets, list) or not isinstance(project, dict):
        raise ValueError("Catalog needs assets and project")
    rows = []
    for asset in assets:
        if not isinstance(asset, dict) or not asset.get("asset_id") or not asset.get("asset_type"):
            raise ValueError("Every asset needs asset_id and asset_type")
        states = asset.get("state_candidates") or []
        if not isinstance(states, list):
            raise ValueError("state_candidates must be an array")
        row = {
            "project_id": project.get("id"),
            "draft_id": data.get("draft_id"),
            "asset_id": asset["asset_id"],
            "asset_type": asset["asset_type"],
            "name": asset.get("name"),
            "aliases": json.dumps(asset.get("aliases") or [], ensure_ascii=False),
            "scene_ids": json.dumps(asset.get("scene_ids") or [], ensure_ascii=False),
            "source_refs": json.dumps(asset.get("source_refs") or [], ensure_ascii=False),
            "certainty": asset.get("certainty"),
            "state_candidate_ids": json.dumps(
                [state.get("state_id") for state in states if isinstance(state, dict)],
                ensure_ascii=False,
            ),
        }
        rows.append({key: safe_cell(row[key]) for key in FIELDS})
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("asset_catalog", type=Path)
    parser.add_argument("output_csv", type=Path)
    args = parser.parse_args()
    try:
        data = json.loads(args.asset_catalog.read_text(encoding="utf-8"))
        rows = export(data)
        args.output_csv.parent.mkdir(parents=True, exist_ok=True)
        with args.output_csv.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        parser.exit(1, f"ERROR: {exc}\n")
    print(f"Exported {len(rows)} asset rows to {args.output_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
