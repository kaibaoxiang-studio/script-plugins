#!/usr/bin/env python3
"""Assemble the authored HarnessBlueprintV1 from maintainable plugin sources."""
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent

INSTRUCTIONS = """# 剧本资产表提取

这是插件唯一的资产提取能力。输入支持标准剧本 DOCX、结构化 Markdown 和一级 standardized_screenplay_v1 JSON。严格使用本插件内置的 `skills/extract-asset-table/SKILL.md` 与 `scripts/`，不得调用个人目录中的同名 Skill。

1. 所有输出写入本次 `artifact_dir`。DOCX/Markdown 必须运行 `python3 <插件根>/scripts/workflow.py prepare <source_path> <artifact_dir>`，随后逐场填写审核台账。
2. 继续运行 `bind → export → check → visual-review`，实际查看四表预览并填写视觉结论；最后运行 `python3 <插件根>/scripts/workflow.py finalize <artifact_dir> --output <artifact_dir>/screenplay-asset-table.xlsx`。
3. standardized_screenplay_v1 JSON 可使用兼容 JSON 流程，但仍须完成逐场审核和保存后验收。
4. 只有 `progress.json.stage=complete`、`acceptance.json` 存在、工作簿通过保存后验收、视觉证据已登记且 postcheck 通过时，才返回 succeeded；否则返回 failed 或 blocked。
5. 返回真实的 characters、locations、props、effects、scenes、findings 计数；`artifacts` 至少包含 `assets.json` 和 `screenplay-asset-table.xlsx`，只能使用 artifact_dir 内相对路径。
"""


def main() -> None:
    spec = {
        "schema_version": "HarnessBlueprintV1",
        "plugin": {"name": "screenplay-asset-extractor", "version": "0.3.2",
                   "description": "从标准剧本 DOCX、结构化 Markdown 或一级标准 JSON 提取经逐场审核并通过交付验收的剧本资产表",
                   "author": {"name": "开宝箱工作室"}},
        "goal": "将一级标准剧本转换为证据可追溯的资产 JSON 和 Excel，独立报告疑点",
        "acceptance_criteria": [
            "接受完整的 standardized_screenplay_v1，读取集场内容块、来源位置及生成标记",
            "保留人物、场景、道具、场次总表四张核心表；有关键特效时才增加特效表",
            "别名、状态与显著事实有剧本证据；未给出的设计细节不虚构",
            "人物出场与状态双向校验、场景状态和场次引用一致；硬错误阻止导出",
            "从独立插件 ZIP 实际调用成功，无其他业务插件运行依赖"],
        "open_questions": [],
        "capabilities": [{
            "id": "extract-asset-table", "skill_name": "extract-asset-table",
            "description": "强制使用插件内置 workflow.py，从 DOCX/Markdown/standardized_screenplay_v1 提取并完成逐场、工作簿、视觉和交付验收",
            "instructions": INSTRUCTIONS,
            "input_schema": {"type": "object", "properties": {
                "source_path": {"type": "string", "minLength": 1}},
                "required": ["source_path"], "additionalProperties": False},
            "output_schema": {"type": "object", "properties": {
                key: {"type": "integer", "minimum": 0}
                for key in ("characters", "locations", "props", "effects", "scenes", "findings")},
                "required": ["characters", "locations", "props", "effects", "scenes", "findings"],
                "additionalProperties": False},
            "execution": {"kind": "agent", "access": "workspace-write", "network": False},
            "knowledge_refs": ["references/asset-rules.md", "references/work-contract.md",
                               "references/source-notes.md", "references/semantic-review.md"],
            "required_artifacts": ["assets.json", "screenplay-asset-table.xlsx"]}],
        "files": {str(path.relative_to(ROOT)): path.read_text(encoding="utf-8")
                  for folder in (ROOT / "scripts", ROOT / "references")
                  for path in folder.rglob("*") if path.is_file() and path.suffix in {".py", ".md"}},
        "workflows": [],
        "sources": [
            {"origin": "kaibaoxiang-studio/script-plugins:script-asset-extractor",
             "revision": "8ba6de3561f85c5a0af6cc46ca68c23fba8b5917",
             "adaptation": "依据分批提取、状态追踪、双向校验和四表结构重新实现 JSON 输入及证据机制；旧代码未进入插件"},
            {"origin": "screenplay-standardizer plugin",
             "revision": "standardized_screenplay_v1",
             "adaptation": "采用其标准 JSON 的集场块、source_refs、origin 与 coverage 契约"},
            {"origin": "Skill Orchestrator 0.8.0",
             "revision": "0.8.0",
             "adaptation": "参考证据边界与资产制作岗位视角，不复制运行时或私有岗位内容"}]}
    spec["files"]["README.md"] = (ROOT / "PLUGIN-README.md").read_text(encoding="utf-8")
    spec["files"]["VALIDATION.md"] = (ROOT / "VALIDATION.md").read_text(encoding="utf-8")
    # DOCX Skill is authored in the installed snapshot; preserve all of its files
    # and the input router when rebuilding the JSON Harness capability.
    snapshot = ROOT.parent / "screenplay-asset-extractor"
    for folder in (snapshot / "skills/extract-asset-table", snapshot / "skills/script-asset-extractor", snapshot / "skills/screenplay-asset-extractor"):
        for path in folder.rglob("*"):
            if path.is_file() and path.suffix in {".py", ".md", ".yaml"} and "__pycache__" not in path.parts:
                spec["files"][path.relative_to(snapshot).as_posix()] = path.read_text(encoding="utf-8")
    target = ROOT / "blueprint.json"
    target.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(target)


if __name__ == "__main__":
    main()
