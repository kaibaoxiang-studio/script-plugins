from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


scene_log = load("scene_log", "capabilities/02-scene-log/scripts/export_scene_log.py")
asset_table = load("asset_table", "capabilities/03-asset-table/scripts/export_asset_table.py")
beat_table = load("beat_table", "capabilities/04-beat-table/scripts/export_beat_table.py")


class ExportContractTests(unittest.TestCase):
    def test_scene_export_keeps_evidence_and_does_not_infer_missing_fields(self):
        data = {
            "source_manifest": {"source_id": "src-1", "draft_id": "d1"},
            "scenes": [{
                "id": "scn-001", "heading": "内景 房间 日", "scene_number": "1",
                "source_refs": ["L1-L4"],
                "source_range": {"start": 1, "end": 4, "unit": "line"},
                "text": "内景 房间 日\n人物：小明",
            }],
        }
        rows = scene_log.export(data)
        self.assertEqual(1, len(rows))
        self.assertEqual("scn-001", rows[0]["scene_id"])
        self.assertEqual(["L1-L4"], json.loads(rows[0]["source_refs"]))
        self.assertEqual("", rows[0]["location"])

    def test_asset_export_preserves_catalog_identity_and_states(self):
        data = {
            "schema_version": "AssetCatalogV1",
            "project": {"id": "project-1"},
            "draft_id": "d1",
            "assets": [{
                "asset_id": "chr-001", "asset_type": "character_master",
                "name": "小明", "aliases": ["明明"],
                "scene_ids": ["scn-001"], "source_refs": ["L2"],
                "certainty": "explicit",
                "state_candidates": [{"state_id": "canonical"}],
            }],
        }
        row = asset_table.export(data)[0]
        self.assertEqual("chr-001", row["asset_id"])
        self.assertEqual(["scn-001"], json.loads(row["scene_ids"]))
        self.assertEqual(["canonical"], json.loads(row["state_candidate_ids"]))

    def test_beat_export_rejects_unfinished_or_broken_links(self):
        data = {
            "project": {"id": "project-1"},
            "source_manifest": {"draft_id": "d1"},
            "coverage": {"status": "partial"},
            "scenes": [{"id": "scn-001"}],
            "beats": [{
                "id": "bea-001", "scene_id": "scn-001",
                "source_refs": ["L2-L3"], "change": "得知真相",
                "entry_state": {}, "exit_state": {},
            }],
        }
        with self.assertRaises(ValueError):
            beat_table.export(data)
        self.assertEqual("partial", beat_table.export(data, allow_partial=True)[0]["coverage_status"])
        data["coverage"]["status"] = "completed"
        data["beats"][0]["scene_id"] = "scn-999"
        with self.assertRaises(ValueError):
            beat_table.export(data)

    def test_csv_cells_cannot_start_spreadsheet_formulas(self):
        for module in (scene_log, asset_table, beat_table):
            self.assertEqual("'=1+1", module.safe_cell("=1+1"))


if __name__ == "__main__":
    unittest.main()
