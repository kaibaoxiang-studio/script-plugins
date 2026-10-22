from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "scripts" / "screenplay_core.py"
spec = importlib.util.spec_from_file_location("screenplay_core", SOURCE)
assert spec and spec.loader
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)


class ScreenplayCoreTests(unittest.TestCase):
    def test_existing_script_and_bilingual_dialogue(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "a.md"
            source.write_text("第1集\n1-1 大厅 内 夜\n人物：莱拉、KAEL\n"
                              "▲ 莱拉抬头。\n莱拉：你好。\nKAEL: Hello.\n", encoding="utf-8")
            doc = core.prepare(str(source))
            self.assertEqual(1, len(doc["episodes"]))
            self.assertEqual([], core.validate_document(doc))
            block = doc["episodes"][0]["scenes"][0]["blocks"][-1]
            self.assertEqual("en", block["language"])
            block["text"] = "Altered."
            self.assertIn("来源块正文已修改", " ".join(core.validate_document(doc)))
            block["origin"] = "generated"
            self.assertFalse(core.validate_document(doc))
            block["text"] = "Hello."
            block["origin"] = "source"
            paths = core.write_outputs(doc, Path(temp) / "out")["paths"]
            self.assertEqual("标准化剧本.json", Path(paths["screenplay_json"]).name)
            self.assertEqual("标准化剧本.md", Path(paths["screenplay_markdown"]).name)
            self.assertEqual("剧本疑点报告.json", Path(paths["findings_json"]).name)
            self.assertEqual("剧本疑点报告.md", Path(paths["findings_markdown"]).name)
            md = Path(paths["screenplay_markdown"]).read_text(encoding="utf-8")
            self.assertIn("# 第 1 集｜", md)
            self.assertIn("KAEL [lang:en]：Hello.", md)
            self.assertEqual(1, len(json.loads(Path(paths["screenplay_json"]).read_text())["episodes"]))

    def test_docx_red_run_keeps_exact_source_range(self):
        xml = ('<?xml version="1.0"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
               '<w:body><w:p><w:r><w:t>第1集</w:t></w:r></w:p>'
               '<w:p><w:r><w:t>1-1 房间 内 日</w:t></w:r></w:p>'
               '<w:p><w:r><w:t>人物：小明</w:t></w:r></w:p>'
               '<w:p><w:r><w:rPr><w:color w:val="FF0000"/></w:rPr><w:t>▲ 小明打开门。</w:t></w:r></w:p>'
               '</w:body></w:document>').encode()
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "red.docx"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("word/document.xml", xml)
            doc = core.prepare(path)
            action = doc["episodes"][0]["scenes"][0]["blocks"][0]
            self.assertEqual("P4", action["source_refs"][0])
            self.assertEqual("FF0000", action["annotations"][0]["color"])
            self.assertEqual(0, action["annotations"][0]["start"])
            self.assertEqual(len("▲ 小明打开门。"), action["annotations"][0]["end"])
            self.assertEqual("FF0000", doc["source_annotations"]["P4"][0]["color"])

    def test_outline_requires_creative_pass(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "outline.txt"
            path.write_text("第1集｜归来\n【剧情】小明回到家，发现门开着。\n", encoding="utf-8")
            doc = core.prepare(path)
            self.assertEqual("outline", doc["input_kind"])
            self.assertTrue(doc["needs_creative_pass"])
            with self.assertRaises(core.SourceError):
                core.write_outputs(doc, Path(temp) / "out")
            self.assertIn("outline_creation", [n["code"] for n in core.audit(doc)["notices"]])

    def test_outline_generated_blocks_and_review_mode_boundary(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "outline.txt"
            path.write_text("第1集｜归来\n【剧情】小明回家，发现门开着。\n", encoding="utf-8")
            doc = core.prepare(path)
            doc["episodes"] = [{"id": "ep-001", "number": 1, "title": "门开着", "summary": "小明回家，发现门开着。",
                "source_refs": ["L1", "L2"], "title_origin": "generated", "summary_origin": "generated", "scenes": [
                    {"id": "scn-001", "number": "1-1", "source_heading": "", "location": "家门口",
                     "interior_exterior": "外", "time": "日", "characters": ["小明"], "source_refs": ["L2"],
                     "blocks": [{"type": "action", "text": "小明来到家门口，发现门开着。", "origin": "generated",
                                 "source_refs": ["L2"], "annotations": []}]}]}]
            doc["needs_creative_pass"] = False
            doc["coverage"]["status"] = "created"
            doc["extra_findings"] = [{"code": "deep_only", "message": "跨集待核", "source_refs": ["L2"],
                                      "certainty": "inferred", "confidence": "low", "suggestion": "核对"}]
            self.assertFalse(core.validate_document(doc))
            self.assertNotIn("deep_only", [f["code"] for f in core.audit(doc, "light")["findings"]])
            self.assertIn("deep_only", [f["code"] for f in core.audit(doc, "deep")["findings"]])
            outputs = core.write_outputs(doc, Path(temp) / "out")
            self.assertIn("小明来到家门口", Path(outputs["paths"]["screenplay_markdown"]).read_text())

    def test_light_review_evidence_and_legitimate_rename(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "names.txt"
            path.write_text("第1集\n1-1 房间 内 日\n人物：小明、小敏\n小明：你好。\n"
                            "小明：再见。\n小敏：\n▲ 小明说：\n"
                            "第2集\n2-1 门外 外 夜\n人物：小名\n小名：好。\n", encoding="utf-8")
            doc = core.prepare(path)
            codes = [f["code"] for f in core.audit(doc)["findings"]]
            self.assertIn("empty_dialogue", codes)
            self.assertIn("possible_missing_dialogue", codes)
            self.assertIn("possible_name_variant", codes)
            doc["name_changes"] = [{"from": "小明", "to": "小名", "source_refs": ["L8"]}]
            codes = [f["code"] for f in core.audit(doc)["findings"]]
            self.assertNotIn("possible_name_variant", codes)

    def test_empty_source_dialogue_is_omitted_and_reported(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "blank.txt"
            path.write_text("第1集\n1-1 后院 外 夜\n人物：甲、乙\n"
                            "▲ 甲坐在院中。\n乙：我们赢了。\n甲：\n▲ 门被推开。\n", encoding="utf-8")
            doc = core.prepare(path)
            scene = doc["episodes"][0]["scenes"][0]
            self.assertEqual(3, len(scene["blocks"]))
            self.assertTrue(all(block["text"].strip() for block in scene["blocks"]))
            self.assertEqual(["L6"], doc["coverage"]["omitted_source_refs"])
            self.assertEqual([], doc["coverage"]["unassigned_source_refs"])
            findings = [item for item in core.audit(doc)["findings"] if item["code"] == "empty_dialogue"]
            self.assertEqual(["L6"], findings[0]["source_refs"])
            self.assertEqual("high", findings[0]["confidence"])
            outputs = core.write_outputs(doc, Path(temp) / "out")
            markdown = Path(outputs["paths"]["screenplay_markdown"]).read_text(encoding="utf-8")
            self.assertNotIn("甲：\n", markdown)
            self.assertIn("L6", Path(outputs["paths"]["findings_markdown"]).read_text(encoding="utf-8"))
            scene["blocks"].insert(2, {"type": "dialogue", "text": "", "speaker": "甲",
                                        "source_refs": ["L6"], "origin": "source", "extracted_text": ""})
            self.assertIn("1-1 第 3 个正文块为空", core.validate_document(doc))
            doc["notices"] = [item for item in doc["notices"] if item["code"] != "empty_dialogue"]
            doc["coverage"]["omitted_source_refs"] = []
            repaired = core.write_outputs(doc, Path(temp) / "legacy-out")
            self.assertEqual(3, len(scene["blocks"]))
            self.assertEqual(["L6"], doc["coverage"]["omitted_source_refs"])
            repaired_json = json.loads(Path(repaired["paths"]["screenplay_json"]).read_text(encoding="utf-8"))
            self.assertTrue(all(block["text"].strip() for block in repaired_json["episodes"][0]["scenes"][0]["blocks"]))
            repaired_report = json.loads(Path(repaired["paths"]["findings_json"]).read_text(encoding="utf-8"))
            self.assertEqual(1, sum(item["code"] == "empty_dialogue" for item in repaired_report["findings"]))

    def test_multiple_versions_selects_final_script(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "multiple.txt"
            path.write_text("三、分集细纲\n第1集\n【剧情】旧稿\n"
                            "四、双语剧本\n第1集\n1-1 宫殿 内 夜\n人物：甲\n甲：Old.\n"
                            "五、剧本\n第1集\n1-1 宫殿 内 夜\n人物：甲\n甲：新稿。\n", encoding="utf-8")
            doc = core.prepare(path)
            self.assertEqual("剧本", doc["selected_section"]["label"])
            self.assertIn("新稿", core.render_markdown(doc))
            self.assertNotIn("Old.", core.render_markdown(doc))
            self.assertEqual(2, len(doc["reference_material"]))
            self.assertIn("Old.", " ".join(x["text"] for x in doc["support_material"]))

    def test_explicit_final_section_and_equal_version_ambiguity(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "versions.txt"
            path.write_text("一、剧本\n第1集\n1-1 屋内 内 日\n人物：甲\n甲：旧。\n"
                            "二、最终剧本\n第1集\n1-1 屋内 内 日\n人物：甲\n甲：新。\n", encoding="utf-8")
            doc = core.prepare(path)
            self.assertEqual("最终剧本", doc["selected_section"]["label"])
            self.assertIn("新。", core.render_markdown(doc))
            path.write_text("一、剧本\n第1集\n1-1 屋内 内 日\n人物：甲\n甲：甲。\n"
                            "二、剧本\n第1集\n1-1 屋内 内 日\n人物：乙\n乙：乙。\n", encoding="utf-8")
            with self.assertRaises(core.SourceError):
                core.prepare(path)

    def test_action_dialogue_mismatch_without_false_missing_dialogue(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "cue.txt"
            path.write_text("第1集\n1-1 屋内 内 日\n人物：甲、乙\n"
                            "▲ 甲说：\n乙：是。\n", encoding="utf-8")
            codes = [item["code"] for item in core.audit(core.prepare(path))["findings"]]
            self.assertIn("action_dialogue_mismatch", codes)
            self.assertNotIn("possible_missing_dialogue", codes)

    def test_flashback_can_cross_scene_boundary(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "flashback.txt"
            path.write_text("第1集\n1-1 客厅 内 日\n人物：甲\n【闪回】\n▲ 甲回忆旧事。\n"
                            "1-2 院子 外 日\n人物：甲\n▲ 甲站在院里。\n【闪出】\n", encoding="utf-8")
            doc = core.prepare(path)
            self.assertFalse(core.validate_document(doc))
            self.assertNotIn("flashback_auto_closed", [n["code"] for n in doc["notices"]])

    def test_private_user_samples_when_available(self):
        folder = os.environ.get("SCREENPLAY_FIXTURE_DIR")
        if not folder:
            self.skipTest("set SCREENPLAY_FIXTURE_DIR to inspect user-provided samples")
        samples = [x for x in Path(folder).rglob("*") if x.suffix.lower() in {".txt", ".docx"}
                   and "原本" in x.name]
        observed = {}
        for path in samples:
            doc = core.prepare(path)
            observed[len(doc["episodes"])] = (sum(len(e["scenes"]) for e in doc["episodes"]), doc)
            self.assertFalse(doc["coverage"]["unassigned_source_refs"])
            self.assertFalse(core.validate_document(doc))
        self.assertEqual({25, 50, 53}, set(observed))
        self.assertEqual(37, observed[25][0])
        self.assertEqual(71, observed[53][0])
        self.assertGreaterEqual(observed[50][0], 90)
        self.assertEqual("剧本", observed[25][1]["selected_section"]["label"])
        annotations = [mark for ep in observed[53][1]["episodes"] for sc in ep["scenes"]
                       for block in sc["blocks"] for mark in block.get("annotations", [])]
        self.assertGreater(len(annotations), 100)


if __name__ == "__main__":
    unittest.main()
