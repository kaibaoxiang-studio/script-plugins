---
name: harness-skill-author
description: "为 Harness 插件编写和修改聚焦的 Agent Skills、references、Python 辅助脚本及真实验收样例。"
---

# Harness Skill Author

读取 [Skill 编写规范](../harness-creator/references/author.md)。依据已确认能力设计编写实际内容，输出可用初版。

SKILL.md 使用 YAML name 与 description 描述真实用途和触发条件；正文保留会改变决策的工作方法与边界。具体知识、格式细节和大段示例放 references，说明何时加载。重复的数据转换、文件操作和格式校验由实际可运行的 Python 脚本承担。

不要把泛泛建议、角色人设或现有单一案例变成所有业务的强制要求。输入不足时提出会改变结果的问题。明确文件输出契约和证据；占位函数、写死示例结果和仅返回“完成”的脚本不构成能力。

面向当前目标路径写文件，不依赖用户已安装的其他业务 Skill。使用 `build` 组装完整蓝图；运行脚本和相关样例，再交给主控检查。修改时先读已有文件，保留用户意图、授权及非本次修改内容。
