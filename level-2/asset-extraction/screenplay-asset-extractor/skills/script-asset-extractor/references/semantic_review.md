# DOCX 入口的逐场语义审核

解析成功、人物/道具记录格式合法，只能证明数据可计算，不能证明已读完原文并完成资产判断。正式 `--check`、Excel 导出、展示计划导出和保存后验收都要求 `assets.json.semantic_review`。同步人物/道具场次仍是中间步骤，不自动产生审核结论。

## 实际工作

1. 通读解析后的每场人物行和全部 `lines`，判断实际出镜、物件使用、身份连续和状态变化。分批读到的内容要形成行级结论，不等到导出时从既有清单反推“全都已审”。
2. 在三类资产合并、人物/道具场次同步后，核对每场类别汇总。某类没有资产也填写本场具体结论；“未提供外观/持有人/变化”不能代替对物件是否出镜的判断。
3. 发现候选但不独立立项时记录原文与排除理由，例如固定桌子归场景、对白仅提及未出镜。无排除项写空数组。不存在的身份、所有权、材质仍留空，不能为通过校验编造。
4. 完成审核后计算来源与资产快照哈希。来源或三类资产的任何数据变化，旧审核都会失效，须重看受影响记录，再绑定当前完整快照。不能只刷新哈希而不复核。

## 数据骨架

```json
{
  "semantic_review": {
    "schema_version": "asset_semantic_review_v1",
    "source_sha256": "规范 scenes.json 数据的 SHA256",
    "assets_sha256": "三类资产数据的 SHA256",
    "scenes": [
      {
        "scene_id": "1-1",
        "lines": [
          {
            "line": 1,
            "quote": "一只手拿起铜钥匙，把手机放在桌上。",
            "asset_ids": ["SCN-001", "PRP-001", "PRP-002"],
            "conclusion": "钥匙被拿起、手机被放下，分别关联两件实物；桌子为固定陈设归房间。"
          }
        ],
        "categories": {
          "characters": {"asset_ids": [], "conclusion": "本场只拍手部，未给独立角色身份，不新增人物资产。"},
          "scenes": {"asset_ids": ["SCN-001"], "conclusion": "本场房间由已登记主场景覆盖，桌子归该场景。"},
          "props": {"asset_ids": ["PRP-001", "PRP-002"], "conclusion": "拿取及放置动作分别使用钥匙与手机，保持独立实物。"}
        },
        "exclusions": [
          {"category": "props", "reason": "桌子是固定陈设，归入场景，不单独立道具。", "evidence": [{"scene_id": "1-1", "line": 1, "quote": "桌上"}]}
        ]
      }
    ]
  }
}
```

示例仅解释合同，不是可复制到真实剧本的审核结果。这里 `scenes` 类别对应 DOCX 格式的场景资产；JSON 兼容入口使用 `locations`，其证据结构也不同，不能直接混用。

`line` 从 1 起，与当前场 `lines` 数组对应。每行必须出现且只能出现一次；`quote` 必须是该行完整原文，保留整句中可能被遗漏的物件线索。每行 `conclusion` 写实际取舍，不填“已完成”占位。

每场的 `categories` 必须恰有 `characters`、`scenes`、`props` 三类；各类 `asset_ids` 必须等于实际分配到本场状态/子场景的 ID 集合。行级 ID 不能引用本场没有状态/子场景的资产；每个道具出镜 `mentions` 的原文行必须关联该道具 ID。对白仅提及且本场未展示的物件，不因行级名称命中升级为出镜资产，应在该行结论和必要的排除记录中说明。

角色无服装变化、道具无破损时都可使用常态。单独不知道所有者或持有人，不影响有证据的实际物件登记。出镜、身份不确定与外观未说明是不同问题。

## 快照算法与导出

`scripts/semantic_review.py` 提供只做确定性操作的两个函数：

```python
from semantic_review import canonical_sha256, asset_snapshot
review["source_sha256"] = canonical_sha256(scenes_data)
review["assets_sha256"] = canonical_sha256(asset_snapshot(assets))
```

两者都按 `json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')` 计算 SHA256。来源绑定整个解析数据，资产绑定 `characters/scenes/props`，不包含审核对象本身。输入 JSON 的缩进变化不导致语义快照失效。

函数不负责阅读、判断或批准；没有一键生成已审结论的命令。旧项目缺少审核记录时仍可读取、回查、同步，但不能新导出正式文件；须回到原文补审核，不能从旧 Excel/状态列表伪造“已读完”。确实没有道具的剧本经逐场复核可以正常交付，数量大于零不是门槛。

这套检查能拒绝漏场、漏行、空结论、错引用和过期快照，不能证明每句自然语言判断必然正确。交付前仍须检查明确拿取、递交、特写和变化的物件是否得到合理处理；真实能力验收与这些结构检查分别记录。
