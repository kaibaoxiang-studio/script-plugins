# 剧本标准化 · 一级插件

组件 `screenplay-standardizer`，版本 **0.1.2**，属于开宝箱工作室剧本插件 **1.0.1**。本目录是可独立运行的完整插件，包含 Skills、规则、Python Harness、脚本和依赖锁；使用时无需另装 Harness Creator。

## 能力与交付

| 入口 | 输入与作用 | 交付 |
| --- | --- | --- |
| `standardize-screenplay` | DOCX、TXT、Markdown 剧本或分集细纲；选择主稿、整理集场、保留对白、双语、标色与来源 | `标准化剧本.json`、`标准化剧本.md`、`剧本疑点报告.json`、`剧本疑点报告.md` |
| `review-screenplay` | 来源文件或标准剧本 JSON；独立检查证据明确的疑点 | `剧本疑点报告.json`、`剧本疑点报告.md` |

默认 `review_mode=light`；明确选择 `deep` 时，由 Agent 做跨集连续性与细纲覆盖复核。纯细纲需要 Agent 依据来源创作；脚本拒绝直接导出尚未完成创作的占位稿。语义整理和改写保留生成标记与来源依据，疑点独立交付。

标准 JSON 的格式为 `standardized_screenplay_v1`。两个二级插件「场记表提取」和「剧本资产表提取」分别读取这份 JSON；Markdown 用于阅读。二级业务提取与最终制作方案须由对应插件和制作方完成。

## 安装到 Codex

团队成员接受仓库邀请，并确认本机 Git 可以读取仓库后，执行：

```sh
codex plugin marketplace add https://github.com/kaibaoxiang-studio/script-plugins.git --ref v1.0.1
codex plugin add screenplay-standardizer@script-plugins
```

在新聊天中选择「剧本标准化」并提供文件，或明确调用 `$screenplay-standardizer`、`$standardize-screenplay`、`$review-screenplay`。完整安装说明见[项目安装文档](https://github.com/kaibaoxiang-studio/script-plugins/blob/v1.0.1/docs/installation.md)。

## 独立目录与命令行

需要 Python 3.12+；调用 Agent 能力还需要已登录且可用的 Codex CLI。在本插件根目录执行：

```sh
python3.12 scripts/bootstrap.py --install
```

将返回 JSON 中的 `python` 路径填入下例：

```sh
runtime_python="/absolute/path/returned/python"
"$runtime_python" harness.py doctor
"$runtime_python" harness.py validate
```

准备 `inputs.json`，将来源路径换成真实文件的绝对路径：

```json
{"source_path":"/absolute/path/input.docx","input_kind":"auto","review_mode":"light"}
```

```sh
"$runtime_python" harness.py run-capability \
  --capability standardize-screenplay \
  --inputs /absolute/path/inputs.json \
  --workspace /absolute/path/standardize-work --confirmed
```

独立审查改用 `--capability review-screenplay`，其输入只包含 `source_path` 和 `review_mode`。运行结果中的 artifacts 指向实际交付文件。输入契约见 [capabilities.json](capabilities.json)，运行方式见 [RUNTIME.md](RUNTIME.md)。

直接执行保守抽取、校验和渲染时：

```sh
"$runtime_python" scripts/screenplay_core.py prepare /absolute/input.docx --output /absolute/work.json
"$runtime_python" scripts/screenplay_core.py finalize /absolute/work.json --output-dir /absolute/out
```

`work.json` 是可供 Agent 审修的中间文件；这组脚本命令不会自动完成细纲创作、语义改写或主动深审。

## 验证与维护

本次确定性测试为 10 项通过、1 项私有原稿测试跳过。真实业务样例经 Agent 整理及脚本校验后交付 10 集、28 场、1 条疑点；该案例含定点修订，不能据此声称任意原稿都可无干预准确转换。范围见[项目验证记录](https://github.com/kaibaoxiang-studio/script-plugins/blob/v1.0.1/docs/validation-v1.0.md)。

蓝图生成器和测试位于仓库的 [creator-src](https://github.com/kaibaoxiang-studio/script-plugins/tree/v1.0.1/level-1/screenplay-standardization/creator-src)，不属于独立安装包的运行依赖。本 README 由其中的 `PLUGIN-README.md` 维护并写入构建蓝图。来源与许可见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
