# 分工、批次提交与独立审核

本地0.3.1。已有用户授权或用户要求多agent时启用；没有subagent能力时保留单agent流程，不把同一执行者的自查称为独立审核。已有授权不要重复询问。以下工具只管理工作文件和验证，不会自己启动agent；主agent用执行环境提供的subagent能力调度。

## 分工与启动

主agent冻结原文、分配编号、合并、路由问题和发布。人物/场景/道具各一个全剧责任者，每个都读全部原文及对应业务规则。不能按集拆同一人物的连续性或同一道具的身份。主agent提前确定ID，不让角色编号随Excel排序变化；程序会拒跨类别和重复ID，不自动重命名。

独立审核agent读原文、合并后的assets/review及业务规则，先独立判断，再查看程序诊断。不要给它提取agent的“无问题”结论作为答案。审核只产报告，提取责任者修数据，主agent再合并，审核者复查。

四并发槽位先运行“主agent+三类提取”，提取结束后再启动审核；审核结束后再分配返修。禁止并发写最终assets.json/review.json。仅主agent调用submit/merge/submit-audit/bind。worker写独立draft文件。

```bash
python3 "$S/workflow.py" prepare "<剧本.docx>" "<工作目录>"
python3 "$S/workflow.py" team-init "<工作目录>"
python3 "$S/workflow.py" fragment-template "<工作目录>" --kind characters --output "<工作目录>/drafts/characters.json"
python3 "$S/workflow.py" fragment-template "<工作目录>" --kind scenes --output "<工作目录>/drafts/scenes.json"
python3 "$S/workflow.py" fragment-template "<工作目录>" --kind props --output "<工作目录>/drafts/props.json"
```

模板保留待审空字段，不是已审证明。每类片段为`asset_fragment_v1`，绑定解析数据的source_sha256、当前version、kind、scope（真实场次号）；包含assets（此类别业务数组）、line_reviews、category_reviews、candidate_reviews、character_reviews。人物负责visual/timeline候选，道具负责prop_*候选，场景不反写其他候选。原文/版本变化拒提交，不能仅刷新哈希继续使用旧判读。

worker任务必须给出：绝对原文/规则/草稿路径、类别和ID范围、全剧责任边界、真实审查范围、当前source/version、只允许写本类draft、完成证据及剩余问题。人物先写appearances和change_reviews，道具先写mentions与identity/alias依据；不能从旧状态列表反造记录。

## 减少重复填写与批次校验

每类line_reviews必须有scene_id、line、完整原文quote、具体conclusion，category_reviews每场一个具体取舍结论。asset_ids允许留空交由程序补可确定的关联：人物真实appearance覆盖的行、道具visible mention所在行、类别集合从已审业务记录派生。程序不补出镜、身份、状态、排除理由或“已读”。额外引用的未知/错类别/不在本场ID会拒。

```bash
python3 "$S/workflow.py" candidate-groups "<工作目录>"
python3 "$S/workflow.py" submit "<工作目录>" --fragment "<工作目录>/drafts/characters.json"
python3 "$S/workflow.py" check-batch "<工作目录>" --kind characters --scene 1-1 --scene 1-2
```

candidate-groups将动作分句与其中物品词作为一个阅读组，保留原始候选全部ID及证据。多物件组仍须分别判断每个候选，不能整组借一个物件通过；未命中词表的内容靠逐行通读补全。

可以用fragment-template的重复`--scene`创建批次范围。提交是累计快照：后续scope必须包含此前已提交场次，保留已审内容，不能用新文件替换掉历史范围。此类assets须自包含全局身份、目前写入的继承链和候选复核；不能把人物阶段的上游记录裁掉来通过局部校验。跨场身份/人物变化候选属于全剧约束，提交仍会检查，不会因为其他批次pending而豁免；场次逐行和独立候选覆盖则只要求当前scope。

报告区分submitted_scope、pending_scope、issues、warnings。部分validated只是提交范围的结构通过，global_complete始终false，不能称整剧提取完成。已有valid片段保存到fragments/<kind>.json；草稿出错不覆盖旧提交。check-batch只读检查，不修数据；最新执行仍running/failed时明确报告agent_incomplete，旧validated片段不能代表本次任务完成。

## 省略宾语动作

“林岚摘下右手的银戒指，交给周衡”可把后分句动作关联同句前分句银戒指，但须实际核对并在该recorded prop_action候选增加action_refs：

```json
{
  "action_refs": [{
    "asset_id": "真实PRP-ID",
    "mention_id": "该道具同一行先行visible记录的真实M-ID",
    "scene_id": "真实场次",
    "line": 1,
    "start_offset": 0,
    "end_offset": 1,
    "quote": "完整候选cue",
    "reason": "具体说明原文哪个局部称呼被该动作承接"
  }]
}
```

