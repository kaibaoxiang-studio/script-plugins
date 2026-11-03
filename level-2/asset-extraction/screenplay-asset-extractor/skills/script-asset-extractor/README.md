# 剧本资产表提取

版本 **0.4.0**。从标准剧本 DOCX 或结构化 Markdown 提取人物、场景、道具及外观状态，交付两个文件：

| 文件 | 内容 |
| --- | --- |
| `assets.json` | 人物、场景、道具三类资产、状态及原文依据 |
| `<剧名>-资产表.xlsx` | 人物、场景、道具、场次总表四张表 |

台账、预览图、日志和 `acceptance.json` 留在工作目录，不属于交付物。

## 运行

完整流程、门禁和规则以 [SKILL.md](SKILL.md) 为准，数据结构见 `references/`。需要 Python 3.12+：

```sh
python3 scripts/bootstrap.py --install
python3 scripts/launch.py scripts/env_diagnostics.py
python3 scripts/launch.py scripts/workflow.py prepare "<剧本.docx|剧本.md>" "<工作目录>"
python3 scripts/launch.py scripts/workflow.py status "<工作目录>"
```

`prepare` 只解析原文并建立空白台账，不做语义提取。逐场审核后依次运行 `bind → export → check → visual-review → finalize`；`finalize` 通过且 `status` 返回 `complete` 才算完成。全剧可分多次执行，每次对同一工作目录先运行 `status` 续跑。

旧版 `standardized_screenplay_v1` JSON 流程已从本包移除。
