# 资产表提取插件验收记录

日期：2026-10-20。目标：`screenplay-asset-extractor` 0.1.0，公开能力 `extract-asset-table`。

## 构建与契约

- 使用 Harness Creator 0.1.0 `build --confirmed` 构建，`doctor` 显示 Python 3.12.14、Codex CLI 可用，`validate` 返回 `valid: true`，1 个能力、2 个 Skill。
- `requirements.lock` 固定 Harness 依赖、`openpyxl==3.1.5` 和 `et_xmlfile==2.0.0`，均带 SHA-256。`asset_run.py` 可由本机默认 `python3` 找到插件的锁定运行时。
- `package` 生成 `screenplay-asset-extractor-0.1.0.zip`；解压到独立目录后再次 `validate`，并从解压目录完成 JSON → 四表 XLSX 的调用。ZIP 中无开发机绝对路径、虚拟环境或其他业务插件源码。
- Codex 本地市场安装检查返回 `screenplay-asset-extractor@screenplay-asset-extractor-local` 为 `installed: true`、`enabled: true`。

## 实际样例

三份“改造后标准剧本”DOCX 先由一级插件生成 `standardized_screenplay.json`。整稿均通过二级 `prepare` 和 `finalize` 的集场、来源及 Excel 结构检查；这一步是**整稿结构验收**，保守底稿尚未由 Agent 补全全部道具与角色层级。

| 样稿 | 整稿集/场 | 保守底稿人物/地点 | 前两集真实 Harness 调用：场/人物/地点/道具/特效/疑点 |
| --- | ---: | ---: | ---: |
| 《我是62岁男房东》 | 53/71 | 70/16 | 5/14/6/8/1/4 |
| 《荒年双穿：老太我靠火锅底料馋哭京城》 | 50/100 | 123/55 | 4/5/3/12/1/3 |
| 《龙王的狐族新娘》 | 25/37 | 25/24 | 2/7/1/2/2/3 |

三次前两集调用的 Harness run ID 分别为 `run-2fb234bfebec4255`、`run-3d56ebbd4e8f4988`、`run-79be2ae5c14a4b28`，状态均为 `completed/succeeded`。每次均交付四个相对产物路径，运行时记录文件 SHA-256。逐份复核 `assets.json` 与 XLSX 的四张核心表、可选特效表、场次数、资产状态及独立疑点数量一致。样稿本身不随公开插件打包。

另用三场合成小样完成真实 Agent 调用 `run-3e77b6f0814a40ea`：3 人物、1 场景、1 道具、1 特效、1 疑点，5 张工作表。核对了“云儿”与“阿云”的合法别名、蓝衫到红袍状态、主要动物、群演、声音需求、生成块证据，以及烧断局部锁链不拆整个场景状态。产物通过 Harness 路径与哈希校验。

`tests/run_acceptance.py` 独立验证 JSON 与 Excel 的人物/道具/特效及场次一致；无特效时只生成四张核心表；错误来源位置和无原文支持的“银白长发”均被阻止导出。

## 已修复的问题与边界

- 首次真实调用前新插件尚未安装，Agent 转找旧 Skill；本地市场安装后重新调用，入口加载正确。
- 第二次真实调用产生正确文件，但 envelope 使用绝对产物路径，被 Harness 拒收；Skill 契约改为四个相对文件名，后续四次真实调用均成功。
- 小样曾将“石门锁链烧断”误当整个场景的新状态；参考规则加了局部陈设反例，最终真实调用保持一个场景常态。
- 三份长剧本已做整稿结构验收与各前两集语义抽查；**尚未对三部全剧逐集完成人工语义资产核定**。人物身份、普通道具是否需独立制作、特殊效果的制作必要性仍可能需要项目方确认。插件把未证实的关系交付到独立疑点报告。
