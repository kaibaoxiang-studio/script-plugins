# 03｜资产表

**当前框架：资产表是与场记表并列的二级产物。正式制作资产表能力待上传。** 资产提炼以标准化剧本中的原文为依据，场记表可提供核对线索；二者之间不是上下级产物关系。

以下为早期归档和试验代码，不代表当前二级资产表已完成。

[screenplay-concept-director](screenplay-concept-director/SKILL.md) 是上游完整 Skill 快照。其 catalog 命令从**已完成且来源新鲜的** screenplay_breakdown_v1 生成 AssetCatalogV1；收录角色主资产、地点主资产、场景状态和关键道具。它不是”读入场记表就自动找全所有资产”的工具。

[script-asset-extractor](script-asset-extractor/SKILL.md) 直接从标准化剧本 docx（含「第N集｜」「N-M 场景 内/外 时间」「人物：」「▲」格式）提取人物、场景、道具资产及其状态（换装、受伤、年龄、破坏等），输出 Excel 资产表（人物、场景、道具、场次总表四个 sheet）。流程分解析剧本、分批提取、双向校验、生成 Excel、人工抽查五步，详见 SKILL.md。

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
