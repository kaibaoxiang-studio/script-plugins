# Harness Creator v0.2.0 候选验证

日期：2026-10-26。目标：在 v0.1 单机运行底座上增加功能级规格和验收证据门槛，并复查真实 Codex 中文路径调用。此记录只描述本次已执行的检查。

## 已通过

- 使用兼容的 Python 3.12.14 执行 `harness.py doctor`：Codex CLI 可发现，候选结构检查有效。系统默认 `python3` 是 3.9.6，需明确选择兼容解释器。
- `python -m unittest discover -s tests -q`：29 项通过，包含原有 24 项及交付计划、真实检查日志、证据失效、自我验收拒绝、验收后插件改动拒绝等 5 项检查；其中覆盖证据通过后的 `release-package` 命令。
- `harness.py validate`：6 项能力、7 个 Skills 的结构、引用、脚本和目录契约有效。
- 直接 App Server 小样：Agent 在中文目录写入 `marker.txt`，返回值和文件字节与 `中文路径验证：剧本 A` 相同。报告位于 `work/harness-creator-v0.2-acceptance/中文路径/smoke-report.json`。
- 生成插件完整链路：候选 Creator 生成 `echo-plugin`，由其独立运行引擎启动真实 Codex Agent，在中文目录写入文件并通过输出 Schema、产物路径和哈希校验。成功运行的报告位于 `work/harness-creator-v0.2-acceptance/完整插件中文路径-修复后/运行工作区/.harness/run-a0de9c5fc8a0431b/run-report.json`。
- 候选版 ZIP 可打包，解压到独立目录后再次运行 `harness.py validate` 通过；ZIP 未包含 `.git`、`.venv`、`.harness`、`dist` 或测试目录。

## 发现并修正

首次生成插件的 Agent 节点在 180 秒后失败。线程记录显示任务提示只给出 `$echo` 名称，Agent 花时间搜索本机已安装 Skills，未及时执行。候选版的 App Server 客户端现将已选技能的准确路径与正文直接放入节点任务提示，仍保留结构化 `skill` 输入。修正后完整链路通过。失败运行记录保留在 `work/harness-creator-v0.2-acceptance/完整插件中文路径/运行工作区/.harness/run-04a6d9be90494eb1/run-report.json`。

## 验证边界

- 成功的中文路径小样证明本次路径和 CLI 组合可运行；它不证明任意路径、模型或业务插件都能成功。
- 交付门槛核对蓝图与计划版本、场景日志、不同会话标识、报告、产物哈希与最终插件指纹；它不能仅凭标识证明审查者真的独立，也不能代替剧本等业务内容的人工或专业复核。
- 尚未用真实剧本材料完成“标准化→场记→资产”整链验收，也未做多机高可用、动态 DAG 或性能回归。v0.2 候选没有宣称这些能力。
- 本次改动由同一会话实现并自测，因此候选版自身尚无独立审查结论；作为可安装候选交付，不标记为业务验收完成。
