# 二级 · 剧本资产表提取

当前主要入口为 [`script-asset-extractor v0.1.1`](screenplay-asset-extractor/skills/script-asset-extractor/SKILL.md)。提供标准剧本 DOCX，调用 `$script-asset-extractor`，输出 `assets.json` 和 `<剧名>-资产表.xlsx`；工作簿固定包含人物、场景、道具、场次总表。新版按逐场人物记录核对造型，按实物记录核对道具身份、异称、交接与状态，错误和未确认警告会阻止导出。

v0.1.1 统一各导出后端的 Excel 模板：人物按去重出场次数降序，组内状态按首次使用的剧本呈现顺序排列；保留逐场备注与道具局部指代证据，并验收已保存工作簿的内容、分组底色、合并、行高、冻结和筛选。详细契约见 [Excel 输出与验收](screenplay-asset-extractor/skills/script-asset-extractor/references/excel_output.md)。该 skill 的 82 项回归测试通过；自动检查不替代视觉和语义核定。

完整 skill 及其脚本、规则、测试均位于 `screenplay-asset-extractor/skills/script-asset-extractor/`。该入口直接执行 skill 自带脚本，无需旧 JSON Harness。原 `extract-asset-table` 保留用于一级标准 JSON 输入；下文说明该兼容入口。

展示名「剧本资产表提取」，组件 screenplay-asset-extractor 0.1.0，公开入口 extract-asset-table。它与[场记表提取](../scene-log-extraction/README.md)并列，直接读取一级完成的 standardized_screenplay_v1 JSON，无需先产出场记表。

提取人物、主要动物、群演组、场景/子场景、道具、按需关键特效及持续状态，保留别名、source_refs、origin 和集场引用。有依据的服装/伤情归人物状态，固定陈设归场景，车辆归道具；重要且需单独制作的明确特效才单列。

## 四个交付物

| 文件 | 内容 |
| --- | --- |
| assets.json | 资产、状态、证据、制作需求及场次索引 |
| screenplay-asset-table.xlsx | 人物、场景、道具、场次总表四张核心表；存在关键特效时增加特效表 |
| asset_findings.json | 可追溯结构化疑点 |
| asset_findings.md | 独立疑点报告 |

头像、全身图、四视图、九宫格表情和声音等属于**制作需求登记**，不生成图像或声音。原文未写的外观、材质、音色等留空；未证实的身份/状态关系进入报告。资产数量和状态行数不同，不能用 Excel 行数直接统计资产数。

- [screenplay-asset-extractor/](screenplay-asset-extractor/README.md)：完整独立插件。
- [creator-src/](creator-src/README.md)：维护源码、规则、蓝图与合成验收脚本。
- [安装与调用](../../docs/installation.md)
- [建设验收](creator-src/VALIDATION.md)及[1.0 最新验证](../../docs/validation-v1.0.md)

全剧业务样例覆盖 28 场，交付 22 人物、17 场景、26 道具、0 单列特效及 3 条疑点，来源与工作簿核对通过。三份长稿完成整稿结构验收和各前两集真实 Agent 提取，尚未逐集人工核定三部全剧。资产身份、归并、状态和制作必要性仍需业务确认。
