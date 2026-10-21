# 来源与改造

源码主仓库为 kaibaoxiang-studio/ai-continuity-sheet，改造基线提交 0c0750115477a6881e1b10650a5266aa9a665fdd。保留主 Skill、七个辅助 Skill、13 列表头和历史 Markdown 转 Excel 脚本；新增一级 JSON 接口、按场分拍/填写/连续性复核、结构化来源、整剧工作簿。旧版 jimeng-storyboard-v3 与 leos-six-department-directing-team-skill-v1 为运行时缺失依赖，现以包内阶段替代。Skill Orchestrator 仅用于角色分工方法评估，未拷贝其知识文件，也不是运行时依赖。
