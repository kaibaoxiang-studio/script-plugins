# 03｜资产表

**当前状态：已有概念设计资产目录；完整制作资产表尚未实现。**

[screenplay-concept-director](screenplay-concept-director/SKILL.md) 是上游完整 Skill 快照。其 catalog 命令从**已完成且来源新鲜的** screenplay_breakdown_v1 生成 AssetCatalogV1；收录角色主资产、地点主资产、场景状态和关键道具。它不是“读入场记表就自动找全所有资产”的工具。

scripts/export_asset_table.py 只把已有 AssetCatalogV1 导出为便于查看的 CSV，不新增资产判断：

    python3 capabilities/03-asset-table/scripts/export_asset_table.py \
      /path/to/asset-catalog.json /tmp/asset-table.csv

上游目录的生成需先具备合格的 breakdown.json；使用 Python 3.12+，显式提供本仓库对应的 ai-script-breakdown 目录作为 --analyzer-root：

    python3.12 capabilities/03-asset-table/screenplay-concept-director/scripts/concept_director.py catalog \
      --breakdown /path/to/breakdown.json \
      --analyzer-root capabilities/02-scene-log/ai-script-breakdown \
      --output /tmp/asset-catalog.json

须按原 Skill 的新鲜度和确认门槛执行。目录接口见 [interfaces.md](screenplay-concept-director/references/interfaces.md)，设计分类见 [design-method.md](screenplay-concept-director/references/design-method.md)。

待定义：服装、妆造、特效、车辆、群演等制作资产的分类、别名归并、跨场状态和人工确认规则。
