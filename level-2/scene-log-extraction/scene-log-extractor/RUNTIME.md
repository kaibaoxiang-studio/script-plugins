# 本地运行说明

需要 Python 3.12+ 和已登录的 Codex CLI。代码使用 `jsonschema` 与 `PyYAML`，全部依赖版本和发行文件哈希锁定在 requirements.lock。

```sh
python scripts/bootstrap.py --install
python harness.py doctor
python harness.py validate
```

bootstrap 将独立环境写入用户缓存；harness.py 自动找到这个环境，避免依赖系统 Python 包。它不修改 Codex 配置。已有兼容环境也可直接执行。

## 调用

输入存为 JSON，使用目标插件的 capability id 或 workflow id：

```sh
python harness.py run-capability --capability CAPABILITY --inputs /absolute/inputs.json --workspace /absolute/work --confirmed
python harness.py run --workflow WORKFLOW --inputs /absolute/inputs.json --workspace /absolute/work --confirmed
python harness.py status --workspace /absolute/work --run-id RUN_ID
python harness.py resume --workspace /absolute/work --run-id RUN_ID --answers /absolute/answers.json
python harness.py cancel --workspace /absolute/work --run-id RUN_ID
python harness.py replay --workspace /absolute/work --run-id RUN_ID
```

--confirmed 表示当前任务已有授权，不生成用户同意。Agent 缺少决定时返回 awaiting_input。完成只在输出符合 schema、必需产物存在且路径/哈希有效时成立。退出码：0 正常，1 验证或执行失败，2 参数/环境错误，3 等待输入。

运行数据和最终文件在工作区 `.harness/RUN_ID/NODE/attempt-N/`，run-report.json 汇总实际结果。数据库存于工作区 `.harness/runs.sqlite3`。输入、插件或已完成产物改变时应启动新任务。运行记录包含本地路径和业务输入，默认仅保存在本机，打包不包含它们。

Agent 使用 Codex App Server 的本地 stdio 协议，继承当前模型配置，按节点分配本地写目录。Python 脚本是已审阅的本地程序；任务目录约定和产物路径校验不构成操作系统级进程沙箱。

## 发行

`python harness.py package --output /absolute/plugin-version.zip` 验证并打包。ZIP 内包含一个插件根目录，可解压后作为本地 marketplace 的插件源。包中不包含 `.venv`、`.harness`、Git 历史、测试运行数据或集中原文源库。

协议依据：https://learn.chatgpt.com/docs/app-server

插件规范：https://developers.openai.com/plugins/build/plugins
