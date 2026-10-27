---
name: screenplay-asset-extractor
description: "从标准剧本 DOCX 或一级标准 JSON 提取经逐场审核的剧本资产表"
---

# 剧本资产表提取 · 0.1.1

按实际输入选择本插件内的 Skill，直接读取下列相对路径的 SKILL.md；不要因为个人技能目录存在同名 Skill 而换用其他版本。使用用户指定目录，报告真实交付和校验结果。

- 一级 `standardized_screenplay_v1` JSON：读取 [extract-asset-table](../extract-asset-table/SKILL.md)，先准备底稿、再逐场提取与审核、最后导出四件套。Harness 的 `extract-asset-table` 能力对应此入口，适合与资产设计总控按同源 SHA 交接。
- 标准剧本 DOCX：读取 [script-asset-extractor 0.1.2](../script-asset-extractor/SKILL.md)，按逐场人物记录及道具实物身份提取，输出资产 JSON 与四表 Excel。使用本插件锁定 Python 环境运行 Skill 自带脚本，不能把 JSON 文件改名冒充 DOCX。

两条链路都必须阅读全文并保存逐场审核。缺少持有人、材质或破损变化不代表没有道具；零道具须有逐场依据。初始化与格式校验不代替语义提取。旧工作文件先补审核再导出，已发布历史资产文件仍可读取。

See [runtime instructions](../../RUNTIME.md).
