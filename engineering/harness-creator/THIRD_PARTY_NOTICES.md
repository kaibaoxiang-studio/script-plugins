# 上游来源

- Bird's Nest / Skill Orchestrator 0.8.0，eggshrt/Bird-s-Nest，提交 `3f5a5f348c2f71b3c5c046128e0c679089ab801a`，MIT。Grill Me 原样收录；运行时借鉴并重写其事件存储、DAG 调度和 App Server 客户端，移除剧本/单资产耦合并增加通用能力执行、文件校验和建设工具。许可见 licenses/Bird-s-Nest-MIT.txt。
- OpenAI Skill Creator，本机随 Codex 提供的版本，Apache-2.0。Skill 编写与增量维护规范参考其指导原则，未将系统 Skill 作为运行依赖。许可见 licenses/skill-creator-Apache-2.0.txt。
- DevExpert Harness Starter，`devexpert-io/harness-starter`，提交 `18b19e61df839f5d8bb9ecb6cce7941437214977`，MIT。研究其按功能切片、实施规格、独立验收与证据状态的方法；v0.2 的交付协议、Schema 和 Python 校验代码为按 Creator 现有架构独立编写，未复制其 Skill 或安装脚本。
- Python 第三方库版本与发行文件哈希见 requirements.lock；安装时保留各库自身的许可证。

生成插件默认携带此说明和上游许可。额外吸收的开源代码由 sources.lock.json 和相应 licenses 文件单独记录。
