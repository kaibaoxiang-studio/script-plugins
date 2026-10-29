---
name: extract-asset-table
description: "由插件内置 Python 固定编排执行 prepare 和 postcheck，禁止跳过阶段"
---

这是内部固定编排能力，由工作流调用，不直接面向用户。它负责在语义审核前创建当前 artifact_dir，并在语义审核完成后执行保存后验收；禁止 Agent 直接跳过这些阶段。
