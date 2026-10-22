# 剧本标准化插件源码

此目录保留可编辑的脚本、references、蓝图生成器和测试。`build_blueprint.py` 将这些文件写入 HarnessBlueprintV1；Harness Creator 在相邻目录生成独立插件源码，再打包 ZIP。运行时不依赖本目录、原始 ZIP 或用户样稿。

`publish_local_plugin.py` 给已构建插件补上 Codex 插件选择器的展示名称与默认提示，并生成 `../dist/local-marketplace`。市场中的插件是发布快照；源码改变后需重新构建或 patch、重新执行发布脚本，再更新安装。

公开能力：`standardize-screenplay` 生成标准剧本 JSON/Markdown 和独立疑点报告；`review-screenplay` 独立生成疑点报告。默认轻审，深审需显式选择。剧本已有正文时脚本先完成保真抽取；纯细纲由 Agent 依据来源逐集创作。

面向用户的交付文件为 `标准化剧本.json`、`标准化剧本.md`、`剧本疑点报告.json`、`剧本疑点报告.md`。新建交付文件夹和文件时优先使用中文名；用户指定路径及系统接口契约优先。

直接检查确定性抽取：

```sh
python3.12 scripts/screenplay_core.py prepare /absolute/input.docx --output /absolute/work.json
python3.12 scripts/screenplay_core.py finalize /absolute/work.json --output-dir /absolute/out
```

`prepare` 的 `work.json` 是可审修中间物。`finalize` 拒绝未完成创作的纯细纲，避免把占位输出误称标准剧本。详细格式和审查边界见 references。
