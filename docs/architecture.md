# 剧本插件 1.0 的交接关系

一级负责把原始材料整理为可追溯的标准剧本；二级两个插件读取同一 JSON，分别交付业务表和独立疑点报告。

| 交接 | 要求 |
| --- | --- |
| 原始材料 → 一级 | DOCX、UTF-8 TXT、Markdown；纯细纲需由 Agent 完成有依据的创作 |
| 一级 → 场记 | 完成的 standardized_screenplay_v1 JSON；保留集场、内容块、source_refs、origin、coverage |
| 一级 → 资产 | 同一份 JSON；人物、场景、道具、状态、特效均以原文为依据 |
| 二级 → 人工复核 | 制作建议和疑点分别标记，不擅自修改原文 |

场记表与资产表是并列二级产物。节拍归入场记的 P 段，一个 P 对应一个叙事拍；不另设三级表。资产可以参考场记线索，正式输入和证据仍来自一级剧本。

JSON 是程序交接格式，Markdown 和 Excel 是阅读/复核格式。Harness Creator 在 engineering 中作为额外工程，用于创建和维护插件。业务插件自带 Harness 与知识，运行时无需安装 Creator。
