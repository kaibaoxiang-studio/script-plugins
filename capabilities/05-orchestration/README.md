# 05｜跨环节主控

**当前状态：上游主控 Skill 已收录；本项目 DAG 尚未建立。**

[skill-orchestrator](skill-orchestrator/SKILL.md) 是上游 Skill Orchestrator V2 快照，包含需求契约、类型化 DAG、节点绑定、并发调度、事件记录与恢复机制。关键接口见 [interfaces.md](skill-orchestrator/references/interfaces.md)，运行代码见 [orchestrator_runtime.py](skill-orchestrator/scripts/orchestrator_runtime.py)。

上游主控有显式调用、依赖安装、用户确认和副作用门槛，且已注册的语义类型不等于本项目的四个交接物。当前没有定义“标准化剧本 → 场记表 → 资产表/节拍表”的 ExecutionGraphV2，也没有完成节点绑定。复制快照不会在 Codex 中自动安装或执行这个 Skill。

下一步应在正式表结构确定后，为四个节点登记输入输出 schema、验收器、失败处理和并行依赖。
