---
name: screenplay-standardizer
description: "将 DOCX、TXT、Markdown 剧本或分集细纲转换为可追溯的标准剧本，并独立审查疑点"
---

# screenplay-standardizer

完成剧本一级标准化；提供 JSON/Markdown 标准稿和独立、证据明确的轻审或深审报告

按下列入口读取本包 Skill 与相关参考，复用已有输入和确认，只补问会实质影响结果的缺项。正常宿主入口按[原生子代理协作](../../references/native-delegation.md)委派连续集场段的语义工作，主控跨段归并并唯一写入；Python 直接负责解析、保存、检查和导出，不强制另起 Harness 会话。独立命令行 Harness 为显式兼容入口。使用用户指定工作目录，报告真实产物及未完成项。

- `$standardize-screenplay`: 把 DOCX、TXT 或 Markdown 剧本及纯细纲做成标准剧本 JSON/Markdown 与疑点报告
- `$review-screenplay`: 独立检查剧本的结构、姓名、台词和按需跨集连续性，只交证据化疑点报告

See [runtime instructions](../../RUNTIME.md).
