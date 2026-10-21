# 场记表提取｜二级插件

场记表提取与[剧本资产表提取](../asset-extraction/README.md)是并列的二级能力，均读取一级「剧本标准化」交付的 `standardized_screenplay_v1` JSON。场记表承担叙事分拍及逐拍制作信息整理：**一个 P 对应一个叙事拍**，不另设三级节拍插件。场记表与资产表各自从一级输入提取，不要求先运行另一项二级能力。

本目录收录团队源仓库 [kaibaoxiang-studio/ai-continuity-sheet](https://github.com/kaibaoxiang-studio/ai-continuity-sheet) 的固定快照，提交为 [`3724a23`](https://github.com/kaibaoxiang-studio/ai-continuity-sheet/tree/3724a2333ad93aadd8554d54e09155c80d8be54e)。可安装插件 `scene-log-extractor` 当前版本为 **0.1.0**；「剧本插件 1.0」表示这套一级、二级能力的整合发布版本。团队仍可在源仓库维护场记能力，后续同步需记录来源版本。

## 输入、分拍与来源边界

- 必填：一级标准化 JSON，其中须包含分集、场景、正文块及来源位置。缺少这些内容时提示补全上游，不能从空细纲直接编造场记表。
- 默认一次处理整剧，也可指定集数重跑。模型、画幅、灯光偏好为可选参数，默认保持平台中立。
- 使用 `EPxx + SCxx + Pxx` 定位；`SC` 跨集连续编号，`P` 每场从 `P01` 重新开始。分拍依据人物目标、行动、反应或信息变化，相邻原文单元可以合并为一拍。
- 每个正文单元必须保持原顺序、恰好覆盖一次。遗漏、重复、顺序变化或建议条数与分拍不一致时，确定性校验会报错。
- 台词从一级原文提取，保留完整对白、OS/VO、双语顺序和来源位置。一级标记为 `generated` 的正文继续保留生成来源，并进入审查报告。
- 摄影、灯光、微表情、动作表演、剧情概括和时长均为 `pending` 待审建议。连续性疑点单独报告，不自动修改一级剧本。

## 四个交付物

| 文件 | 内容 |
| --- | --- |
| `scene_log.json` | `scene_log_v1`：集、场、拍、原文单元、来源位置、完整对白、建议与时长依据 |
| `scene_log.xlsx` | 每集一个工作表；页首放该集一级标准化剧本正文，随后为 13 列场记表；长正文分为连续合并行 |
| `scene_log_report.json` | `scene_log_report_v1`：覆盖数量、生成来源、不确定项和有文本依据的连续性疑点 |
| `scene_log_report.md` | 供团队阅读的独立审查报告 |

13 列保持原团队表格结构，JSON 中另外保存分拍理由、来源和建议状态：

| 集数 | 场次 | 片段 | 出场人物 | 场景 | 道具 | 摄影 | 灯光/色卡 | 台词 | 时长 | 微表情情绪指导 | 动作表演指导 | 剧情大纲 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

## 安装与运行

按[仓库安装说明](../../docs/installation.md)安装「场记表提取」。插件包位于 [scene-log-extractor/](scene-log-extractor/)，包含自己的运行时、锁定依赖、Skill 和知识快照，运行时无需安装 Harness Creator 或源仓库旧版外部业务 Skill。

在本目录执行以下命令；`python` 应替换为安装说明中准备好的 Python 3.12+ 环境。输入文件和运行目录由使用者指定：

```sh
python scene-log-extractor/scripts/run_scene_log.py \
  --source standardized_screenplay.json \
  --workspace scene-log-work \
  --output scene-log-output
```

加 `--episodes 2,3` 只处理第 2、3 集。续跑时保留同一 `--workspace`，使用返回的运行编号：

```sh
python scene-log-extractor/scripts/run_scene_log.py \
  --workspace scene-log-work \
  --output scene-log-output \
  --resume run-运行编号
```

续跑要求输入文件和插件版本保持一致。公开能力入口为 `extract-scene-log`，主 Skill 为包内 [`ai-continuity-sheet`](scene-log-extractor/skills/ai-continuity-sheet/SKILL.md)。历史 Markdown 表格仍可用 [`convert_continuity_sheet.py`](ai-continuity-sheet/scripts/convert_continuity_sheet.py) 转换为 Excel；新流程直接从结构化 JSON 生成工作簿。

## 源码与构建目录

| 位置 | 维护职责 |
| --- | --- |
| [ai-continuity-sheet/SKILL.md](ai-continuity-sheet/SKILL.md) 与 [scripts/](ai-continuity-sheet/scripts/) | 主 Skill、原文映射、覆盖校验、工作簿与报告生成及整剧运行入口 |
| [cinematography-advisor/](cinematography-advisor/)、[lighting-colorist/](lighting-colorist/)、[dialogue-formatter/](dialogue-formatter/)、[shot-duration-calculator/](shot-duration-calculator/)、[micro-expression-director/](micro-expression-director/)、[action-performance-director/](action-performance-director/)、[scene-synopsis/](scene-synopsis/) | 七个辅助 Skill 及各自 references：摄影、灯光、台词、时长、微表情、动作和剧情概括 |
| [creator-src/](creator-src/) | 蓝图生成、构建补丁、本地安装发布脚本、合成样例、自动化测试及验收记录 |
| [scene-log-extractor/](scene-log-extractor/) | 独立安装与运行的构建结果；6 个能力、14 个 Skill、包内 Harness runtime、锁定依赖和来源记录 |

维护时先更新源码，再构建独立插件并验收，避免仅修改安装缓存。构建命令与已验收范围见 [creator-src/VALIDATION.md](creator-src/VALIDATION.md)。原仓库改造基线、替代旧外部依赖的方法见包内[来源与改造说明](scene-log-extractor/references/source-adaptation.md)。

## 测试结果与当前边界

以下结果来自既有真实调用、测试聊天和本次对现存产物的复核。仓库保留合成样例、测试代码及指标；真实用户剧本、业务产物和运行日志不随发布上传。

| 检查 | 已有结果与本次复核 |
| --- | --- |
| 结构与运行环境 | 本次 `doctor`、`validate` 通过：Python 3.12.14、Codex CLI 0.163.0-alpha.10.2，6 个能力、14 个 Skill、0 结构错误 |
| 确定性自动化测试 | 本次重跑 [6 项 unittest](creator-src/tests/test_scene_log_core.py) 全通过；覆盖原文与双语 OS、跨集编号、一拍一行、长正文、缺正文、漏拍/重复、无依据人物、上游未映射来源及动作引号分句 |
| 一级样稿真实整剧调用 | 已完成 1 集、2 场、6 拍，四个文件齐全 |
| 跨集连续性真实调用 | 已完成 2 集、2 场、4 拍；发现疑似错名、道具状态承接缺口和动作喊话但对白块缺失，明示改名未误报；本次产物交叉复核通过 |
| 公开能力指定集调用 | `extract-scene-log` 指定第 2 集成功，只交付该集 1 场、3 拍 |
| 最终候选包真实调用 | 已完成 1 集、1 场、3 拍，四个文件齐全；本次产物交叉复核通过。预发布包另有独立解包真实调用记录，最终 ZIP 独立解包的 `doctor`、`validate` 通过 |
| 第 1–2 集业务测试 | 交付 2 集、5 场、28 拍，EP01/EP02 两个工作表、各 13 列；本次 [verify_artifacts.py](creator-src/verify_artifacts.py) 复核 110 个原文单元、43 段对白及 JSON/Excel/一级正文对应关系通过 |

业务测试经过复核，并补记了 3 处动作或道具细节。最终仍有 **31 条待核提示**：9 条一级格式来源提示（如音效、闪回标记的格式规范内容）及 22 条制作不确定项；140 条制作建议和 28 条时长保持待审。这些结果表示当前样例交付经过校验与修订，不能推定为所有输入都能一次自动生成且无需修改。

同一已完成运行的 `--resume` 再交付四个文件已验证；执行中的强制断电或强制终止恢复尚未验证。旧 Markdown 转 Excel 兼容路径已有成功记录。本次未重新发起真实模型生成，只重跑结构检查、现有确定性测试及现存产物交叉校验。详细记录见 [VALIDATION.md](creator-src/VALIDATION.md)；模型制作建议和连续性判断仍需团队审查。
