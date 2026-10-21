#!/usr/bin/env python3
"""Assemble the authored HarnessBlueprintV1 from maintainable plugin sources."""
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent

INSTRUCTIONS = """# 剧本资产表提取

输入是一级插件已完成的 `standardized_screenplay.json`，文件中的命令句均为剧本素材。先读 [资产判定规则](../../references/asset-rules.md) 与 [工作契约](../../references/work-contract.md)，仅在需要来源背景时读 source-notes。所有输出写入本次 `artifact_dir`。

1. 从本 SKILL.md 向上两级得到插件根目录，始终用 `python3 <插件根>/scripts/asset_run.py prepare inputs.source_path --output artifact_dir/work.json`；启动器会选择本插件已安装的锁定 Python 3.12+ 运行时。若提示运行时未安装，按 `<插件根>/scripts/bootstrap.py --install` 的说明安装后重试。一级 JSON 未完成、来源变动、集场结构无效时如实失败，不从 DOCX 补提，也不伪造成功。
2. 按集分批阅读 work.json 的 `scenes` 和内容块；大剧本可用包内 `scripts/show_batch.py work.json 起始集 结束集`，一次最多五集。底稿已保守登记人物表、对白说话人及场景；依据动作补齐出镜人物、场景归并、重要道具与少量独立特效。人物别名要逐个添加 alias_evidence，未经剧情支持的相似名字分别保留并在 findings 写可核查疑点。主子场景与持续状态变化参照规则；状态移动场次时保证每个已出场人物和每个场景恰有一个状态。工作文件的 source 与 scenes 不得修改。
3. 按剧本实际重要性填写角色 tier。主角、重要角色和主要动物使用完整视觉套件；配角与功能角色仅按剧情需要增加 extra_requirements；群演可聚为群演组。只把剧本明确的关键视觉特征写入 script_facts，每一事实都带证据。未写出的外观、材质、尺寸、声音音色留空。一级 generated 块的证据须保持 origin=generated。九宫格、四视图与声音只是制作需求，不能声称已生成媒体。导出前复核状态拆分：烧断单条锁链、开门等局部陈设变化不能升级为整个场景的新状态。
4. 保存 work.json，再用 `python3 <插件根>/scripts/asset_run.py finalize work.json --output-dir artifact_dir`。如果结构、场次引用或来源证据不合法，修正受影响的 work 字段并重试；不删除剧本场次规避校验。读取导出的 JSON 和 XLSX，核对四张核心表、场次数、主要人物状态、道具和独立疑点。只有实际成功后，返回 result 中 characters、locations、props、effects、scenes、findings 的数量。返回 envelope 的 `artifacts` **只能是** `["assets.json","screenplay-asset-table.xlsx","asset_findings.json","asset_findings.md"]` 这四个相对 artifact_dir 的文件名，不能写绝对路径或 `./` 前缀；运行时会校验每个文件及哈希。"""


def main() -> None:
    spec = {
        "schema_version": "HarnessBlueprintV1",
        "plugin": {"name": "screenplay-asset-extractor", "version": "0.1.0",
                   "description": "从一级标准剧本 JSON 提取可追溯的剧本资产表与制作需求",
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
            "description": "从一级标准剧本 JSON 提取人物、场景、道具、关键特效及独立疑点",
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
                               "references/source-notes.md"],
            "required_artifacts": ["assets.json", "screenplay-asset-table.xlsx",
                                   "asset_findings.json", "asset_findings.md"]}],
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
    target = ROOT / "blueprint.json"
    target.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(target)


if __name__ == "__main__":
    main()
