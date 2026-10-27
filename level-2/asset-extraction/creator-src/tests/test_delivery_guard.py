"""The actual Harness success verifier rejects old-cache and altered deliveries."""
from copy import deepcopy
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from asset_core import finalize, initial_work, write_json
from test_semantic_review import reviewed_fixture, source_fixture

PLUGIN = Path(__file__).resolve().parents[2] / "screenplay-asset-extractor"
sys.path.insert(0, str(PLUGIN / "runtime"))
from harness_core.engine import verify_result


class DeliveryGuard(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.source = self.root / "source.json"
        write_json(self.source, source_fixture())
        self.work = reviewed_fixture(initial_work(self.source))
        write_json(self.root / "work.json", self.work)
        counts = finalize(self.root / "work.json", self.root)
        self.capability = json.loads((PLUGIN / "capabilities.json").read_text())["capabilities"][0]
        self.envelope = {"status": "succeeded", "result": counts, "artifacts": [
            "assets.json", "screenplay-asset-table.xlsx", "asset_findings.json", "asset_findings.md"],
            "questions": [], "error": None}

    def tearDown(self):
        self.tmp.cleanup()

    def test_reviewed_current_version_passes_runtime_success_gate(self):
        self.assertEqual(len(verify_result(self.envelope, self.capability, self.root)), 4)

    def test_legacy_work_with_valid_files_and_counts_is_rejected(self):
        work = deepcopy(self.work)
        del work["semantic_review"]
        write_json(self.root / "work.json", work)
        with self.assertRaisesRegex(ValueError, "postcondition"):
            verify_result(self.envelope, self.capability, self.root)

    def test_export_without_review_cannot_be_substituted(self):
        result = json.loads((self.root / "assets.json").read_text())
        del result["semantic_review"]
        write_json(self.root / "assets.json", result)
        with self.assertRaisesRegex(ValueError, "postcondition"):
            verify_result(self.envelope, self.capability, self.root)

    def test_reported_counts_must_match_actual_artifacts(self):
        self.envelope["result"]["props"] = 99
        with self.assertRaisesRegex(ValueError, "postcondition"):
            verify_result(self.envelope, self.capability, self.root)


if __name__ == "__main__":
    unittest.main()
