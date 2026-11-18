# 剧本标准化插件 v0.1.3

## v0.1.3 本机同步（2026-11-18）

同步本机已安装的宿主原生语义委派与临时CLI兼容路线；保留标准剧本、来源与疑点合同。实际文件、结构、重建与解包核对见发行manifest，本次未调用模型重新标准化剧本，历史业务结果不转记为本次通过。

本目录是可独立安装的插件快照，包含 Skills、references、脚本与锁定依赖。正常宿主调用用原生子代理完成连续集场段的语义标准化、创作或深审；主控维护全文覆盖并统一跨段姓名、编号和持续状态，唯一写入工作稿。Python 负责保真解析、来源定位、保存、检查与导出。无需另装 Harness Creator，也不默认新建 App Server 派发聊天；独立命令行 Harness 仅为显式兼容入口。详见[协作规则](references/native-delegation.md)。

公开能力：`standardize-screenplay` 生成标准剧本 JSON/Markdown 和独立疑点报告；`review-screenplay` 独立生成疑点报告。默认轻审，深审需显式选择。剧本已有正文时脚本先完成保真抽取；纯细纲由 Agent 依据来源逐集创作。

面向用户的交付文件为 `标准化剧本.json`、`标准化剧本.md`、`剧本疑点报告.json`、`剧本疑点报告.md`。新建交付文件夹和文件时优先使用中文名；用户指定路径及系统接口契约优先。

直接检查确定性抽取：

```sh
python3.12 scripts/screenplay_core.py prepare /absolute/input.docx --output /absolute/work.json
python3.12 scripts/screenplay_core.py finalize /absolute/work.json --output-dir /absolute/out
```

`prepare` 的 `work.json` 是可审修中间物。`finalize` 拒绝未完成创作的纯细纲，避免把占位输出误称标准剧本。详细格式和审查边界见 references。
