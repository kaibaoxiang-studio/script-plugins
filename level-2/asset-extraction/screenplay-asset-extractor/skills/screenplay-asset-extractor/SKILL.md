---
name: screenplay-asset-extractor
metadata:
  version: "0.3.2"
description: 从标准剧本 DOCX、结构化 Markdown 或 standardized_screenplay_v1 JSON 提取经逐场审核并通过交付验收的剧本资产表。
---
# 剧本资产表提取 · 0.3.2

这是本插件唯一的总入口。必须根据输入类型选择本插件内的流程，不能调用电脑上同名的个人 Skill，也不能直接手写最终 Excel。

- DOCX / Markdown：读取 [extract-asset-table](../extract-asset-table/SKILL.md)，并在 `artifact_dir` 内执行包内 `scripts/workflow.py` 的完整流程：`prepare → 逐场审核 → bind → export → check → visual-review → finalize`。
- standardized_screenplay_v1 JSON：读取同目录的 [extract-asset-table](../extract-asset-table/SKILL.md)，使用其兼容 JSON 流程。

所有中间文件和正式产物都写入任务提供的 `artifact_dir`。只有 `progress.json.stage=complete`、`acceptance.json` 存在、工作簿保存后验收通过、四张表视觉证据已登记，并通过插件 postcheck，才允许返回 `succeeded`。否则返回 `failed` 或 `blocked`，不能用部分 Excel 冒充完成。

不要根据个人目录中的同名 Skill 替换本插件版本。报告必须列出真实执行的输入格式、工作目录、验收状态和产物路径。
