# 01｜剧本标准化

本目录包含可独立安装的 [screenplay-standardizer 插件](screenplay-standardizer/README.md)及其[可维护源码](creator-src/README.md)。插件接收 DOCX、TXT、Markdown，公开两个能力：

本机已将它注册为 Codex 本地插件 **[@剧本标准化](plugin://screenplay-standardizer@screenplay-standardizer-local)**，可像 Harness Creator 一样在插件选择器中使用。插件名为 `screenplay-standardizer`；默认入口 Skill 会按请求转给标准化或独立审查能力。

| 入口 | 用途 | 交付 |
| --- | --- | --- |
| `standardize-screenplay` | 选主稿、标准化已有剧本；纯分集细纲经创作 Agent 补成剧本 | `standardized_screenplay.json`、`standardized_screenplay.md`、`findings.json`、`findings.md` |
| `review-screenplay` | 独立轻审；显式选择 `deep` 后做跨集连续性与细纲覆盖复核 | `findings.json`、`findings.md` |

两项能力均默认 `review_mode=light`。标准 JSON 保存集、场、内容块、来源段落、生成标记与 DOCX 原稿标色范围；Markdown 从该 JSON 结构渲染。审查只列证据化疑点，不自动改写剧本。纯细纲的脚本化、第一人称叙述的可拍摄性改写和主动深审由 Agent 按引用规范完成；命令行脚本负责保守抽取、结构校验、渲染与可确定的轻审。

解压 [安装包](screenplay-standardizer-0.1.0.zip)后，公开能力可用插件自带的 Harness 命令调用。先准备一个 JSON 输入文件，例如 `{"source_path":"/absolute/input.docx","review_mode":"light"}`，再运行：

```sh
python3.12 /absolute/screenplay-standardizer/harness.py run-capability \
  --plugin /absolute/screenplay-standardizer \
  --workspace /absolute/workspace \
  --inputs /absolute/inputs.json \
  --capability standardize-screenplay --confirmed
```

独立审查把 `--capability` 改为 `review-screenplay`；主动深审在输入 JSON 中设置 `"review_mode":"deep"`。如果同文件存在同级多个剧本版本，标准化输入可加 `"selected_section":2` 指定段号。

在其他 Codex 安装中，可从仓库根目录运行 `python3.12 capabilities/01-screenplay-standardization/creator-src/publish_local_plugin.py` 生成本地市场，再执行 `codex plugin marketplace add /absolute/path/to/dist/local-marketplace` 与 `codex plugin add screenplay-standardizer@screenplay-standardizer-local`。安装状态可用 `codex plugin list --marketplace screenplay-standardizer-local --json` 核对。

GitHub 仓库根目录也包含 Codex 市场清单。使用当前开发分支安装：

```sh
codex plugin marketplace add https://github.com/kaibaoxiang-studio/script-plugins.git \
  --ref codex/screenplay-standardizer-plugin
codex plugin add screenplay-standardizer@script-plugins
```

示例（Python 3.12+，从插件目录运行）：

```sh
python3.12 scripts/screenplay_core.py prepare /absolute/input.docx --output /absolute/work.json
python3.12 scripts/screenplay_core.py finalize /absolute/work.json --output-dir /absolute/out
python3.12 scripts/screenplay_core.py review /absolute/out/standardized_screenplay.json --output-dir /absolute/review
```

`prepare` 生成可供 Agent 修订的中间 JSON；纯细纲必须完成创作后才能 `finalize`。两个公开入口的输入契约见插件的 `capabilities.json`。验收记录见 [VALIDATION.md](creator-src/VALIDATION.md)。

原有的 `scripts/normalize_screenplay.py` 与 `analysis_provenance.py` 是上游解析器快照，仍可用于 Fountain/FDX 及场景线索提取；其场景映射 JSON 不等于本插件的标准剧本 JSON。历史评估见 [sn2s-assessment.md](references/sn2s-assessment.md)。
