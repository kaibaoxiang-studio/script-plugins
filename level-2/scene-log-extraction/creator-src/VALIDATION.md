# 场记表提取 v0.1.0 验收记录

## 来源与构建

- 改造基线：`ai-continuity-sheet` 原仓库提交 `0c0750115477a6881e1b10650a5266aa9a665fdd`；主 Skill、七个辅助 Skill、原 13 列和历史 Markdown 转 Excel 脚本均保留。
- Harness Creator `doctor`：Python 3.12.14、Codex CLI 0.163.0-alpha.10.2 可用，Creator 自身插件有效。
- `creator-src/build_blueprint.py` 由现有源码生成蓝图；Harness Creator `build` 与哈希校验 `patch` 成功。最终插件 `validate`：6 个能力、14 个 Skill、0 错误。
- 最终 ZIP：`scene-log-extractor-0.1.0.zip`，SHA-256 `24f56ae515a72b68588e72dd4787e95d6d9aae097418b7edf70692b95447beb0`。最终 ZIP 解包至独立目录后 `doctor`、`validate` 均通过；锁定依赖安装成功。
- 本地市场 `scene-log-extractor-local` 已添加，`scene-log-extractor@scene-log-extractor-local` v0.1.0 安装并在 `codex plugin list --json` 中显示 `installed=true`、`enabled=true`。

## 行为验证

| 检查 | 结果 |
|---|---|
| `python3.12 -m unittest discover -s creator-src/tests -v` | 6 项通过：一拍一行、原文与双语 OS、跨集场号、长正文分段、缺正文与漏拍报错、无依据人物拒绝、上游未映射来源入报告、动作引号分句。 |
| 一级实际样稿整剧调用 | 1 集 2 场 6 拍，四个文件齐全；`verify_artifacts.py` 核对 JSON、Excel、正文和台词通过。 |
| 跨集连续性小样 | 2 集 2 场 4 拍，报告抓到「林申／林深」疑似错名、铜钥匙状态承接缺口和动作写喊话但对白块缺失；明示的「顾云改名顾澜」未误报。双语 VO 和一级生成来源保留。 |
| 公开 `extract-scene-log` 能力 | `run-capability` 指定第 2 集成功：只交付该集 1 场 3 拍，四个文件及输入追溯交叉核对通过。 |
| 最终候选包真实调用 | 1 集 1 场 3 拍，四个文件齐全，`verify_artifacts.py` 通过；候选内容即最终 ZIP 内容。 |
| 预发布包独立解包真实调用 | 解包安装后 1 集 1 场 3 拍成功；JSON、Excel、报告交叉核对通过。最终 ZIP 另经独立解包的 `doctor` 与 `validate` 检查。 |
| 历史 Markdown 转 Excel | 原 `convert_continuity_sheet.py` 对旧 13 列样稿成功转换，首行原文和两行数据均存在。 |
| 完成任务的 `--resume` 路径 | 同一运行状态、输入和插件版本下重新交付四个文件成功。 |

## 验收边界

- 模型提出的摄影、灯光、表演和时长均以 `pending` 保存，不能视为已确认制作方案。
- 未强制终止正在执行的 App Server 来模拟断电；中断节点的重试与检查点由包内 Harness Engine 实现，本次验证了同版本已完成运行的续用路径。输入文件或插件包变化时会拒绝沿用旧运行状态。
- 仓库未见许可文件；此版本按团队现有源码在原仓库内增量改造并用于本地安装，未复制 Skill Orchestrator 知识到插件。

## 复现命令

```sh
python3.12 creator-src/build_blueprint.py
python3.12 $HARNESS_CREATOR_ROOT/harness.py build --spec creator-src/blueprint.json --output scene-log-extractor --confirmed
python3.12 creator-src/make_plugin_patch.py
python3.12 $HARNESS_CREATOR_ROOT/harness.py patch --plugin scene-log-extractor --plan creator-src/plugin-patch.json --confirmed
python3.12 scene-log-extractor/harness.py validate --plugin scene-log-extractor
python3.12 scene-log-extractor/harness.py package --plugin scene-log-extractor --output scene-log-extractor-0.1.0.zip
python3.12 creator-src/verify_artifacts.py /absolute/path/standardized_screenplay.json /absolute/path/output
```

构建目标目录若已存在，应先用独立候选目录构建并验证，再替换旧生成目录；不要覆盖用户修改。