上例仅示字段，位置必须用真实候选完整区间替换。quote为候选动作cue，mention的raw_name保持真实物品称呼。旧直接分句内mention匹配继续有效。action_refs仅允许同一行、逗号连接的相邻分句、一个先行visible实物；精确回查引用ID、原文、区间和状态，遇句号/分号、间隔其他物件或新人物主语保守拒绝。跨句复杂指代保留阻塞给规则维护者，不伪造raw_name、不删候选、不假称动作没有出镜。即便另有直接匹配，坏action_refs也会拒。该结构不能证明自然语言指代必然正确，独立审核仍需回查。

## 合并与独立审核门槛

```bash
python3 "$S/workflow.py" submit "<工作目录>" --fragment "<工作目录>/drafts/scenes.json"
python3 "$S/workflow.py" submit "<工作目录>" --fragment "<工作目录>/drafts/props.json"
python3 "$S/workflow.py" merge "<工作目录>"
python3 "$S/workflow.py" audit-template "<工作目录>" --output "<工作目录>/audit.pending.json"
```

merge只有三类全场scope通过才生成最终assets/review，保留主agent未识别段落复核、旧审核记录及旧视觉记录供后续判断；不自动bind。未通过不覆盖，写入采用共享锁、输入指纹检查和失败回滚。team状态不能代替实际片段验证。模板报告为asset_independent_audit_v1，绑定source/asset/review哈希、audit_state_sha256（当前独立审核及问题状态）和version，reviewer_id填写实际审核者标识。

审核agent填写scene_reviews逐场结论及character_reviews按人物全剧边界结论。人物复核不按集割裂；场次结论须涉及原文出镜、状态、道具身份、候选排除与陈设。发现问题写issues，每项有issue_id、owner（characters/props/scenes/validator/coordinator）、真实scene_id/line、message、实际原文evidence_refs；人物问题必须填该人物asset_id。只在确实涉及其他类具体资产时填asset_id，不捏造。

```bash
python3 "$S/workflow.py" submit-audit "<工作目录>" --report "<工作目录>/audit.pending.json"
```

审核报告有未解决问题或范围尚未覆盖时命令返回非零，但有效审核记录已保存，不需删掉重来。主agent读具体报告决定下一步。不能以exit code代替是否写入的判断。submit-audit不会批准业务弱警告。

issues退给责任方修改draft，再submit/merge。审核者用新audit-template复查变化范围及仍未解决问题所在范围；open_issue_ids只列待办，不自动声称已解决：已解决旧问题填resolved_issue_ids，必须实际复查问题所在场次，人物问题还要复查该人物。忽略旧问题、空issues或简单改status不能通过正式闭环。新问题保持新ID，不能改写旧ID为另一问题。报告还绑定当前问题状态；问题重开或其他审核提交后，旧报告不可重放，须取当前模板再次实际复查。

审核按场次和人物指纹保存。修改一个资产会让其所有相关场次及相关人物审核过期（保守依赖，不只改动行）；无关范围可复用。原文或规则版本改变全部失效。每条范围结论仍由审核者实际填写，程序只绑定，不编造“已审”。

## 错误路由与恢复

```bash
python3 "$S/workflow.py" diagnose "<工作目录>"
python3 "$S/workflow.py" record-run "<工作目录>" --kind props --state running --agent "实际agent标识"
python3 "$S/workflow.py" record-run "<工作目录>" --kind props --state failed --error "实际429或其他错误原文"
```

diagnose保存完整diagnostics.json，不截断到前40项，并提供code、owner、场次/行/资产位置及affected_scopes。分类是提示，无法确定责任时归coordinator；不要将所有候选错误都归校验器。真实候选位置规则冲突先给validator维护，不能逼提取agent伪造事实来通关。

record-run在启动/失败时记录到team.json；成功由submit校验确认，不允许自报completed。running或failed不能借旧片段merge。连续同类执行最多3次，失败后错峰重试；达到上限保留草稿并报告阻塞原因，先解决原因再继续，不无限重启。成功提交重置连续失败计数，历史runs保留。工具没有自动调用agent或自动睡眠。中断后先status/check-batch，再读team.json中的真实scope、run和issues恢复。

写入锁为工作目录.team-write.lock，正常结束清理。进程被强制终止可能留锁；先确认没有任何agent/命令在写，再由主agent清理该残留锁，不自动删活跃锁。

## 最终验收

所有覆盖、全剧业务约束、独立范围审核、问题复查与具体警告确认完成后，主agent统一bind/export，实际查看四表，再finalize。bind不清除语义结论；只有展示计划、来源指纹、已保存工作簿内容及哈希均一致才保留视觉记录。计划变更/文件被改则重做视觉检查。旧0.2.1记录没有新增计划指纹，首次升级需重新导出并看图；不能机械填新字段保留旧证据。

新增工作文件均留工作目录，正式输出仍是assets.json与Excel。结构、哈希、审核者标识只能验证记录一致性，无法证明agent确实独立通读，也无法保证零漏提。禁止伪造审核、图片或用户批准。
