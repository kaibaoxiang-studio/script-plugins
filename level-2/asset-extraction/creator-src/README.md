# 剧本资产表提取插件维护源码

本目录是 `screenplay-asset-extractor` v0.3.2 的唯一构建源。插件支持标准 DOCX、结构化 Markdown 和 `standardized_screenplay_v1` JSON。DOCX/Markdown 使用插件内置 `scripts/workflow.py` 完成 `prepare → 逐场复核 → bind → export → check → visual-review → finalize`；JSON 保留兼容入口。

`build_blueprint.py` 生成 `blueprint.json`，再由 Harness Creator 构建插件。构建后必须运行静态校验、独立解压校验、JSON→Excel 验收，并确认包内不存在 `__pycache__` 或 `.pyc`。
