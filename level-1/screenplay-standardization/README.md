# 一级 · 剧本标准化

展示名「剧本标准化」，组件 screenplay-standardizer 0.1.2。接收 DOCX、TXT、Markdown 剧本或分集细纲，交付两个二级插件共同使用的标准 JSON。

| 入口 | 作用 | 文件 |
| --- | --- | --- |
| standardize-screenplay | 选主稿、整理集场、保留对白/双语/标色/来源；细纲由 Agent 有依据地创作 | 标准化剧本.json、标准化剧本.md、剧本疑点报告.json、剧本疑点报告.md |
| review-screenplay | 独立轻审；明确选择 deep 时检查跨集连续性与细纲覆盖 | 剧本疑点报告.json、剧本疑点报告.md |

JSON 使用 standardized_screenplay_v1，含集、场、内容块、source_refs、origin 和覆盖状态。语义创作/改写保留生成标记与依据。轻审默认，深审须明确选择；疑点独立交付。

原稿歧义、多版本、第一人称外化及细纲创作需 Agent 判断；脚本负责保守抽取、结构校验、渲染和可确定的检查。完成后将 JSON 分别交给[场记表](../../level-2/scene-log-extraction/README.md)和[资产表](../../level-2/asset-extraction/README.md)。

- [screenplay-standardizer/](screenplay-standardizer/README.md)：独立安装插件，自带 Harness、知识与依赖锁。
- [creator-src/](creator-src/README.md)：维护脚本、规则、蓝图和测试。
- [安装与运行](../../docs/installation.md)
- [建设验收](creator-src/VALIDATION.md)及[1.0 最新验证](../../docs/validation-v1.0.md)

真实业务样例经 Agent 整理和脚本校验后交付 10 集、28 场、1 条疑点。本次确定性检查 10 项通过、1 项私有原稿测试跳过。该案例含定点修订，不能据此声称任意剧本均可无干预准确转换。

0.1.2 修复原稿只有角色标签时产生空对白块的问题：保留来源位置并登记疑点，生成的正文可供场记表继续校验。
