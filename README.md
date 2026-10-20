# 剧本插件

开宝箱工作室的团队共建项目。`@Harness Creator` 和 `@剧本标准化` 已更新；团队成员也已在独立仓库上传场记表能力。以下区分已有内容与尚未完成的接口，避免把目标流程误写成已跑通。

## 当前已更新

| 插件 | 当前状态 | 位置 |
| --- | --- | --- |
| `@Harness Creator` | 已更新，用于建设和维护插件 | 独立的本地项目；源码尚未收录到本仓库 |
| `@剧本标准化` | 已更新，可处理剧本标准化与独立审查 | [剧本标准化插件](https://github.com/kaibaoxiang-studio/script-plugins/tree/codex/screenplay-standardizer-plugin/capabilities/01-screenplay-standardization/screenplay-standardizer)；目前位于开发分支，尚未合入 `main` |

## 当前框架：一级与二级产物

| 层级与产物 | 定义 | 当前状态 |
| --- | --- | --- |
| 一级：标准化剧本 | 从原始剧本生成可追溯的标准格式，保留原文依据 | `@剧本标准化` 已更新；与二级能力的接口待对齐 |
| 二级：场记表（目标包含节拍） | 按场次、片段组织场记信息与节拍线索 | [ai-continuity-sheet](https://github.com/kaibaoxiang-studio/ai-continuity-sheet) 已由团队成员上传至独立仓库；现有实现以纯剧本为输入，按片段生成 13 列 Excel 场记表。与一级标准化输出的衔接、节拍字段及团队验收尚待对齐 |
| 二级：资产表 | 与场记表并列；以标准化剧本中的原文为依据提炼资产，场记线索可辅助核对 | 正式能力待上传 |

节拍归入场记表，不再设独立节拍表；当前框架没有三级产物。现有场记表的 13 列中尚无单独的节拍列，不能将“目标包含节拍”理解为该字段已经交付。

本仓库的 [02-scene-log](capabilities/02-scene-log/README.md) 仍保存早期场景索引与参考材料；[03-asset-table](capabilities/03-asset-table/README.md)、[04-beat-table](capabilities/04-beat-table/README.md)、[05-orchestration](capabilities/05-orchestration/README.md) 也有早期归档或试验代码。目录存在不代表对应正式插件已接入当前流程；其中 `04-beat-table` 是旧规划资料。

## 团队协作

新需求先讨论输入、输出、负责人和验收标准，再通过 Issue、分支与 Pull Request 提交。协作方式见[贡献指南](CONTRIBUTING.md)。剧本及人物设定等素材上传前，请确认团队拥有共享权限。
