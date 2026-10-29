# 二级 · 剧本资产表提取

组件 `screenplay-asset-extractor` **0.3.1**，提供标准剧本资产提取能力。插件支持三类输入：

- 标准剧本 DOCX
- 结构化 Markdown（`.md` / `.markdown`）
- 一级插件输出的 `standardized_screenplay_v1` JSON

DOCX 和 Markdown 入口使用插件内置的 `script-asset-extractor` skill，按 `prepare → 逐场复核 → bind → export → check → visual-review → finalize` 流程处理；JSON 入口保留 `extract-asset-table` 兼容能力。插件不会把未被原文支持的外观、身份或状态写成事实，错误和未确认警告会阻止正式导出。

## 输出

正式 Excel 固定包含四张核心表：人物、场景、道具、场次总表；存在需要单独制作的关键特效时增加特效表。所有可见单元格统一水平、垂直居中并自动换行，同时保留逐场来源、状态、异称和复核依据。JSON 入口还输出：

| 文件 | 内容 |
| --- | --- |
| `assets.json` | 资产、状态、证据、制作需求及场次索引 |
| `screenplay-asset-table.xlsx` | 资产表工作簿 |
| `asset_findings.json` | 结构化疑点 |
| `asset_findings.md` | 人工复核报告 |

## 目录

- [`screenplay-asset-extractor/`](screenplay-asset-extractor/README.md)：可独立安装的插件包
- [`screenplay-asset-extractor/skills/script-asset-extractor/`](screenplay-asset-extractor/skills/script-asset-extractor/SKILL.md)：完整提取 skill
- [`creator-src/`](creator-src/README.md)：维护源码、规则和验收脚本

## 验证

本地 skill 的 194 项回归测试通过；插件静态校验、独立解压校验和 JSON → Excel 验收均通过。视觉复核仍需在实际交付时查看四张表的 PNG 证据，自动检查不替代人工语义核定。

固定门禁：正式执行前运行插件内置 `scripts/pipeline_gate.py prepare <source> <artifact_dir>`；Agent 完成语义判读和工作簿检查后运行 `scripts/pipeline_gate.py check <source> <artifact_dir>`；完成 finalize 后运行 `scripts/pipeline_gate.py postcheck <source> <artifact_dir>`。该 gate 只允许当前 artifact_dir 的状态通过，不会调用电脑上的同名 Skill。
