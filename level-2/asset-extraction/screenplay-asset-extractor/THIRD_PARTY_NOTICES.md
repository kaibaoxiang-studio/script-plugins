# 第三方来源

- 插件携带的 Harness Creator 0.1.0 运行时借鉴并改写 Bird's Nest / Skill Orchestrator 的事件存储、DAG 调度与 App Server 客户端；上游提交 `3f5a5f348c2f71b3c5c046128e0c679089ab801a`，MIT 许可见 `licenses/Bird-s-Nest-MIT.txt`。本资产插件未收录 Grill Me Skill。
- Skill 编写方法参考本机 OpenAI Skill Creator 的指导原则；其 Apache-2.0 许可见 `licenses/skill-creator-Apache-2.0.txt`。本资产插件运行时不调用该 Skill。
- Python 第三方依赖版本与发行文件哈希见 `requirements.lock`，安装时应保留各库自身许可证。
- 仓库旧 `script-asset-extractor` 提供业务流程与四表结构的迁移依据；新插件独立实现 JSON 输入、证据校验和导出，来源修订记录见 `sources.lock.json`。
