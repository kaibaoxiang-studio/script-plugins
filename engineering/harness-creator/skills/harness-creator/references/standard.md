# Harness 标准 v1

一个插件表示可复用能力集合。能力蓝图记录业务设计；一次运行的输入、任务图和结果单独存放。避免把首次示例、角色名或场次写成通用调度规则。

## 包结构

插件包含 `.codex-plugin/plugin.json`、`skills/`、`capabilities.json`、`harness.py`、`runtime/`、固定版本 `requirements.lock` 及需要的 scripts/references。生成器同时输出 portable `plugin.json`。资源路径相对插件根目录，插件不依赖 Creator 或其他已安装业务 Skill。

能力定义包含：唯一 id、skill_name、实际用途、JSON Schema 输入输出、执行方式、知识引用与可选 required_artifacts。Agent 负责有依据的判断；Python 负责确定性转换。调用一个能力可用 `run-capability`；组合能力用 catalog 中的 workflow。开放业务主控可以按任务选择或提出经过验证的组合，而不是固定套用全部岗位。

## 节点与交接

节点声明 capability、depends_on、bindings、idempotent、retries 和 timeout_seconds。`bindings` 的普通值是常量；`{"from":"inputs.file"}` 从本次输入取值，`{"from":"extract.rows"}` 从依赖节点的业务结果取值。引用上游必须显式声明依赖。

Python 节点使用当前解释器执行包内脚本，参数 `--input TASK_JSON --output RESULT_JSON`。任务输入为 `inputs`，本节点允许的产物目录为 `artifact_dir`，补充答案位于 `answers`。结果写入协议 envelope：

```json
{"status":"succeeded","result":{"value":1},"artifacts":["report.json"],"questions":[],"error":null}
```

`result` 必须通过该能力输出 schema；产物路径相对 artifact_dir，运行时校验文件及哈希。Agent 使用同一 envelope，由 Codex App Server 的 outputSchema 约束输出。需要用户决定时返回 blocked 和具体 questions。失败返回 failed 与 error。

## 状态与边界

SQLite 事件是运行记录的事实来源，snapshot 可重放。插件或输入文件改变时启动新 run；成功结果的产物哈希改变时拒绝续用。幂等节点最多重试一次，非幂等节点不自动重试。默认并发 3，上限 3；可选单节点或串行依赖链。

Agent 写入仅授予节点工作目录；源资料用于读取。Python 节点是已检查的本地程序，运行目录隔离不等于操作系统沙箱。需要写外部业务系统的功能超出 v0.1 默认能力范围。

生成过程中使用当前用户选择的 Codex 模型配置，不固定具体模型。调用权限受宿主设置约束；不通过修改配置绕开限制。实际 CLI 和协议需要通过 doctor 与真实小样检查。
