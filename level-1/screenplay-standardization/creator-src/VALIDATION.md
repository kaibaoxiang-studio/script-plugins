# 剧本标准化插件验收记录

日期：2026-10-20。测试对象是相邻目录中的 `screenplay-standardizer`，由 `build_blueprint.py` 生成并经 Harness Creator `build`、增量 `patch`、`validate` 和 `package`。交付 ZIP：`../screenplay-standardizer-0.1.0.zip`。

## 已通过

- Harness Creator 插件契约校验：`valid=true`、0 错误、2 个公开能力、3 个 Skill。ZIP 解压至临时目录后再次校验，结果相同；解压后的脚本对一集一场 TXT 小样实际执行 `prepare` 与 `finalize`，产生四份文件。
- Codex 插件化：给 `.codex-plugin/plugin.json` 与 portable `plugin.json` 增加“剧本标准化”展示信息，生成本地市场并通过 `codex plugin marketplace add`、`codex plugin add screenplay-standardizer@screenplay-standardizer-local` 安装。`codex plugin list --marketplace screenplay-standardizer-local --json` 返回 `installed=true`、`enabled=true`；安装缓存中的展示名已核对。
- 10 项单元测试通过。覆盖 DOCX 标色字符范围、正文与双语对白、纯细纲待创作门槛与生成块契约、同级版本歧义、明确最终稿选择、合法改名、疑似错名、空对白、动作提示与对白不符、漏台词线索、跨场闪回，以及 light/deep 结果边界。
- 使用打包目录中的实际脚本，对三组用户原稿分别执行 `prepare`、`finalize` 和独立 `review`。全部主稿非空段落均映射来源；JSON 校验通过；Markdown 的集场数量与 JSON 一致，原有对白仍可在 Markdown 中找到。审查疑点独立写入 `findings.json` / `findings.md`。

| 原稿 | 选定主稿 | 集 | 场 | 对白块 | DOCX 标色 run | 轻审疑点 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 《我是62岁男房东》 | 含剧本的复合段 | 53 | 71 | 1127 | 918 | 40 |
| 《荒年双穿》 | 正文 | 50 | 92 | 845 | 20 | 55 |
| 《龙王的狐族新娘》 | 末尾“剧本”段 | 25 | 37 | 298 | 0（TXT） | 11 |

《龙王》原稿中的细纲及双语版本保存于 JSON 的 `support_material`，主稿已有双语对白原样保留。剧本 Markdown 只呈现所选主稿的剧本正文。原稿标色范围统一保存于 `source_annotations`，正文块同时保存局部 `annotations`。独立审查的 `notices` 与证据化 `findings` 分开。

## 尚未验证的 Agent 路径与已知差异

- Harness `run-capability standardize-screenplay` 对一场 TXT 小样发起两次真实调用；两次子线程均在读取 Skill 后由本机 App Server 标记为 `interrupted`，未执行 `prepare`，随后取消运行。安装本地插件后，`run-capability review-screenplay` 又对同一小样调用一次，子线程同样在读取 Skill 后中断。插件注册、脚本与契约已经分别验证，但 **Agent 的创作、自动标题概要修订及主动深审未完成端到端验收**。不将这些调用记为通过。
- 《荒年双穿》原稿显式列出 92 场，人工改造标准稿为 100 场。本插件的保守抽取保留 92 场；额外拆场属于需要 Agent 结合情节判断的编辑工作，尚未由被中断的 Agent 调用验证。
- 纯细纲创作通过模拟 Agent 写入的有来源生成块验证了结构和渲染契约；真实模型创作质量仍待 Agent 运行环境恢复后验收。直接对尚未创作的纯细纲执行 `finalize` 会拒绝输出，以免把占位稿当作标准剧本。

三组原稿与标准稿是用户本地验收素材，没有复制进插件 ZIP。ZIP 中仅保留独立编写的脚本与方法性 references；原 SN2S ZIP 未见许可文件，未复制其实现。

## 2026-10-22｜0.1.1 中文交付名称

- 按用户要求，面向用户的文件夹与文件优先采用中文名称；固定交付文件更新为 `标准化剧本.json`、`标准化剧本.md`、`剧本疑点报告.json`、`剧本疑点报告.md`。内部运行目录与 JSON schema 标识保持既有契约。
- `creator-src/tests` 的 10 项测试运行结果为 9 项通过、1 项因未设置私有样稿目录而跳过；新增断言核对四个中文文件名。
- Harness Creator `doctor` 确认 Python 3.12.14 与 Codex CLI 可用；`build` 和 `patch` 的验证均返回 `valid=true`，2 个能力、3 个 Skill。0.1.1 ZIP 解压后再次 `validate`，并用一集一场样稿实际执行 `prepare`、`finalize`，只产出四个中文文件。
- `codex plugin add screenplay-standardizer@screenplay-standardizer-local` 安装 0.1.1；`codex plugin list` 返回已安装且启用，安装缓存内的 Skill、reference 与脚本均已核对。此次更新未重新验收 Agent 创作或深审路径。
- 以当前四份中文文件调用安装版 Harness 的 `verify_result`，相对产物名、必需产物检查与 SHA-256 校验通过。

## 2026-10-22｜0.1.2 空对白正文块修复

- 根因：来源稿有仅含说话人标签的段落，0.1.1 将其抽成 `text=""` 的对白块；一级校验未拦截，二级场记表因此在正文块非空检查时停止。
- `prepare` 略去空对白块，同时在 `coverage.omitted_source_refs` 和 `empty_dialogue` 疑点中保留来源；`finalize` 对旧版 `work.json` 的同类空块做相同修复。其他空正文块仍由校验器拒绝，不补造台词。
- 11 项单元测试中 10 项通过、1 项私有样稿测试因未设置环境变量而跳过。新增回归覆盖来源空对白、旧版中间 JSON 修复、来源引用与报告去重。
- 用户提供的实际 50 集 DOCX 在第 32 集第 2 场的空对白来源为 P1535；使用 0.1.1 生成中间 JSON，再由 0.1.2 `finalize`，该场仅保留 7 个非空正文块，疑点报告仍有一条 P1535 的 `empty_dialogue`。本次确定性抽取为 92 场；用户提供的人工标准稿为 98 场，本修复没有重做其创作性拆场。
- Harness Creator `doctor`、新构建及 ZIP 解压后 `validate` 均通过，2 个能力、3 个 Skill。0.1.2 已安装到本地插件缓存并启用。未重新运行完整二级场记表 Agent 流水线。
