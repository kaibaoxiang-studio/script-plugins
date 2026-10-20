# 02｜场记表

**当前状态：可导出基础场景索引；正式场记表尚未定义。**

[ai-script-breakdown](ai-script-breakdown/SKILL.md) 是上游完整 Skill 快照，包含文本解析、共享戏剧分析、逐场和节拍规则、证据与覆盖校验。原 Skill 有显式调用与计划/执行门槛；复制到仓库不代表它已被本项目主控调用。

scripts/export_scene_log.py 将 01 解析出的 JSON 场景记录导出为 CSV，保留场景 ID、场号、标题、内外景、地点、时间、确定性、原文位置及文本。它只做确定性转表，不推断剧情功能或补写缺失内容。

从仓库根目录运行：

    python3 capabilities/02-scene-log/scripts/export_scene_log.py \
      /tmp/script-scenes.json /tmp/scene-index.csv

下一步需要团队确认场记表字段、逐场覆盖标准、人工校对方式，以及它与资产表/节拍表的正式交接契约。参考 [shared-analysis.md](ai-script-breakdown/references/shared-analysis.md)、[format-and-evidence.md](ai-script-breakdown/references/format-and-evidence.md) 和 [breakdown.schema.json](ai-script-breakdown/schemas/breakdown.schema.json)。
