# 二级 · 剧本资产表提取

组件 `screenplay-asset-extractor` **0.3.2**，提供标准剧本资产提取能力。插件支持 DOCX、结构化 Markdown 和 `standardized_screenplay_v1` JSON。DOCX/Markdown 强制使用插件内置 `workflow.py`，按 `prepare → 逐场复核 → bind → export → check → visual-review → finalize` 完成；JSON 入口保留兼容能力。

正式 Excel 固定包含人物、场景、道具、场次总表四张核心表；存在需单独制作的关键特效时增加特效表。所有可见单元格水平、垂直居中并自动换行。
