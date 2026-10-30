# `extract-asset-table` 工作契约

输入：`{"source_path":"/absolute/standardized_screenplay.json"}`。来源须为一级插件的 `standardized_screenplay_v1` 完成稿。运行时只依赖包内脚本和锁定 Python 依赖，不调用一级、Skill Orchestrator 或 Creator 插件。

执行：用 `python3 scripts/launch.py scripts/asset_run.py prepare SOURCE --output WORK` 生成保守底稿；启动器选择插件锁定的 Python 3.12+ 运行时。`scenes` 和 `source` 不得修改。Agent 按集浏览剧本内容块，大剧本用 `show_batch.py WORK 起始集 结束集` 每次读取一至五集；补充人物层级、主要动物/群演组类型、人物别名、资产状态、场景合并/子场景、道具、关键特效、剧本事实和业务疑点。按 [逐场语义审核](semantic-review.md) 保存覆盖全部场次和内容块的 `semantic_review`，绑定来源与资产快照哈希。每类资产逐场有明确结论；没有道具可以成立，未经判读不能直接保留空数组。人物层级须完成。再用同一启动器运行 `finalize WORK --output-dir DIR`；硬性错误必须修复后重试。

资产数据：`assets` 含 `characters`、`locations`、`props`、`effects`。各资产有唯一 ID、名称、`evidence` 和至少一个 `states`；场景还需 `subscenes`。`evidence` 项含 `{scene_id,text,source_refs,origin}`。状态含 `{id,name,scenes,evidence,script_facts}`，事实含 `{text,evidence}`。别名要在 `aliases` 与 `alias_evidence` 中成对出现。人物 `tier` 可取主角、重要角色、配角、功能角色、群演；`asset_type` 可取人物、主要动物、群演组。制作清单由 `tier`、状态和发声自动推导；额外需求放 `extra_requirements`，注明 `basis=script` 或 `production`，前者需证据。

正式输出：`assets.json`、`screenplay-asset-table.xlsx`、`asset_findings.json`、`asset_findings.md`。工作 JSON 仅作中间文件。Excel 始终包含人物、场景、道具、场次总表；有关键特效时增加特效表。`assets.json` 保存证据位置与生成标记；Excel 是同一 JSON 的视图。疑点不进入资产的确定字段。剧本来源文件变动后，旧工作 JSON 不能继续导出。

旧工作文件须补齐审核后再导出；既有正式资产文件保留历史可读性。上游 source_coverage 不表示本次资产语义覆盖。
