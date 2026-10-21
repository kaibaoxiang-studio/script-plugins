---
name: ai-continuity-sheet
description: 从一级标准化剧本 JSON 提取整剧场记表，按场分拍并输出可追溯 JSON、13 列 Excel 与独立审查报告。可独立使用，也作为「场记表提取」插件主能力。
---

# AI Continuity Sheet｜场记表提取

本 Skill 沿用原有 13 列场记表和七个辅助 Skill，以一级 `standardized_screenplay_v1` JSON 为唯一剧本输入。每行仍用 `EPxx + SCxx + Pxx` 标识；**一个 P 只对应一个叙事拍**。`SC` 跨集递增，`P` 每场从 P01 重新开始。一次调用处理整剧；需要时可只重跑指定集。

## 输入与交付

- 必填：一级插件产出的 `standardized_screenplay.json` 路径。若没有分集、场景、正文块或来源位置，给出上游补全提示，不从空细纲直接杜撰场记表。
- 可选：指定集数、模型、画幅、灯光偏好。无参数时保持平台中立，不追问 Seedance 或制作规格。
- 交付：`scene_log.json`、`scene_log.xlsx`、`scene_log_report.json`、`scene_log_report.md`。报告与表格分离；疑点不自动改进剧本。
- JSON 记录每拍的正文单元、来源 refs、原文对白、生成来源、待审建议和时长依据。Excel 为一个工作簿，每集一页；各页顶部合并单元格放该集一级标准化剧本正文。

## 原有 13 列与岗位

| 集数 | 场次 | 片段 | 出场人物 | 场景 | 道具 | 摄影 | 灯光/色卡 | 台词 | 时长 | 微表情情绪指导 | 动作表演指导 | 剧情大纲 |
|------|------|------|----------|------|------|------|-----------|------|------|----------------|--------------|----------|

本 Skill 维护集场/P 编号、来源、出场人物、场景和道具。原有七个辅助 Skill 继续负责各自的列：`cinematography-advisor`、`lighting-colorist`、`dialogue-formatter`、`shot-duration-calculator`、`micro-expression-director`、`action-performance-director`、`scene-synopsis`。按当前拍的需要使用相应视角，不要求每拍都臆造复杂摄影、灯光或表演。

## 分阶段执行

1. **校验并备料**：读取一级 JSON，按集场取 `blocks`，把动作句拆为保持原文的单元；对白整体保留。每个单元有原块索引、来源 refs、类型、说话人、OS/VO、语言和 `origin`。
2. **逐场分拍**：按人物目标、行动、反应或信息变化划分叙事拍。可把相邻单元合为一拍；不得跳过、重复或调换单元。标点和镜头变化不能单独迫使切拍。输出每拍连续的 `unit_ids` 与分拍理由。
3. **逐场填写**：沿用七个辅助 Skill 的列职责，先确定本拍涉及的人物、道具和原文台词，再给出必要的摄影、灯光、表演、时长及剧情建议。建议须说明所依据的单元或场景条件；无法判断时写 `—` 并列出不确定项。不得创造人物、道具、剧情事件或更改对白。时长是初步估计，不设平台时长硬上限。
4. **整剧复核**：检查跨场、跨集的人物与道具连续性、疑似漏拍及名称变化。仅输出带来源位置的疑点；有剧情解释的合法变化不报错。模型建议、生成剧本内容与不确定项都留待人工审查。
5. **确定性发布**：脚本校验所有正文单元恰好覆盖一次、建议与分拍逐条对应，并从同一 JSON 写 Excel 和报告。长篇剧本正文分成连续的合并行，避免 Excel 单元格截断。

## 台词和建议边界

- 台词列由原 `dialogue-formatter` 的原文保留原则收紧：每段对白全文与语言顺序不变，OS/VO 保留标记；长对白不得用省略号截断。JSON 中逐块保存原文，Excel 单元格以换行并列。
- 摄影、灯光、微表情、动作表演、剧情概括和时长均标记为 `pending` 待审建议；不能作为原剧本事实。
- 有 `origin=generated` 的一级正文可以继续处理，但每个受影响的 P 都保留生成标记并进入报告。

## 运行

独立插件调用 `extract-scene-log`。需要可恢复的整剧命令时，运行包内 `scripts/run_scene_log.py --source <一级JSON> --workspace <运行目录> --output <交付目录>`；`--episodes 2,3` 仅输出指定集，`--resume <run_id>` 在输入与插件版本未变时续跑。运行使用包内 Harness，不依赖 `jimeng-storyboard-v3`、Skill Orchestrator 或开发机已安装的其他业务 Skill。

原 `scripts/convert_continuity_sheet.py <旧版Markdown> [Excel]` 命令继续可用，供历史表格转换；新流程直接使用结构化 JSON 写工作簿。
