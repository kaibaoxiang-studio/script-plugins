---
name: screenplay-asset-extractor
description: "从标准剧本 DOCX 或一级标准 JSON 提取可追溯的剧本资产表"
---

# screenplay-asset-extractor

将一级标准剧本转换为证据可追溯的资产 JSON 和 Excel，独立报告疑点

按实际输入选择下列入口，读取对应 SKILL.md。DOCX 入口执行 skill 自带脚本；一级 JSON 入口使用原有 Harness。使用用户指定的工作目录，报告实际产物与校验结果。

- `$script-asset-extractor`（v0.1.1）：标准 DOCX 剧本，人物逐场造型及道具实物身份校验，统一排序与 Excel 模板并验收保存结果，交付资产 JSON 和四表 Excel。读取 [SKILL.md](../script-asset-extractor/SKILL.md)。

- `$extract-asset-table`: 从一级标准剧本 JSON 提取人物、场景、道具、关键特效及独立疑点

See [runtime instructions](../../RUNTIME.md).
