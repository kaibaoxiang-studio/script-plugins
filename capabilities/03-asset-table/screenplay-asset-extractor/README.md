# 剧本资产表提取插件

使用 Harness Creator 生成独立 `screenplay-asset-extractor` 插件，入口 `extract-asset-table`。输入一级标准剧本 JSON，输出资产 JSON、四张核心工作表组成的 XLSX，以及独立疑点 JSON/Markdown。关键特效出现时增加“特效”工作表。插件不生成图像或声音。

源码分工：`scripts/asset_core.py` 完成一级 JSON 检查、保守底稿、来源与资产引用校验、报告；`scripts/asset_xlsx.py` 从同一资产 JSON 渲染 Excel。Agent 按 `references/asset-rules.md` 作有依据的身份、状态与道具判断。旧 Skill 目录保留作对照，不是插件依赖。

构建：用 Python 3.12+ 运行 `build_blueprint.py`，再以 Harness Creator 的 `harness.py build --spec blueprint.json --output ../screenplay-asset-extractor --confirmed` 构建。构建后锁定 `openpyxl` 与 `et_xmlfile`，执行 `validate`、实际 `run-capability` 和 `package`。验收记录见 `VALIDATION.md`。
