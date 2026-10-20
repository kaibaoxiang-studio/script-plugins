# 剧本插件

开宝箱工作室四人共建项目。一级剧本标准化已提供独立插件；其余环节仍处于能力归档与接口讨论阶段，尚未形成从任意剧本自动产出全部表格的完整流程。

## 当前状态（2026-10-20）

| 环节 | 仓库目录 | 当前可用内容 | 尚未完成 |
| --- | --- | --- | --- |
| 一级：剧本标准化 | [01-screenplay-standardization](capabilities/01-screenplay-standardization/README.md) | 独立插件；DOCX/TXT/Markdown 到可追溯的剧本 JSON、Markdown 和独立审查报告 | 与后续级别的接口联调；复杂改写及深审需 Agent 复核 |
| 二级：场记表 | [02-scene-log](capabilities/02-scene-log/README.md) | 剧本拆解 Skill 原始快照；基础场景索引 CSV 导出 | 团队定义的完整场记表字段和逐场验收 |
| 三级 A：资产表 | [03-asset-table](capabilities/03-asset-table/README.md) | 概念设计 Skill 原始快照；已有资产目录的 CSV 导出 | 从场记表直接提取的完整制作资产表 |
| 三级 B：节拍表 | [04-beat-table](capabilities/04-beat-table/README.md) | 节拍分析规则；已有拆解结果的 CSV 导出 | 从场记表独立生成节拍、人工复核流程 |
| 跨环节主控 | [05-orchestration](capabilities/05-orchestration/README.md) | Skill Orchestrator V2 原始快照及接口/运行代码 | 本项目的节点 DAG、交接绑定和端到端运行 |

现有流程设想见[结构图](docs/剧本插件结构图.png)及其 [Mermaid 图源](docs/剧本插件结构图.mmd)。它表示目标交接关系，不代表表中所有节点已实现。

## 现在可以怎样试用

上游剧本解析/拆解代码需要 Python 3.12+；本机系统默认的 Python 3.9 不适用。使用前先确认解释器版本。若没有 python3.12 命令，可用 Codex 桌面版提供的 bundled Python 路径替换下文命令中的解释器。

1. 在 Codex 选择 `@剧本标准化`（`screenplay-standardizer@screenplay-standardizer-local`）处理 DOCX、TXT 或 Markdown，得到标准剧本 JSON/Markdown 与疑点报告。旧解析器仍可处理 Fountain/FDX 并输出场景映射。
2. 使用 02 的导出器得到**基础场景索引**；它不等于正式场记表。
3. 如果已有通过校验的完整 screenplay_breakdown_v1，03 可生成 AssetCatalogV1 并导出目录表，04 可导出其中的节拍。

各目录的 README 写有命令、输入要求和已知边界。当前不应把四个目录串联后声称“无损标准化—场记—资产/节拍”已经跑通。

## 验证

使用 Python 3.12+，从仓库根目录运行：

    python3.12 -m unittest discover -s capabilities/02-scene-log/ai-script-breakdown/tests -v
    python3.12 -m unittest discover -s capabilities/01-screenplay-standardization/creator-src/tests -v
    python3.12 -m unittest discover -s tests -v

## 来源与协作

所收录的上游能力来自 Skill Orchestrator 仓库固定提交，详见[来源说明](capabilities/UPSTREAM.md)及[MIT 许可证](capabilities/UPSTREAM-LICENSE.txt)。SN2S 的本地下载包仅做适配评估，未复制其代码或文档。

本次归档由 [Issue #1](https://github.com/kaibaoxiang-studio/script-plugins/issues/1) 跟踪。新需求先讨论输入、输出、负责人和验收标准，再通过 Issue、分支与 Pull Request 合入；参见[贡献指南](CONTRIBUTING.md)。剧本及人物设定等素材请先确认共享权限。

## 成员加入

请工作室管理员邀请你的 GitHub 账号加入组织，并为你开放本仓库权限。获得权限后即可查看 Issue、提出方案和提交 Pull Request。
