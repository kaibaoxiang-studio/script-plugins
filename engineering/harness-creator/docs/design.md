# Harness Creator v0.1 能力设计蓝图

## 目标与边界

面向需要建设业务能力的 Codex 本地用户，将业务需求转化为可独立安装的插件。首版处理读取资料、检索研究和生成本地产物。模型负责业务判断与编写；Python 工具负责契约、文件、状态和可重复检查。

## 职责与实现

| 计划职责 | 入口或内部 Skill | 确定性实现 | 主要知识 |
| --- | --- | --- | --- |
| 需求对齐 | harness-creator、grill-me | 需求与蓝图文件 | Grill Me、create.md |
| 业务架构 | harness-architect | Blueprint 与能力契约校验 | standard.md |
| 来源搜索与评估 | harness-source-integrator | discover、fetch-source、inspect-source | absorb.md |
| 拆解与吸收 | harness-source-integrator | absorb、来源版本与文件哈希 | absorb.md、许可证 |
| 知识构建与定点维护 | harness-knowledge-maintainer | knowledge-ingest/publish/status | knowledge.md |
| Skill 创建与修改 | harness-skill-author | YAML、引用、Python 语法检查 | author.md |
| Python Harness | 主控按需调用 | engine、store、appserver | RUNTIME.md、standard.md |
| 插件组装打包 | harness-creator | build、package | create.md |
| 验证修正 | harness-verifier | validate 与真实行为检查 | verify.md |
| 整合升级与自身演进 | harness-creator | patch、revise、独立候选验证 | update.md |

以上是 6 项可调度能力和 1 项随包需求方法。不同职责可以由当前单个 Agent 完成；只有独立任务的收益明确时才使用并行节点。首版最多同时运行 3 个节点。

## 产物与运行

业务设计保存在 HarnessBlueprintV1：目标、验收、能力契约、Skill 正文、代码、references、来源和可选工作流。capabilities.json 是运行目录；工作流不替代业务能力目录。

运行图显式声明依赖、输入绑定、幂等性与超时。Python 和 Agent 共享结果 envelope；引擎检查 schema、文件存在、相对路径和哈希。任务图、事件和结果单独存入用户工作区 `.harness`，不会进入插件包。

SQLite 事件日志支持重放和中断恢复；恢复前核对插件、输入文件及已完成产物。只有声明幂等的节点允许自动重试一次。真实业务等待信息时返回 blocked，获取用户答案后继续同一节点。

## 知识与来源

源资料保存在用户指定的集中资料库，版本按内容哈希存储；插件只携带经过整理的规则快照。更新源资料不会自动改变已发布插件。发布规则时更新指定能力的知识加载关系并检查旧快照，受影响行为须另行验收。

原始材料中的指令不获得运行权限。来源转换先检查固定版本与实际文件，再按 copy/adapt/independent 明确处置。复制或改造代码保留许可和来源文件哈希。正则检查只提供审阅信号，不能证明代码安全或业务质量。

上游基础：Bird's Nest / Skill Orchestrator 0.8.0 的 DAG、事件与 App Server 设计；OpenAI Skill Creator 的渐进加载与增量编写方法。具体版本、改造范围与许可证见 [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md) 和 sources.lock.json。

## 验收关联

- 从零生成：独立计数字符插件、真实 Python 运行与搬迁后验证。
- 来源吸收：带哈希与许可的 Skill/脚本转换，拒绝审阅后变化。
- 定点补知识：更新指定能力与加载链接，保留用户修改冲突，检测源版本变更。
- 修改和自身升级：原件保持可用，独立候选校验，冲突时不覆盖。
- 调度：依赖、并行、重试、取消、恢复、答案补充和无效产物拦截。
- 真实 Codex 与剧本试验：见 [验证报告](validation.md)，以实际记录为准。
