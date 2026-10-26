# 剧本资产表提取 · 二级插件

主要入口已更新为 [`script-asset-extractor v0.1.1`](skills/script-asset-extractor/SKILL.md)：提供标准剧本 DOCX 并调用 `$script-asset-extractor`，按 skill 自带脚本提取，交付 `assets.json` 和 `<剧名>-资产表.xlsx` 四表工作簿。包含人物逐场状态、道具实物身份与异称证据校验。该入口无需运行 `harness.py`。

v0.1.1 使用共享展示计划统一 Excel 后端，人物按去重出场次数降序，状态按首次使用的剧本呈现顺序排列；保存后必须运行 `skills/script-asset-extractor/scripts/check_workbook.py` 核对内容与格式，再进行视觉和语义检查。模板、原生筛选补丁及验收边界见 [Excel 输出与验收](skills/script-asset-extractor/references/excel_output.md)。本次更新仅升级该 skill，组件和原 JSON Harness 的版本及输入输出契约保持不变。

原 `$extract-asset-table` 继续接收一级标准 JSON；以下输入、四文件交付及 Harness 命令仅适用于该兼容入口。

组件 `screenplay-asset-extractor`，版本 **0.1.0**，属于开宝箱工作室剧本插件 **1.0.0**。本目录包含独立运行所需的 Skills、规则、Python Harness、脚本和依赖锁；使用时无需另装 Harness Creator。

## 输入与功能

公开能力为 `extract-asset-table`。输入是一级「剧本标准化」已完成的 `standardized_screenplay_v1` JSON；本插件与场记表提取并列，可直接读取同一份一级 JSON。

- 提取人物、主要动物、群演组、场景与子场景、道具，以及需要单独制作的关键特效。
- 根据剧本证据整理合法别名和持续状态变化，记录来源位置；一级生成内容保留 `origin=generated`。
- 登记人物造型、四视图、九宫格表情和声音等制作需求。需求仅是待制作清单，不代表已经生成图像、声音或视频。
- 明确的剧本事实与独立疑点分别保存。未给出的外观、材质、尺寸、音色等字段留空；身份、归并和制作必要性有疑问时交付报告。

`script_facts` 和 `basis=script` 的需求须有剧本证据。`basis=production` 仅登记额外制作需求，不应写成原文事实。状态拆分用于换装、持续伤势、破坏等制作变化；短暂动作或局部陈设变化不自动升级为整个资产的新状态。具体规则见 [asset-rules.md](references/asset-rules.md)。

## 四个交付文件

| 文件 | 内容 |
| --- | --- |
| `assets.json` | 人物、场景、道具、关键特效、状态、制作需求及来源证据 |
| `screenplay-asset-table.xlsx` | 同一 JSON 的工作簿视图，固定包含人物、场景、道具、场次总表四张核心表；存在关键特效时才增加特效表 |
| `asset_findings.json` | 结构化业务疑点及来源证据 |
| `asset_findings.md` | 供人工阅读的独立疑点报告 |

同一资产的多个状态可能对应多条 Excel 数据行，因此工作表行数不等于资产唯一数量。`work.json` 是本次提取的中间文件，不属于四个正式交付物。输入契约见 [capabilities.json](capabilities.json) 和 [work-contract.md](references/work-contract.md)。

## 安装到 Codex

团队成员接受仓库邀请，并确认本机 Git 可以读取仓库后，执行：

```sh
codex plugin marketplace add https://github.com/kaibaoxiang-studio/script-plugins.git --ref v1.0.0
codex plugin add screenplay-asset-extractor@script-plugins
```

在新聊天中选择「剧本资产表提取」，提供一级 `standardized_screenplay.json`，或明确调用 `$extract-asset-table`。完整安装说明见[项目安装文档](https://github.com/kaibaoxiang-studio/script-plugins/blob/v1.0.0/docs/installation.md)。

## 独立目录与命令行

需要 Python 3.12+；调用 Agent 能力还需要已登录且可用的 Codex CLI。在包含本 README 和 `harness.py` 的插件根目录执行：

```sh
python3.12 scripts/bootstrap.py --install
```

将最后返回 JSON 中的 `python` 路径填入下例：

```sh
runtime_python="/absolute/path/returned/python"
"$runtime_python" harness.py doctor
"$runtime_python" harness.py validate
```

准备 `inputs.json`，将来源路径换成一级完成稿的绝对路径：

```json
{"source_path":"/absolute/path/standardized_screenplay.json"}
```

```sh
"$runtime_python" harness.py run-capability \
  --capability extract-asset-table \
  --inputs /absolute/path/inputs.json \
  --workspace /absolute/path/asset-work --confirmed
```

运行结果中的 `artifacts` 指向实际四个交付文件，运行记录保存在指定 workspace 中。Agent 先读取保守底稿，再依据原文补充资产判断并运行导出校验；单独执行 `prepare` / `finalize` 不会自动完成语义提取。结构、证据、状态或场次引用无效会阻止导出；来源文件变化后应重新开始。更多运行约束见 [RUNTIME.md](RUNTIME.md)。

## 验证范围与维护

现有确定性验收脚本通过，覆盖合法别名、换装状态、主要动物、群演、生成来源、工作簿一致性，以及错误引用和无依据外观事实的拒绝。另有真实合成调用、三份长稿整稿结构验收及各前两集真实提取。全剧业务案例交付 28 场、22 人物、17 场景、26 道具、0 单列特效和 3 条疑点；来源、结构与工作簿复核通过。

结构和数量通过不能代替人工语义核定。三份长稿未逐集完成人工资产核定；身份、场景归并、道具与特效的制作必要性及遗漏仍需结合独立报告审阅。范围见 [VALIDATION.md](VALIDATION.md) 和[项目验证记录](https://github.com/kaibaoxiang-studio/script-plugins/blob/v1.0.0/docs/validation-v1.0.md)。

蓝图生成器和测试位于仓库的 [creator-src](https://github.com/kaibaoxiang-studio/script-plugins/tree/v1.0.0/level-2/asset-extraction/creator-src)，不属于独立包运行依赖。本 README 由其中的 `PLUGIN-README.md` 维护并写入构建蓝图。来源与许可见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
