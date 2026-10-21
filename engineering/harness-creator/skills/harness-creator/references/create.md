# 从需求到可用插件

先完成业务能力设计，输出供用户阅读的能力目录、采用来源、知识资料、交接与验收。确认后的同一份决定用于 HarnessBlueprintV1；不要另写一套互相矛盾的实现规格。

蓝图 JSON 最小结构如下；示例里的统计方法是实际可执行能力，不构成其他业务的默认工作流。

```json
{
  "schema_version":"HarnessBlueprintV1",
  "plugin":{"name":"text-counter","version":"0.1.0","description":"统计输入文字并保留结果","author":{"name":"Your team"}},
  "goal":"提供可独立调用的文字计数能力",
  "acceptance_criteria":["不同输入得到对应计数","实际结果文件存在"],
  "open_questions":[],
  "capabilities":[{
    "id":"count-text","skill_name":"count-text","description":"统计用户提供文字的字符数",
    "instructions":"读取用户提供的 text，使用 scripts/count.py 完成字符统计。保留空白字符的定义，并通过运行结果核对实际计数。经 bundled harness 调用该能力，在本次任务目录生成 report.json，再报告产物位置。",
    "input_schema":{"type":"object","properties":{"text":{"type":"string"}},"required":["text"],"additionalProperties":false},
    "output_schema":{"type":"object","properties":{"characters":{"type":"integer"}},"required":["characters"],"additionalProperties":false},
    "execution":{"kind":"python","script":"scripts/count.py"},
    "required_artifacts":["report.json"],"knowledge_refs":[]
  }],
  "files":{},"workflows":[],"sources":[]
}
```

必须实际编写 `files["scripts/count.py"]`：解析 input/output 参数，从任务 inputs 取 text，计算 len(text)，向 artifact_dir/report.json 写结果，再向 --output 写结果 envelope。构建前确认输入定义和输出规则，不能用硬编码示例值代替实现。

Agent 能力的 execution 形如 `{"kind":"agent","access":"workspace-write","network":false}`；无需写文件的节点可用 read-only。其 instructions 应包含当前业务方法、证据要求和验收，而不是仅要求模型“专业地完成”。

`files` 包含已写好的 references、scripts 和模板文本；引用根目录资料时 Skill 内链接使用 `../../references/...`。蓝图不会复制开发机 `.venv`、源库、其他业务 Skills 或环境配置。

从插件根目录运行：

```sh
python harness.py build --spec /absolute/work/blueprint.json --output /absolute/work/new-plugin --confirmed
python harness.py validate --plugin /absolute/work/new-plugin
python harness.py package --plugin /absolute/work/new-plugin --output /absolute/work/new-plugin-0.1.0.zip
```

`--confirmed` 记录调用者已有的任务/方案授权；命令行参数不会替用户产生确认。遵循当前会话已给出的授权，不为每个低影响实现细节增加一次确认。输出目录已存在时选择增量 patch 或独立 revision，不清空用户目录。
