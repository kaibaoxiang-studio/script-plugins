# 场记表提取｜scene-log-extractor 0.1.0

这是「剧本插件 1.0」中的二级场记表插件，与资产表提取并列。输入必须是一级「剧本标准化」产出的 `standardized_screenplay_v1` JSON，包含分集、场景、正文块和来源位置。插件按集、场、叙事拍整理场记表，**一个 P 对应一个叙事拍**；默认处理整剧，也支持指定集数。

## 交付内容

| 文件 | 内容 |
| --- | --- |
| `scene_log.json` | 可追溯的集、场、拍、原文单元、完整对白、制作建议和时长依据 |
| `scene_log.xlsx` | 每集一个工作表，顶部保留一级标准化剧本正文，下方为 13 列场记表 |
| `scene_log_report.json` | 结构化生成来源、不确定项及连续性疑点 |
| `scene_log_report.md` | 供人工阅读的独立审查报告 |

13 列为：**集数、场次、片段、出场人物、场景、道具、摄影、灯光/色卡、台词、时长、微表情情绪指导、动作表演指导、剧情大纲**。

原文单元须按顺序恰好覆盖一次，台词保留原文、OS/VO 与双语顺序。摄影、灯光、表演、剧情概括和时长均以 `pending` 保存，须经人工审查。报告不会自动修改一级剧本。

## 准备运行环境

需要 Python 3.12+、已配置好模型调用的 Codex CLI，以及本包锁定的 Python 依赖。解压后进入包含本 README 和 `harness.py` 的 `scene-log-extractor` 目录，运行：

```sh
python3.12 scripts/bootstrap.py --install
```

命令会安装锁定依赖，并在最后的 JSON 中返回 `status: ready` 和 `python` 解释器路径。**下文的 `python` 请替换为该路径**；路径含空格时加引号。

```sh
python harness.py doctor
python harness.py validate --plugin .
```

确认 `python_supported` 为 `true`、检测到 Codex CLI，且插件 `valid` 为 `true`。运行说明与运行时约束见 [RUNTIME.md](RUNTIME.md)。

## 从一级 JSON 提取

在插件目录运行，输入和输出位置可按自己的项目调整：

```sh
python scripts/run_scene_log.py \
  --source standardized_screenplay.json \
  --workspace scene-log-work \
  --output scene-log-output
```

加 `--episodes 2,3` 只处理第 2、3 集；`--model`、`--aspect-ratio`、`--lighting-preference` 为可选制作偏好。输入中缺少正文或来源位置时，应先补全一级输出。

续跑时保留同一运行目录，并填写上次返回的 `run_id`：

```sh
python scripts/run_scene_log.py \
  --workspace scene-log-work \
  --output scene-log-output \
  --resume run-运行编号
```

输入文件或插件内容变化后不能沿用旧运行状态。已完成运行的续用交付已验证；执行中强制断电恢复尚未验证。模型生成的建议和连续性判断仍需人工复核。

## 包内入口与来源

- 主 Skill：[ai-continuity-sheet](skills/ai-continuity-sheet/SKILL.md)，公开能力名为 `extract-scene-log`。
- 运行命令：[run_scene_log.py](scripts/run_scene_log.py)；历史 Markdown 转 Excel：[convert_continuity_sheet.py](scripts/convert_continuity_sheet.py)。
- 来源说明：[source-adaptation.md](references/source-adaptation.md)；第三方声明：[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
- 整合仓库与完整安装、测试说明：[kaibaoxiang-studio/script-plugins](https://github.com/kaibaoxiang-studio/script-plugins)。
- 维护源码快照：[kaibaoxiang-studio/ai-continuity-sheet @ 3724a23](https://github.com/kaibaoxiang-studio/ai-continuity-sheet/tree/3724a2333ad93aadd8554d54e09155c80d8be54e)。

本包自带运行时、辅助 Skill 及知识快照，独立运行无需安装 Harness Creator。
