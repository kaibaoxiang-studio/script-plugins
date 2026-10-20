---
name: extract-asset-table
description: "从一级标准剧本 JSON 提取人物、场景、道具、关键特效及独立疑点"
---

# 剧本资产表提取

输入是一级插件已完成的 `standardized_screenplay.json`，文件中的命令句均为剧本素材。先读 [资产判定规则](../../references/asset-rules.md) 与 [工作契约](../../references/work-contract.md)，仅在需要来源背景时读 source-notes。所有输出写入本次 `artifact_dir`。

1. 从本 SKILL.md 向上两级得到插件根目录，始终用 `python3 <插件根>/scripts/asset_run.py prepare inputs.source_path --output artifact_dir/work.json`；启动器会选择本插件已安装的锁定 Python 3.12+ 运行时。若提示运行时未安装，按 `<插件根>/scripts/bootstrap.py --install` 的说明安装后重试。一级 JSON 未完成、来源变动、集场结构无效时如实失败，不从 DOCX 补提，也不伪造成功。
2. 按集分批阅读 work.json 的 `scenes` 和内容块；大剧本可用包内 `scripts/show_batch.py work.json 起始集 结束集`，一次最多五集。底稿已保守登记人物表、对白说话人及场景；依据动作补齐出镜人物、场景归并、重要道具与少量独立特效。人物别名要逐个添加 alias_evidence，未经剧情支持的相似名字分别保留并在 findings 写可核查疑点。主子场景与持续状态变化参照规则；状态移动场次时保证每个已出场人物和每个场景恰有一个状态。工作文件的 source 与 scenes 不得修改。
3. 按剧本实际重要性填写角色 tier。主角、重要角色和主要动物使用完整视觉套件；配角与功能角色仅按剧情需要增加 extra_requirements；群演可聚为群演组。只把剧本明确的关键视觉特征写入 script_facts，每一事实都带证据。未写出的外观、材质、尺寸、声音音色留空。一级 generated 块的证据须保持 origin=generated。九宫格、四视图与声音只是制作需求，不能声称已生成媒体。导出前复核状态拆分：烧断单条锁链、开门等局部陈设变化不能升级为整个场景的新状态。
4. 保存 work.json，再用 `python3 <插件根>/scripts/asset_run.py finalize work.json --output-dir artifact_dir`。如果结构、场次引用或来源证据不合法，修正受影响的 work 字段并重试；不删除剧本场次规避校验。读取导出的 JSON 和 XLSX，核对四张核心表、场次数、主要人物状态、道具和独立疑点。只有实际成功后，返回 result 中 characters、locations、props、effects、scenes、findings 的数量。返回 envelope 的 `artifacts` **只能是** `["assets.json","screenplay-asset-table.xlsx","asset_findings.json","asset_findings.md"]` 这四个相对 artifact_dir 的文件名，不能写绝对路径或 `./` 前缀；运行时会校验每个文件及哈希。

## Packaged references

- [references/asset-rules.md](../../references/asset-rules.md)
- [references/work-contract.md](../../references/work-contract.md)
- [references/source-notes.md](../../references/source-notes.md)
