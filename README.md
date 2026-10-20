# 剧本插件

开宝箱工作室的团队共建项目。当前框架只有一级和二级产物；下表区分已更新的插件、已上传的场记表能力和仍待上传的部分。

## 当前能力

| 能力 | 状态 | 位置 |
| --- | --- | --- |
| `@Harness Creator` | 已更新，用于建设和维护插件 | 独立的本地项目，尚未收录到本仓库 |
| `@剧本标准化` | 已更新，负责标准化与独立审查 | [剧本标准化插件](https://github.com/kaibaoxiang-studio/script-plugins/tree/codex/screenplay-standardizer-plugin/capabilities/01-screenplay-standardization/screenplay-standardizer)，目前在开发分支，尚未合入 `main` |
| 场记表能力 | 团队成员已上传；与一级能力的接口待对齐 | [ai-continuity-sheet](https://github.com/kaibaoxiang-studio/ai-continuity-sheet) 独立仓库 |

## 一级与二级产物

| 层级 | 产物与定义 | 当前状态 |
| --- | --- | --- |
| 一级 | 标准化剧本：保留原文依据，生成可追溯的标准格式 | `@剧本标准化` 已更新；二级接口待对齐 |
| 二级 | 场记表（目标包含节拍）：按场次、片段组织场记与节拍线索 | 已上传的能力以纯剧本为输入，按片段生成 13 列 Excel；尚未接入标准化剧本，13 列中也没有独立节拍字段。详见[场记表说明](https://github.com/kaibaoxiang-studio/script-plugins/blob/codex/screenplay-standardizer-plugin/capabilities/02-scene-log/README.md) |
| 二级 | 资产表：与场记表并列，以标准化剧本中的原文为依据提炼资产，场记线索可辅助核对 | 正式能力待上传 |

节拍归入场记表，不再设独立节拍表；当前框架没有三级产物。开发分支中的其他能力目录是早期归档、参考资料或试验代码，不代表正式插件已经交付。

## 团队协作

新需求先讨论输入、输出、负责人和验收标准，再通过 Issue、分支与 Pull Request 提交。协作方式见[贡献指南](CONTRIBUTING.md)。剧本及人物设定等素材上传前，请确认团队拥有共享权限。
