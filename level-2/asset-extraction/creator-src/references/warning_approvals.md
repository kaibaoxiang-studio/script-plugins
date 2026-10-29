# 具体警告的用户确认

先修复所有错误、漏提与错误归属。仅当警告经原文回查确有合理解释，且用户已明确确认该条可忽略时，才能建立确认记录。开发本技能或要求修复脚本的授权，不等于批准将来剧本里的任何警告。

例如道具被他人临时拿着，归属人物没在人物行出现，可保留原始数据和警告，把具体场次、原文解释交给用户确认。不得为了通过校验改写人物行、批量忽略所有警告，或代用户填写未经批准的确认。

## 生成报告

先完成人物逐场记录、道具实物记录和候选复核，依次运行 --sync-character-scenes、--sync-prop-scenes，再执行下列报告命令。同步会改变资产输入，必须在生成确认摘要之前完成：

```bash
python3 $S/build_xlsx.py <scenes.json> <assets.json> --warning-report
```

返回 JSON 包含当前输入的 source_digest、空 approvals、warnings 中的警告 ID/完整 message，以及 errors。报告只供核对，没有预先确认任何警告；有错误时命令非零退出。

## 保存已确认条目

用户对具体条目授权后，在工作目录保存 warning_approvals.json。source_digest 和 warning_id/message 从当前报告原样复制；reason 记录原文回查依据及用户确认内容，confirmed_by 记录实际确认人，不得凭空填写。

```json
{
  "source_digest": "从当前报告原样复制的输入摘要",
  "approvals": [
    {
      "warning_id": "从报告原样复制的警告编号",
      "message": "该条完整警告文字",
      "reason": "具体场次原文表明由他人持有；用户已明确确认该条可忽略。",
      "confirmed_by": "实际确认人"
    }
  ]
}
```

可以保留报告中的 warnings/errors 字段用于审阅，但只有 approvals 内的精确匹配条目被确认。重复编号、空理由、错误 message、未知警告、格式错误均阻止导出。

## 校验和导出

```bash
python3 $S/build_xlsx.py <scenes.json> <assets.json> --check --warning-approvals <warning_approvals.json>
python3 $S/build_xlsx.py <scenes.json> <assets.json> <输出.xlsx> --warning-approvals <warning_approvals.json>
```

错误不能被确认覆盖；未确认警告仍阻止导出。控制台分别显示错误、未确认警告、已确认警告数量。Excel 场次总表的“校验确认”列保存具体警告、确认人和依据；全局警告放到首场行，不丢失确认记录。

确认绑定完整 scenes.json 和 assets.json 的逻辑内容，不受 JSON 缩进影响。任何输入内容修改后摘要改变，旧确认文件失效；必须重新报告、回查和确认，不能直接换摘要冒用旧确认。确认文件保存在工作目录，用于复核；正式交付仍为 assets.json 和资产表 Excel。
