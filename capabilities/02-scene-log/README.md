# 02｜场记表

**二级产物定义：场记表与资产表并列，由一级标准化剧本分别进入二级环节；节拍归入场记表，不再单列三级产物。**

团队成员已将 [ai-continuity-sheet](https://github.com/kaibaoxiang-studio/ai-continuity-sheet) 上传到独立仓库。其[主 Skill](https://github.com/kaibaoxiang-studio/ai-continuity-sheet/blob/main/ai-continuity-sheet/SKILL.md)以纯剧本为输入，按集数、场次、片段组织记录，调度 7 个子 Skill，设计了集数、场次、片段、出场人物、场景、道具、摄影、灯光/色卡、台词、时长、微表情情绪指导、动作表演指导、剧情大纲共 13 列，并通过转换脚本输出 Excel。主 Skill 还依赖 `jimeng-storyboard-v3` 和 `leos-six-department-directing-team-skill-v1` 的上游分析结果。

**接入状态：待对齐。** 该独立仓库目前直接读取纯剧本，尚未验证与本项目一级标准化 JSON/Markdown 的输入接口；13 列中没有独立节拍字段，虽然其工作流提到切节拍。团队仍需确定节拍如何记录、原文追溯方式和逐场验收标准。上传此能力不等于本仓库已完成两级联调。

## 本仓库早期材料

[ai-script-breakdown](ai-script-breakdown/SKILL.md) 是上游完整 Skill 快照，包含文本解析、共享戏剧分析、逐场和节拍规则、证据与覆盖校验。原 Skill 有显式调用与计划/执行门槛；复制到仓库不代表它已被本项目主控调用。

scripts/export_scene_log.py 将 01 解析出的 JSON 场景记录导出为 CSV，保留场景 ID、场号、标题、内外景、地点、时间、确定性、原文位置及文本。它只做确定性转表，不推断剧情功能或补写缺失内容。

从仓库根目录运行：

    python3 capabilities/02-scene-log/scripts/export_scene_log.py \
      /tmp/script-scenes.json /tmp/scene-index.csv

后续需对齐正式场记表字段、逐场覆盖标准、人工校对方式，以及与并列资产表的线索共享方式。参考 [shared-analysis.md](ai-script-breakdown/references/shared-analysis.md)、[format-and-evidence.md](ai-script-breakdown/references/format-and-evidence.md) 和 [breakdown.schema.json](ai-script-breakdown/schemas/breakdown.schema.json)。
