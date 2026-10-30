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

## 运行环境门禁（不可绕过）

在执行任何解析、提取、导出或验收命令前，必须先确认插件运行时：

```bash
python3 "$S/bootstrap.py" --install
python3 "$S/launch.py" "$S/env_diagnostics.py"
```

所有诊断必须同时满足：Python 3.12+，并能导入 `jsonschema`、`yaml`、`docx`、`openpyxl`、`lxml`。如果诊断失败，必须停止并报告缺少的解释器或依赖，不能继续生成部分资产表。

所有插件脚本必须通过 `$S/launch.py` 启动，例如：

```bash
python3 "$S/launch.py" "$S/workflow.py" prepare "<剧本.docx|剧本.md>" "<artifact_dir>"
```

禁止直接调用系统 `python`、`python3` 或当前工作目录中的同名脚本运行插件流程；禁止依赖 `PATH` 中的 Python 别名、用户目录中的同名 Skill 或其他项目的虚拟环境。`$S` 必须解析为本插件包内 `scripts/` 的绝对路径。
