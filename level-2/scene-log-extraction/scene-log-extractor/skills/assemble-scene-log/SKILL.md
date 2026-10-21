---
name: assemble-scene-log
description: "校验来源覆盖并生成整剧 JSON 与 13 列工作簿"
---

从逐场结果校验全部正文单元顺序与建议对应关系，确定性组合集场拍与原文台词，写 scene_log.json 和 scene_log.xlsx。遇到任何遗漏或重复必须失败并指出场次，不静默丢弃。
