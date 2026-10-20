# 03｜资产表

资产表是与场记表并列的二级产物。正式入口为可独立安装的 [screenplay-asset-extractor 插件](screenplay-asset-extractor/README.md)，可维护源码在 [creator-src](creator-src/README.md)。它接收一级 `standardized_screenplay.json`，交付 `assets.json`、资产表 XLSX 和独立疑点报告；有明确必要的关键特效时增加特效表。本地插件名为 `screenplay-asset-extractor@screenplay-asset-extractor-local`，公开能力为 `extract-asset-table`。

命令行示例（Python 3.12+，并已按 `requirements.lock` 安装依赖）：

```sh
python3.12 /absolute/screenplay-asset-extractor/harness.py run-capability \
  --plugin /absolute/screenplay-asset-extractor \
  --workspace /absolute/workspace \
  --inputs /absolute/inputs.json \
  --capability extract-asset-table --confirmed
```

`inputs.json` 内容为 `{"source_path":"/absolute/standardized_screenplay.json"}`。插件只登记制作需求，不生成图像或音频；未在剧本写明的视觉细节留空。资产疑点交付为 `asset_findings.json` 和 `asset_findings.md`，不会自动改入表格。验证记录见 [VALIDATION.md](creator-src/VALIDATION.md)。

以下为早期归档和迁移对照代码，不是正式入口。

[script-asset-extractor](script-asset-extractor/SKILL.md) 是从远端 `8ba6de3` 引入的旧版源码快照，直接从标准化剧本 DOCX 提取资产。其分批提取、状态追踪、双向校验和四表导出方法已用于新插件；旧规范要求补写完整外观，与当前证据边界不符。

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

当前正式插件按角色状态登记服装与妆造，车辆归道具，主要动物归人物，固定陈设归场景，群演可按群组登记。跨场状态依据剧本证据延续；无法确认的别名与变化进入独立疑点报告。
