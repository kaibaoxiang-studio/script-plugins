# 功能级规格与验收证据

这套协议用于 Creator 建设插件时的交付记录；`DeliveryPlanV1` 不是一次业务运行的 DAG，也不进入生成插件的发布包。蓝图仍定义能力及其输入输出，交付计划定义如何逐项建设和验收。

## 形成计划

先完成 `HarnessBlueprintV1`，再在用户工作区写 `delivery-plan.json`：

- `blueprint_sha256` 是蓝图文件的 SHA-256。蓝图变化后重新检查计划和受影响证据。
- `features` 按可观察行为拆分。每项有稳定 `id`、`capability_ids`、`depends_on`、目标、非目标和至少一个 Given/When/Then 场景。一个小插件可以只有一项；不设固定数量或行数要求。
- 每项能力至少被一项 feature 覆盖。依赖只表示建设先后，不替代运行时 workflow。
- 对每项 feature 写单独的实施规格，指出当前文件、预期修改、验证方式、证据与边界。已有清晰材料可直接引用，不重复复制整份蓝图。

运行 `harness.py delivery-plan-check --blueprint BLUEPRINT.json --plan delivery-plan.json` 检查覆盖、依赖和版本。

## 实施与独立验收

实现者先运行真实检查并记录命令、退出码与日志：

```sh
python3 harness.py capture-check --workspace WORKSPACE --feature FEATURE_ID --scenario SCENARIO_ID -- python3 tests/check_feature.py
```

命令从 `WORKSPACE` 执行，不经 shell；返回的 `log_path` 相对工作区。每个验收场景至少有一条成功检查。实现者将检查记录、实际产物路径及哈希填入 `evidence/FEATURE_ID.json` 的 `implementation` 部分。失败检查可以保留；同一场景最后一条检查须通过。

验证者依据实施规格、实际文件、差异和原始证据复核；在可行时重跑场景并用 `capture-check` 留下**自己的**检查日志。验证者输出 `accept`、`revise` 或 `block`，以及报告文件；`revise` 给出可直接执行的修复清单。实现者与验证者使用不同会话标识，且不能复用同一检查日志。若当前环境无法提供独立会话，只记录自检和待审状态，不把它写成独立通过。

验证者检查完最终插件文件后，运行 `harness.py plugin-fingerprint --plugin PLUGIN`，将返回的 `fingerprint` 写入每个已验收 feature 的 `validation.plugin_fingerprint`。之后修改插件文件必须重新复核并更新证据；该指纹覆盖打包范围内的插件文件。

`FeatureEvidenceV1` 的字段见 `schemas/feature-evidence.schema.json`。所有日志、报告与产物路径相对 `WORKSPACE`，填写实际 SHA-256。证据文件名固定为 `evidence/FEATURE_ID.json`。`plan_sha256` 是 `delivery-plan.json` 文件的 SHA-256；改动计划会使旧证据失效。

运行以下交付门槛：

```sh
python3 harness.py delivery-check --plugin PLUGIN --workspace WORKSPACE --blueprint BLUEPRINT.json --plan delivery-plan.json --evidence-dir evidence
```

`delivery-check` 要求所有 feature 的独立结论为 `accept`，每个场景的实施与验证检查均通过，且日志、报告、产物哈希及最终插件指纹仍匹配。它核对可观察记录，不能证明模型的判断正确，也不能仅凭会话标识证明审查者完全独立；业务内容仍由验证者负责。未通过时交付候选与具体缺口，不宣称已验收。

正式发行使用 `release-package --plugin PLUGIN --output ZIP --workspace WORKSPACE --blueprint BLUEPRINT.json --plan delivery-plan.json --evidence-dir evidence`，它先执行交付门槛，再打包。普通 `package` 仍可制作待审候选，不表示功能已验收。
