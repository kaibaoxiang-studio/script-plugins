---
name: screenplay-asset-extractor
description: "从标准剧本 DOCX、结构化 Markdown 或一级标准 JSON 提取经逐场审核并通过交付验收的剧本资产表"
---

# screenplay-asset-extractor

将一级标准剧本转换为证据可追溯的资产 JSON 和 Excel，独立报告疑点

Match the request to a capability below. Read its SKILL.md and relevant references. Ask only for missing consequential inputs; preserve established decisions. Run Python-backed capabilities through the bundled harness. Use the workspace selected by the user and report actual artifacts and remaining failures.

- `$extract-asset-table`: 强制使用插件内置 workflow.py，从 DOCX/Markdown/standardized_screenplay_v1 提取并完成逐场、工作簿、视觉和交付验收
- `$extract-asset-table`: 由插件内置 Python 固定编排执行 prepare 和 postcheck，禁止跳过阶段

See [runtime instructions](../../RUNTIME.md).
