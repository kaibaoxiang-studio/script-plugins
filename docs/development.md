# 维护与发布

## 维护入口

| 组件 | 维护源码 | 安装快照 |
| --- | --- | --- |
| 一级 | level-1/screenplay-standardization/creator-src | 同级 screenplay-standardizer |
| 二级场记 | level-2/scene-log-extraction 的主 Skill、七个辅助 Skill、creator-src | 同级 scene-log-extractor |
| 二级资产 | level-2/asset-extraction/creator-src | 同级 screenplay-asset-extractor |
| 额外工程 | engineering/harness-creator | 工程本身也是完整插件 |

场记业务源码以团队 ai-continuity-sheet 仓库为维护上游，本仓保留本次可重建快照，具体提交见 release.json。修改时记录上游关系与来源，不只修改 Codex 安装缓存。

creator-src/PLUGIN-README.md 是独立插件 README 的构建模板，其中相对链接按生成后的插件根目录解析。阅读插件使用文档时进入同级安装快照目录。

## 修改与重新构建

1. 从 main 建分支，在维护源码修改规则、脚本、能力契约和合成样例。
2. 三个业务组件运行各自的 build_blueprint.py，更新蓝图；Harness Creator 直接维护工程。构建前先在独立候选目录复制该组件的源码布局，避免覆盖当前验收通过的安装快照。
3. 使用额外工程 Harness Creator 的 `harness.py build --spec ... --output ... --confirmed` 生成候选插件。相对目录需维持源码与输出同级关系。
4. 执行组件的构建后处理，再运行其确定性检查和相关真实 Agent 验收。
5. 验收通过后替换安装快照，更新版本、生成锁、来源及验证记录，再走 Pull Request。

| 组件 | 构建后处理 | 现有检查 |
| --- | --- | --- |
| 一级 | creator-src/publish_local_plugin.py：补选择器展示与本地市场 | creator-src 中 unittest discover -s tests -v |
| 场记 | creator-src/make_plugin_patch.py，再用 Harness patch；详见该目录 VALIDATION.md | 组件根目录 unittest discover -s creator-src/tests -v；verify_artifacts.py 检查业务交付 |
| 资产 | creator-src/postbuild.py，再按需 publish_local_plugin.py | creator-src/tests/run_acceptance.py |
| Creator | 直接维护工程 | 工程根目录 unittest discover -s tests -v |

publish_local_plugin.py 生成的局部市场位于组件 dist 下，作为本地开发产物，不随仓库提交。正式共享市场是根目录 .agents/plugins/marketplace.json。

build/patch 会校验并保护修改冲突。若后处理改变生成锁覆盖的文件，须在审阅明确变更内容后刷新对应哈希，并记录原因；不能用刷新锁掩盖未知差异。本版已记录此前展示信息和依赖后处理造成的旧锁差异，以及场记包新增中文 README，见[快照基线](validation/snapshot-baseline.json)。

## 仓库检查与打包

使用已装齐各插件锁定依赖的 Python 3.12+ 环境（包括 PyYAML、jsonschema、python-docx、openpyxl 等；版本与哈希以各 requirements.lock 为准）。在仓库根目录：

```sh
python3.12 scripts/release.py validate --output docs/validation/repository-checks.json
python3.12 scripts/release.py package --output dist/v1.0.0
```

检查包含四个组件身份、统一市场路径、生成锁、Python 语法、各自 validate/doctor。打包从已验收快照生成四个独立 ZIP；逐包解压、比对全部文件哈希并调用 validate。ZIP 不带 .venv、.harness、Git 元数据或测试运行缓存，源码及合成测试在仓库中维护。

项目版本由 VERSION 与 release.json 共同声明；组件版本独立维护。本次项目为 1.0.0，组件均为 0.1.0。业务代码改变时按组件版本策略更新，不能只改项目标签。

## 发布清单

- README、层级、输入输出和当前测试范围一致。
- 源码、安装快照与版本清单一致；无个人绝对路径、凭据或原始业务素材。
- 测试记录区分本次检查、既有真实调用和人工修订。
- Pull Request 合并后在对应提交创建版本标签。
- Release 上传四个 ZIP、逐文件 manifest 和 SHA256SUMS.txt。

本版未重写 Git 历史。旧三级规划、旧 capabilities 目录及被替代归档可从历史提交查看。
