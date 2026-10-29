# 执行台账与完成标准

此文件定义本地 `0.3.2` 工作流程，业务资产仍沿用 v0.1.1 的三类结构。`review.json`、`progress.json`、预览图片和 `acceptance.json` 是工作文件，不新增正式交付文件。

## 阶段与状态

`prepare → 逐场提取和审查 → 同步 → bind → export → 实际视觉复核 → finalize`。

- `prepare` 原始 DOCX 质量通过后才写 `scenes.json` 和空白 `review.json`；不会创建已审结论或自动提取资产。目录已有文件时拒绝覆盖，重新解析用新目录。
- `bind` 先运行原有资产约束及来源重解析，再检查全场、全行、三类集合、独立线索和人物边界复核。通过后只计算源数据、三类业务数据的规范 JSON 哈希；记录场次/人物范围指纹；只有来源、展示计划和已保存工作簿验收一致时保留旧视觉记录，否则清空。
- `export` 原文及审核快照通过后生成 `asset-table.review.xlsx`，自动重开保存文件并从当前数据重建期望模板验收。新导出后建立待填逐表视觉审核；当前副本及计划不变且验收通过时复用原文件和记录。此时不是正式交付完成。
- `finalize` 再运行上述约束，核对已看图证据、复核副本哈希并再次检查工作簿，复制通过的 Excel 为正式文件，保存 `acceptance.json`。
- `status` 动态检查输入、审核与交付哈希；不会仅因 progress 写了 complete 就成功。来源或资产变化、修改已交付文件、修改台账均可能使验收过期。

`--warning-report` 仍是诊断命令，不要求审核完成，也不能表示可以交付。底层 `--sync-*` 不产生审查结论；正式 `--check`、`--export-spec`、工作簿导出和保存后验收均回查原始 DOCX，并要求当前台账；删除来源信息不能绕过。`validate()` 纯函数保留为底层业务校验，不能替代执行门槛或交付验收。

分工模式先执行team-init，三类片段分别提交和合并，再独立审核、返修和范围复查；详见 [分工与独立审核](agent_workflow.md)。旧单agent台账仍兼容，独立审核启用后不能用关闭标记绕过。

## 空白台账

`prepare` 生成以下结构，待填写字段均为空。示例是结构说明，不可复制成真实剧本的通过结论。

```json
{
  "schema_version": "asset_execution_review_v1",
  "source_sha256": "bind 后生成",
  "assets_sha256": "bind 后生成",
  "scenes": [{
    "scene_id": "1-1",
    "lines": [{"line": 1, "quote": "完整原文行", "asset_ids": [], "conclusion": "本行实际出镜、变化及物件取舍"}],
    "categories": {
      "characters": {"asset_ids": [], "conclusion": "本场人物取舍"},
      "scenes": {"asset_ids": ["SCN-001"], "conclusion": "本场空间归属"},
      "props": {"asset_ids": [], "conclusion": "本场道具取舍，零项也写原因"}
    }
  }],
  "candidate_reviews": [],
  "character_reviews": [],
  "delivery_review": {}
}
```

每场每行仅一条审核，行号从 1 起、引文与完整原文相同。类别 ID 集合等于本场实际 states/subscenes 分配；行级 ID 只能引用本场资产，每条已有 visible mentions 也必须关联相应原文行，即使词语未命中候选扫描。未识别但质量门槛内保留的 `other` 行也必须判断，不能跳过。"已完成"、"通过"、"无问题"等单独占位文字不通过。

未识别段落另由 `parse_reviews` 逐条复核，包括场头前或集标题前的内容：每项保存 `paragraph`、完整原文 `quote` 和具体 `conclusion`。超过门槛不能靠复核放行；门槛以内也不能忽略这些段落。发现实质剧情无法正确入场时先修规范格式重新解析，而不是改 scenes.json。验收报告单列未识别段落数与已复核数，不把解析提示冒充全部消失。

## 独立原文候选

`source_candidates.py` 不读取 assets，扫描原文物件词、拿取/交接/使用等动作分句、外观变化、闪回/时间跳跃等线索。它们是复核待办，不是自动出镜判断；有误报必须回查排除。常见物件词表不是完整字典，关键词未命中的表达仍由通读补全。

