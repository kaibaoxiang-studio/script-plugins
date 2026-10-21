# 定点知识维护

默认集中源库位于用户工作区 `.harness/library/`；可显式指定其他位置。每项来源保留原文、抽取文本、来源说明及内容哈希，源库不随插件打包。

```sh
python harness.py knowledge-ingest --library /work/library --source /work/material.md --source-id scene-rules --origin https://example.org/source
```

支持 UTF-8 TXT、Markdown、HTML、DOCX、JSON、CSV。其他格式先通过可用文档能力抽取，保留页码/段落依据，再导入；抽取失败或版面丢失时记录缺口，不猜测缺失文本。

针对指定能力编写精炼规则 Markdown：适用问题、可执行方法、证据位置、例外和未知。将用户决定、原文事实、专业解释和建议区分清楚。遇到实质冲突回到主控对齐，不按来源数量投票。

```sh
python harness.py knowledge-publish --library /work/library --source-id scene-rules --rules /work/distilled.md --plugin /work/plugin --capability scene-log --expected-source SOURCE_SHA256 --confirmed
python harness.py knowledge-status --library /work/library --plugin /work/plugin
```

发布生成目标能力专用的 `references/knowledge/CAPABILITY/SOURCE.md`，同时更新 capability 的 knowledge_refs、Skill 链接和 knowledge-lock.json。来源重复使用时分别维护各能力快照，单点补充不会替换其他能力的规则。

对已发布知识文件，工具检查旧快照哈希。用户手工编辑过时，先读完整差异并融合规则；授权的更新可传 `--expected-current CURRENT_HASH`，避免覆盖未读内容。source 版本变化不自动激活，knowledge-status 提示哪些快照有新来源。

最后运行 validate 和与该知识有关的行为样例。来源哈希、文件完整性检查只能验证快照，知识正确性仍由证据、用户业务判断和实际样例验证。
