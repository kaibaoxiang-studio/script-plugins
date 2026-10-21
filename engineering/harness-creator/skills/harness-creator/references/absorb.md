# 搜索、拆解与吸收

根据用户业务缺口查找候选，也接受用户提供的仓库、本地目录或解压包。搜索不是安装：先读 README、入口 Skill、Agent 配置、调用代码、references、依赖和测试，再评价它在当前任务中的价值。

可使用宿主搜索/GitHub 能力，或 `harness.py discover --query 'screenplay skill'`。脚本使用 GitHub 公共 API，不依赖 Creator 私有凭据；限流和不可访问结果应如实报告。用户可提供已下载目录。`fetch-source --repo OWNER/REPO --revision FULL_COMMIT_SHA --output NEW_DIRECTORY` 只下载固定提交，不运行安装器或 hooks。

`inspect-source --source DIRECTORY --origin URL --revision SHA --output inspection.json` 生成入口、文件哈希、许可文件和待阅读信号。它不决定候选安全或业务适用性，不能代替阅读代码。

## 集中改造方案

列明源版本、待解决问题、拟采纳文件与方法、需要改写的框架调用、放弃部分及理由、许可文件、目标能力和验证方法。用户确认方案后，选择：

- 从零建设时把改造后的 Skill、规则、代码和来源收据写入同一蓝图，再 build。
- 定点整合用 absorb recipe 与已有文件哈希，先验证候选，再提交 patch。
- 完整 Harness 改造先拆分入口、岗位、知识、执行、状态与工具，迁移到统一底座；将原框架调用留在源码里不算已迁移。

## absorb recipe

```json
{
  "origin":"https://github.com/owner/repository","revision":"exact commit or local content digest",
  "license":"MIT","adaptation":"提取指定方法，并转换成目标能力的纯 Python 函数",
  "selections":[{"source":"original.py","source_sha256":"inspected sha256",
    "target":"scripts/adapted.py","mode":"adapt","content":"complete authored code",
    "expected_target_sha256":null}],
  "license_files":[{"source":"LICENSE","source_sha256":"inspected sha256",
    "target":"licenses/upstream-MIT.txt","expected_target_sha256":null}]
}
```

copy 保留原文；adapt 提交改造后的完整内容；independent 需要 method_summary 说明方法研究与独立实现。复制或改造代码/文字需记录许可与随包许可文件。许可未知时只研究方法并独立编写，不能用改名掩盖复制。不要复制私有配置、密钥、原项目样例决定或无关运行时。

运行 `absorb --source DIR --plugin TARGET --recipe RECIPE --confirmed` 后核对 sources.lock.json，并执行当前能力相关样例。旧版本来源不因仓库出现新提交而自动更新。
