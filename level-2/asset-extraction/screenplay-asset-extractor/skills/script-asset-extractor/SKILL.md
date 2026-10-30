---
name: script-asset-extractor
metadata:
  version: "0.3.2"
description: 从标准化剧本 docx 提取人物、场景、道具及外观状态，通过逐场审查、原文候选复核和保存后验收交付 Excel 资产表。用户提到剧本资产表、拆资产、提取人物场景道具或制作资产清单时使用。
---
# 剧本资产表提取

插件版本 `0.3.2`；业务兼容规则沿用历史 v0.1.1，运行时只使用插件内置脚本。输入标准 DOCX 或结构化 Markdown，正式交付 `assets.json` 与 `<剧名>-资产表.xlsx`，保持人物、场景、道具、场次总表四张表及原展示模板。正式模板四张表所有单元格统一水平、垂直居中并自动换行。

`$S` 指本 SKILL.md 所在目录下的 `scripts/`，不能使用当前工作目录代替。依赖 `python-docx==1.1.2`、`openpyxl==3.1.5`；PNG 证据校验仅使用标准库；所有脚本使用同一 Python 解释器。


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

## 启动与恢复

先读 [执行台账与完成标准](../../references/execution_contract.md)。开始资产判断前读 [资产结构](../../references/asset_schema.md) 与 [提取和纠错规则](../../references/asset_judgment.md)。人物还须读 [状态规则](../../references/character_states.md)，道具还须读 [实物身份规则](../../references/prop_identity.md)。

首次运行，选择剧本目录下新的 `<剧名>_资产提取/`：

```bash
python3 "$S/launch.py" "$S/workflow.py" prepare "<剧本.docx|剧本.md>" "<工作目录>"
```

Markdown 输入可先运行：

```bash
python3 "$S/launch.py" "$S/workflow.py" diagnose-markdown "<剧本.md>"
```

该命令只生成解析诊断，不建立资产判断。

程序检查零集/零场、超过 5% 未识别段落、连续至少 10 行无法解析及表格正文；不达标时停止，不以失败解析继续。`prepare` 只建立原文结构、空白逐场台账与待复核线索，不进行语义提取，也不代表已读。Markdown 会去除标题标记、引用标记和分隔线，但保留原始文件行号；来源格式写入 `scenes.json.source.format`。

恢复已有工作时先运行：

```bash
python3 "$S/launch.py" "$S/workflow.py" status "<工作目录>"
```

依据实际缺项继续；`progress.json` 是提示，不是完成证明。原始 DOCX 变化后用新目录重新解析，回查迁移，不能只更新哈希。

## 分工和批次

已获多agent授权时，先读 [分工与独立审核](../../references/agent_workflow.md)，用 `workflow.py team-init`、`fragment-template`、`submit`、`check-batch`、`merge` 管理三类独立片段。人物和道具各有全剧唯一责任人；主agent合并后交独立审核，责任方返修、审核者复查，最后统一绑定。失败执行最多3次、错峰重试，不用旧片段冒充新任务完成。

程序从已审appearances/mentions派生场次、类别和行关联，不生成身份、出镜或排除结论。`candidate-groups`减少重复阅读但保留全部原始线索。`diagnose`输出完整结构化错误及受影响范围，其他批次的待办与当前错误分开。

## 通读、提取与记录

每批约 5 集，阅读全部人物行与动作/对白上下文，逐场填写 `review.json`。每个原文行记录实际结论，人物/场景/道具各类记录本场取舍；没有某类资产也需本场理由。不能先形成清单，再批量反写“已完成”。

```bash
python3 "$S/launch.py" "$S/show_episodes.py" "<工作目录>/scenes.json" 1 5
python3 "$S/launch.py" "$S/show_character.py" "<工作目录>/scenes.json" "<人物名>" "<别名>"
python3 "$S/launch.py" "$S/show_character.py" "<工作目录>/scenes.json" "<人物名>" --changes
python3 "$S/launch.py" "$S/show_prop.py" "<工作目录>/scenes.json" "<工作目录>/assets.json" --related
```

建立三类数组的 `assets.json`。每个人物读取全剧全部候选场次；有台词不归群演，名称命中、对白提及、VO/OS 不自动证明出镜。人物先写逐场 `appearances`；状态场次和展示引文只能从记录派生。同场变化按阶段，分身按有依据的实体；故事时间边界重新判读，未知外观写未说明。

道具按实物身份建立 `mentions`，交接不新建物件；泛称/代词不得成为全局别名。明确拿取、递交、使用、特写任一线索都可登记，不因未知所有者或没有破损而漏提。固定陈设归场景，服装归人物。

逐项填写台账中的独立原文候选：已收录须关联该位置的实际资产与记录；排除须有覆盖线索的原文证据及具体原因；不确定项保留待确认，不能正式交付。扫描不覆盖所有表达，不能用候选数量代替通读。人物多状态、初始重置及继承记录还要完成 `character_reviews` 全阶段复核。

## 同步、校验、生成

