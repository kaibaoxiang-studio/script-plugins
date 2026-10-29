# JSON 资产提取的逐场语义审核

`prepare` 只登记人物表、说话人与地点，输出的不是完整资产表。Agent 必须逐场阅读动作与对白，补齐人物、场景、道具、独立特效、状态与疑点，再记录本文件规定的审核凭据。`finalize` 拒绝没有完成凭据的底稿；字段齐全的凭据仍不等于语义必然正确，应回查原文。

## 登记与留白

拿起、递交、使用、特写、剧情因果或持续损坏等均可支持道具登记，不要求全部同时成立。原文没写持有人、归属、材质、尺寸或变化时保留相应留白；没有变化就登记常态。只在对白里提到、并未出镜或要求制作的物件不直接入表，有必要时列出排除依据或疑点。固定陈设归场景，服装归人物状态，车辆归道具。

不要把“字段不完整”写成“没有资产”，也不要为填字段补造故事。零道具、零独立特效可以是正确结果，但必须通过全文审核得出。

## 工作文件字段

`work.semantic_review` 使用以下结构；下例是格式示意，ID、引文、结论都必须来自本次剧本与资产。

```json
{
  "schema_version": "asset_semantic_review_v1",
  "source_sha256": "与 work.source.sha256 一致",
  "assets_sha256": "当前 work.assets 的规范化 SHA256",
  "scenes": [
    {
      "scene_id": "1-1",
      "blocks": [
        {
          "block_index": 0,
          "source_refs": ["L3"],
          "origin": "source",
          "text": "林禾拿起铜钥匙",
          "asset_ids": ["CHR-001", "PRP-001"],
          "conclusion": "林禾实际拿取铜钥匙，两项均已登记。"
        }
      ],
      "categories": {
        "characters": {"asset_ids": ["CHR-001"], "conclusion": "林禾在动作中实际出镜。"},
        "locations": {"asset_ids": ["SCN-001"], "conclusion": "本场位于剧本标题指定的门廊。"},
        "props": {"asset_ids": ["PRP-001"], "conclusion": "铜钥匙实际拿取，需要道具资产。"},
        "effects": {"asset_ids": [], "conclusion": "本场只有实物动作，没有独立制作特效。"}
      },
      "exclusions": []
    }
  ]
}
```

- `scenes` 覆盖全部剧本场次，每场恰好一次，不能以已提取资产反推审阅范围。
- `blocks` 覆盖本场所有内容块，索引从 **0** 开始，每块一次。`source_refs` 与原块一致，`origin` 保持原值，`text` 引用该块真实文字片段。读完一块后写具体处理结论，不能批量填“已检查”。
- `asset_ids` 只引用已登记且实际分配到本场的资产。每场四类 `categories` 的 ID 集合与当前状态的场次分配一致。道具、特效还须关联到实际内容块，不能只列在总结中。
- 每类都写结论；空类说明本场为什么没有可独立登记项。不可把“未扫描”“未写细节”“为了保守”当成零结果依据。
- 排除有争议的候选物件时，在 `exclusions` 保存 `category`、具体 `reason` 和 `evidence`。证据仍使用 `{scene_id,text,source_refs,origin}`，不能虚构排除物或给未读文本批量下结论。
- 人物 `tier` 必须完成。证据不足的身份合并等进入疑点，不通过保留空层级绕过必要判断。

读完并完成上述内容后，才机械计算 `assets_sha256`。计算方法是 `hashlib.sha256(json.dumps(work['assets'], ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()`，包内也提供 `assets_digest(work['assets'])`。哈希函数只绑定当前数据，不会替你生成审核结论。

## 变更与兼容

修改来源必须重新 prepare、重新审核。修改资产、状态、特征或场次分配后，复核受影响记录，再更新资产哈希；不能只重算哈希掩盖未复核的修改。旧工作文件需要补齐审核记录后才能在新版正式导出。已有 `screenplay_assets_v1` 文件仍可作为历史交付读取，不把旧批准自动改成新版已审核。

正式导出的 `assets.json` 保留已验证审核信息供追溯，四个交付文件名及结果计数不变。上游 `source_coverage` 只描述原文映射，不代表资产语义提取完成。
