---
name: scene-log-extractor
description: "从一级标准化剧本提取可追溯场记表与审查报告"
---

# scene-log-extractor

增量优化 ai-continuity-sheet 并交付可独立安装的场记表提取插件

Match the request to a capability below. Read its SKILL.md and relevant references. Ask only for missing consequential inputs; preserve established decisions. Run Python-backed capabilities through the bundled harness. Use the workspace selected by the user and report actual artifacts and remaining failures.

- `$ai-continuity-sheet`: 从一级标准化 JSON 一次提取整剧场记表与审查报告
- `$segment-scene`: 按文本证据将一场剧本切成连续叙事拍
- `$enrich-scene`: 沿用七个辅助 Skill 为每拍提供待审制作建议
- `$assemble-scene-log`: 校验来源覆盖并生成整剧 JSON 与 13 列工作簿
- `$review-continuity`: 整剧人物与道具连续性疑点复核
- `$finalize-scene-log`: 合并疑点报告并发布四个交付物

See [runtime instructions](../../RUNTIME.md).
