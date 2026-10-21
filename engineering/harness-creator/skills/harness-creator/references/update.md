# 增量修改与自身升级

先读目标源码、capabilities、已发布知识、generation-lock 与来源收据。明确目标行为变化及受影响能力；普通修正沿用已有授权，高影响新需求先对齐。

## 定点 patch

每项修改提供目标路径、当前文件 SHA-256 与完整新内容；新文件 expected_sha256 为 null。命令先在候选副本中修改并验证，再检查原目录是否发生并发变化。冲突时停止并保留现有文件。

```json
{"changes":[{"path":"references/rules.md","expected_sha256":"current sha256","content":"complete new contents"}]}
```

`python harness.py patch --plugin TARGET --plan CHANGES_JSON --confirmed`

## 新版本

`revise --source CURRENT --spec NEW_BLUEPRINT --output SIBLING_CANDIDATE --confirmed` 重新组装独立候选，对照首次生成哈希保留未被新需求触及的用户修改；双方都改动同一文件则报冲突，融合进蓝图后重新生成。用户新增文件也保留。调整版本号后重新验证、打包。

Creator 自身也作为插件目标处理。使用 patch 时将复制后的候选目录作为 target，不改正在执行的 Creator 包；候选通过测试后交付供更新安装。当前 run 使用固定源码和输入，升级后的新任务使用新版本。不同来源和版本的真实验证结果分别保留，不能拿旧版结果替新版背书。