每条候选包含 `candidate_id/kind/cue/start_offset/end_offset/source`，这些来源字段保持原样；填写：

```json
{
  "decision": "recorded",
  "asset_ids": ["PRP-001"],
  "evidence_refs": [{"scene_id": "1-1", "line": 1, "quote": "覆盖候选线索的本行原文"}],
  "reason": "说明为什么属于此实物或阶段"
}
```

- `recorded`：关联本行实际资产。物件词须由同位置 visible mentions 覆盖；动作分句须有分句内的 visible 实物记录，或符合 [分工与审核](agent_workflow.md) 的显式 action_refs 局部先行称呼依据；不能借任意同场道具通过。外观/时间线关联覆盖该行的人物 appearances；同一行更精细的阶段及继承由原人物校验器负责。
- `excluded`：`asset_ids=[]`，证据覆盖该线索，说明固定陈设归场景、服装归人物、仅提及不出镜等具体取舍。不要因没有所有者、没有损坏、词语不熟悉而排除。
- `uncertain`：保留问题并回查，需要用户判断时问具体问题；该状态阻止正式交付。不能删候选或改原文来消除。

候选 ID 与原文位置/文本绑定，原文变化必须重新定位。排除理由的真实性仍需实际判断，脚本不能证明任意自然语言结论正确；禁止编造理由绕过。

多状态、有 reset 边界或 inherited 出场的人物另填 `character_reviews`：

```json
{"character_id": "CHR-001", "appearance_ids": ["A001", "A002"], "conclusion": "按原文核对全部阶段的服装、伤势、变身恢复及时间连续性"}
```

此列表必须覆盖该人物全部 appearances，结论来自按人物通读全剧；不能只核对最后一个状态。

## 工作簿视觉复核

`export` 自动绑定复核副本字节哈希，并为四表建立空白 visual 数组。实际查看正常缩放预览或 Excel 页面，保存 PNG 证据（检查完整数据块、校验和及像素流，拒绝文件头和单像素占位），再填写每表的 `conclusion/evidence_file/evidence_sha256`。路径可为工作目录内相对路径或绝对路径。每张表均需具体记录分组、长文本、合并留白、阅读密度及实际筛选结果；缩小整体图不能替代正常缩放检查。可针对长备注和完整人物组增加多个视图，`evidence_file` 指向关键视图，其余图留工作目录。

```json
{
  "workbook_sha256": "export 自动生成的工作簿哈希",
  "visual": [{"sheet": "人物", "conclusion": "实际检查的具体结果", "evidence_file": "previews/人物.png", "evidence_sha256": "该已查看图片的文件哈希"}]
}
```

用以下确定性函数计算图片指纹，不生成任何判读：

```python
from execution_review import file_digest
image_sha256 = file_digest("previews/人物.png")
```

图片存在与哈希匹配只证明证据文件固定，不能证明图中布局正确。不得用测试图、其他项目图片、占位图冒充预览。环境无法查看时说明具体阻塞，保留已完成数据和复核副本，不伪造正式完成。

## 其他 Excel 后端

统一 `export_contract.py` 不变。先 `build_xlsx.py scenes.json assets.json --export-spec workbook-plan.json --review-file review.json`，按计划写工作目录的 `asset-table.review.xlsx`，运行 `check_workbook.py scenes.json assets.json asset-table.review.xlsx --review-file review.json`。有已确认警告时两个命令传同一 `--warning-approvals`。

验收通过后依据当前副本字节哈希填写 `delivery_review`，完成实际四表视觉检查，仍由 `workflow.py finalize` 再验收并发布；该流程不要求另调用 export 覆盖外部后端的结果。

## 完成证据

`acceptance.json` 绑定原始 DOCX、解析数据、三类业务数据、assets.json 文件、review.json 文件和已交付 Excel；记录资产/状态数量、错误、未确认及已确认警告数量与详情。报告分开说明机器检查通过与实际人工/Agent 判读记录，不能把通过程序等同于语义百分之百正确。该门槛适用于本 skill 的正式流程，无法约束故意绕开 skill 另写文件的行为。

运行回归：

```bash
python3 -m unittest discover -s scripts -p 'test_*.py'
```
