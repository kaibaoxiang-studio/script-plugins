# Harness Creator

通过 Grill Me 对齐业务，创建、改造和维护可独立运行的 Codex 能力插件。

**v0.1.0** 面向 Codex 本地环境。它内置需求对齐、业务架构、来源搜索与拆解、Skill 编写、知识维护、Python Harness、插件打包及验证工具。生成物可以独立安装，采用 Agent Skills、Python 调度器和 Codex App Server。

## 使用

安装后在新聊天中选中 **Harness Creator**，或调用：

```text
$harness-creator 我想建设一套服务剧本业务的基础插件。
请先检查我的资料，通过 Grill Me 与我确定能力、输入输出和验收，
再建设可独立使用的业务插件。
```

```text
$harness-creator 请研究这个开源 Skill / Agent / Harness。
先拆解实际代码、知识和依赖，集中说明采纳与改造方案，
将适用部分转换成我们的标准并验证。
```

```text
$harness-knowledge-maintainer 请把这份资料中有关节拍划分的规则，
补充到指定插件的对应能力，保留来源并验证受影响的行为。
```

入口 `harness-creator` 只在明确调用时启动。内部架构、来源整合、Skill 编写和验证职责按任务需要使用；知识维护可单独调用。Grill Me 已随包提供，不依赖用户安装的其他业务 Skills。

## 技术与维护

Python 3.12+，依赖固定版本的 jsonschema、PyYAML 及其传递依赖；哈希锁定安装见 [RUNTIME.md](RUNTIME.md)。模型使用当前 Codex 配置。

- `harness.py build`：将**已经编写完整**的业务能力蓝图组装成独立插件。
- `discover / fetch-source / inspect-source / absorb`：搜索、固定版本获取、代码检查和显式内容整合。
- `knowledge-ingest / knowledge-publish / knowledge-status`：集中源库与指定能力知识快照。
- `patch / revise`：带当前文件哈希的定点修改，以及保留用户修改的独立版本候选。
- `run / run-capability / resume / cancel / replay`：实际能力调用与本地恢复。
- `validate / package / doctor`：结构检查、打包和环境检查。

语义判断、业务设计和代码改造由 Codex 按内置 Skills 完成；确定性命令处理文件、契约、调度和验证。`build` 本身不从一句话自动发明业务实现。

原文源库、运行数据和生成过程文件保存在用户工作区；插件分发只带需要的规则快照及来源说明。Python 节点执行经过检查的本地代码，任务目录约定不构成操作系统级隔离。

## 验证

```sh
python -m unittest discover -s tests -v
python harness.py validate
```

真实调用与业务检查范围记录在 [验证报告](docs/validation.md)。本地安装及打包命令见 [安装说明](docs/install.md)。

上游代码和方法来源及许可证见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
