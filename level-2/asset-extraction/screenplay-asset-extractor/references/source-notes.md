# 来源与适配

- 仓库 `origin/codex/capability-bundle` 的 `8ba6de3561f85c5a0af6cc46ca68c23fba8b5917` 提供旧 `script-asset-extractor`。保留分批阅读、人物状态双向校验、主子场景和四表导出的做法；新插件独立实现 JSON 读取、证据追溯和校验。旧 DOCX 解析器仍留在仓库作迁移对照，不进入插件运行路径。
- 一级 `screenplay-standardizer` 的 `standardized_screenplay_v1` 是唯一正式输入契约。其 `episodes/scenes/blocks`、`source_refs`、`origin` 和 `coverage` 决定可追溯范围。
- Skill Orchestrator 0.8.0 的 Evidence Guardian 提示区分剧本事实、保守推断、已批准的创作决定与偏好；人物、场景、道具设计岗位提示识别下游制作视角。插件仅吸收证据边界，不复制岗位提示词或调用私有运行时。
- “镜头执行图参考.jpeg”显示同一角色的正面头像、侧面头像、正面全身和背面全身。该图仅用于定义制作需求字段，不打包进插件。