```bash
python3 "$S/launch.py" "$S/build_xlsx.py" "<工作目录>/scenes.json" "<工作目录>/assets.json" --sync-character-scenes
python3 "$S/launch.py" "$S/build_xlsx.py" "<工作目录>/scenes.json" "<工作目录>/assets.json" --sync-prop-scenes
python3 "$S/launch.py" "$S/workflow.py" bind "<工作目录>"
python3 "$S/launch.py" "$S/workflow.py" export "<工作目录>"
python3 "$S/launch.py" "$S/workflow.py" check "<工作目录>"
python3 "$S/launch.py" "$S/workflow.py" visual-review "<工作目录>"
python3 "$S/launch.py" "$S/workflow.py" preflight "<工作目录>"
python3 "$S/launch.py" "$S/workflow.py" warning-groups "<工作目录>"
python3 "$S/launch.py" "$S/workflow.py" warning-draft "<工作目录>"
python3 "$S/launch.py" "$S/workflow.py" compress-advice "<工作目录>"
python3 "$S/launch.py" "$S/workflow.py" impact "<工作目录>"
python3 "$S/launch.py" "$S/workflow.py" semantic-audit "<工作目录>"
python3 "$S/launch.py" "$S/workflow.py" visual-regression "<工作目录>"
python3 "$S/launch.py" "$S/workflow.py" compare-sources "<Markdown或DOCX>" "<Markdown或DOCX>"
```

`check` 是统一的非视觉验收入口，会汇总数据、独立审核、工作簿和视觉证据门槛；返回非零状态时不能 finalize。
`visual-review` 自动为四张表生成独立 PNG 预览并登记文件哈希；它不会代替人工看图，也不会自动写入视觉结论。生成后必须实际查看图片、填写每张表的 `conclusion`，再运行 `check` 和 `finalize`。
`preflight` 在交付前检查 Excel 行高风险、场次编号重复和审核台账漏场。`finalize` 通过后会在工作目录生成 `交付报告.md`。
`warning-groups` 按广播/AI 音、群体角色、缺少状态等规则整理当前警告，供人工逐组复核；它只分组，不自动确认，也不改变 `warning_approvals.json`。
`warning-draft` 生成带规则分组的确认草稿；必须人工填写每条 `reason` 和 `confirmed_by` 并复核消息后，另存为正式 `warning_approvals.json`。空白草稿不能通过交付验收。
`compare-sources` 比较 Markdown 与 DOCX 的集次、场次编号、场景名、内外和时间；`compress-advice` 报告接近 Excel 行高上限的字段并给出保序压缩建议；`impact` 根据当前快照提示资产修改影响的复核表范围。
`semantic-audit` 检查状态重复和跨场次引用；`visual-regression` 检查自动预览是否覆盖四表首/中/尾页面并验证 PNG 结构。两者都只报告问题，不修改资产。

`bind` 在覆盖和证据通过后绑定当前快照，不生成判读或批准结论。改动资产/原文后旧绑定失效；用 diagnose 定位受影响范围，复核再绑定。分工模式的独立审核按范围过期，无关范围可保留；来源或版本变化全部失效。重复bind/export仅在来源、展示计划和工作簿验收均一致时保留视觉记录；变更后重新查看。导出自动重开已保存 Excel，按当前数据验收通过后才保留复核副本；没有通过时不会覆盖已有文件。

有合理但无法消除的弱警告，先读 [警告确认](../../references/warning_approvals.md)，取得用户对具体警告的确认后保存 `warning_approvals.json`。不能自行代用户确认。任何错误或未确认警告阻止交付；已确认警告保留真实数量和内容。workflow 自动读取该确认文件；如单独执行 --check 或 check_workbook.py，须同时传 --warning-approvals "<工作目录>/warning_approvals.json"。

## 视觉复核与正式交付

先读 [Excel 模板与验收](../../references/excel_output.md)。实际查看 `asset-table.review.xlsx` 四张表，检查分组、合并、长文本截断、阅读密度与实际筛选；将已查看的本地 PNG 预览图片及哈希和具体结论填入 `review.json.delivery_review`。自动检查不替代实际看图和语义判断，不能用占位图伪造证据。

```bash
python3 "$S/launch.py" "$S/workflow.py" finalize "<工作目录>" --output "<剧本目录>/<剧名>-资产表.xlsx"
```

只有此命令通过且 `status` 返回 `complete` 才能声明完成。它再次回查原始 DOCX、审查台账、确认警告和已保存工作簿，检查视觉证据及哈希后发布 Excel，生成工作目录内的 `acceptance.json`。修改已交付文件后验收失效。其他 Excel 后端必须消费同一展示计划并通过同一交付验收，见执行契约。

简报分别写资产与状态数量、数据校验、Excel 验收、实际语义/视觉复核结果，列出待确认问题以及错误、未确认和已确认警告的真实数量。不把有记录说成语义必然正确。正式交付仅两个文件，台账、预览、日志、备份与验收报告留在工作目录。

## 不可绕过

禁止修改原始人物行、删场次、伪造实体/时间线或变更规则和脚本以通过验收；禁止从旧状态列表反造出场或道具记录。旧项目必须回到原文补台账。不能因 token、阅读批次或中断跳过后续场次，未完成就报告具体剩余项。并行仅在获得授权后进行，已有授权不重复询问；分工及合并约束见 agent_workflow.md。单agent流程兼容；不能把自查伪称独立审核。


## 插件入口

本插件保留一级 JSON 兼容入口；对 DOCX/Markdown 使用本目录 `scripts/workflow.py` 的 `prepare → 逐场复核 → bind → export → check → visual-review → finalize` 流程。插件包内的 `scripts/` 与 `references/` 是运行时副本，不依赖用户机器上的同名 skill。
