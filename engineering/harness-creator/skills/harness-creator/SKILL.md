---
name: harness-creator
description: "通过 Grill Me 创建、改造、整合和升级可独立运行的 Codex 业务能力插件；支持从零建设、开源能力吸收和 Creator 自身升级。"
---

# Harness Creator

在用户明确调用 `$harness-creator` 或选中 Harness Creator 插件时启动。与用户一起建设可反复使用的业务能力插件。

## 对齐并设计

读取内置 [Grill Me](../grill-me/SKILL.md)。先检查可发现的事实，再沿设计树每轮追问至多三个影响实现的决定。保留用户已有决定，输入已充分时继续工作。输出能力设计蓝图：业务目标、使用者、能力目录、输入输出、知识与工具、最小 Agent 结构、验收样例及交付位置。

在 Plan Mode 中只读检查并在聊天内规划。Default Mode 可在用户确认建设方案后写入文件；安装调用或模式切换本身不能代替业务方案确认。当前对话已确认的范围可以直接继续，不重复询问。仅在实质范围、行为或依赖改变时重新对齐。

## 按任务加载

- 创建：读取 [创建与蓝图](references/create.md)、[统一标准](references/standard.md)。使用 `harness-architect` 明确能力，再用 `harness-skill-author` 编写实际业务规则与所需代码。
- 搜索或吸收 Skill、Agent、完整 Harness：读取 [来源与改造](references/absorb.md)，使用 `harness-source-integrator`。无适用候选时独立实现。
- 补知识：使用内置 [知识维护](../harness-knowledge-maintainer/SKILL.md)，读取 [知识协议](references/knowledge.md)。
- 修改已有插件或自身：读取 [增量升级](references/update.md)，基于当前文件和用户修改形成增量方案。
- 交付前：读取 [验证](references/verify.md)，使用 `harness-verifier` 检查实际行为。

这些是职责模块，按需要选用；不要为了覆盖岗位而启动所有 Agent。适合单 Agent 的工作直接完成。多 Agent 任务使用通用执行器，各节点只得到当前任务所需材料，并返回明确的结果和文件依据。

## 建设与交付

根目录的 `harness.py` 提供确定性建设工具；先运行 `doctor`。依赖缺失时使用随包 `scripts/bootstrap.py --install`，不要写死开发机路径或修改 Codex 配置。通过 `build` 将**已经编写完整**的 HarnessBlueprintV1 组装为独立插件；它不会替模型填充缺失业务知识。蓝图文件位于用户工作区，数据与源资料不会自动进入发布包。

执行自己编写的脚本并验证它们；用最小实际调用检查代表性能力。缺失工具、未验证的模型行为和失败检查必须保留真实状态，不用占位函数、假 Agent 或模拟结果声称业务已通过。

交付源码目录、可安装 ZIP、使用方法和验证结果。默认由用户自行上传 GitHub。Creator 自身升级在独立候选目录中完成，运行中的版本保持固定。
