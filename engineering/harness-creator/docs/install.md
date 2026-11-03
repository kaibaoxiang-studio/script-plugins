# 安装与独立运行

## 环境

- Codex 本地客户端或 CLI，已登录且具有模型调用权限。
- Python 3.12 或更新版本，首次安装需要获取固定版本依赖。
- ZIP 解压后保留整个插件目录，不能仅复制 SKILL.md。

在插件目录使用 Python 3.12+ 执行。若系统 `python3` 仍指向 3.9，请指定已安装的 3.12+ 解释器完整路径；不要依赖 `python3` 这个名称：

```sh
/absolute/path/to/python3.12 scripts/bootstrap.py --install
/absolute/path/to/python3.12 harness.py doctor
```

bootstrap 在用户缓存目录创建按依赖锁哈希隔离的虚拟环境。安装使用固定版本、发行文件 SHA-256 和二进制 wheel，不改系统 Python。后续 harness.py 自动使用该环境。业务插件的依赖锁、运行代码和知识文件均随包携带。

## 安装到 Codex

源码根目录已包含本地 marketplace，可直接注册：

```sh
codex plugin marketplace add /absolute/path/to/harness-creator --json
codex plugin add harness-creator@harness-creator-local --json
```

候选目录本身包含本地 marketplace 清单；发行 ZIP 解压后也包含该清单。已有同名 marketplace 时先在 Codex 中核对其来源，再按当前安装流程更新，避免同时注册两个同名来源。

安装后新建聊天，选择 Harness Creator，或明确调用 `$harness-creator`。补资料时可单独调用 `$harness-knowledge-maintainer`。当前聊天中的 Skill 清单不会因为 CLI 安装而自动刷新。

插件在聊天内直接使用已安装 Skill，也可通过 harness.py 运行显式能力或 DAG。App Server 使用当前 Codex 的模型配置和登录状态；运行器不内置模型名称或密钥。

## 打包与更新

```sh
/absolute/path/to/python3.12 harness.py validate
/absolute/path/to/python3.12 harness.py package --output dist/harness-creator-0.2.0.zip
```

已有文件不会被打包命令覆盖。更新 Creator 时先在独立候选目录完成修改与验证，再交付新包并更新安装。生成插件通过 `revise` 保留用户修改；存在双方修改冲突时给出具体文件，由 Creator 读实际内容后融合。

生成插件的入口、能力与业务使用方法见各自 README、capabilities.json 和 RUNTIME.md。首次生成不会替用户写入现有业务资料目录。

## 常见失败

- Python 过旧：使用 Python 3.12+ 重新执行 bootstrap。
- 缺少 Codex：将可用 CLI 放入 PATH，或设置 `HARNESS_CODEX_BIN` 为 CLI 的完整路径。
- 模型调用失败：查看节点失败记录，核对 Codex 登录与当前模型可用性。
- 恢复被拒绝：插件、输入文件或已完成产物已变化，应按当前版本创建新任务；旧运行记录仍保留。
- 节点等待业务信息：读取 run-report.json 的 questions，再通过 resume --answers 提供用户真实答案。

完整命令、输入输出 envelope 与退出码见 [RUNTIME.md](../RUNTIME.md)。
