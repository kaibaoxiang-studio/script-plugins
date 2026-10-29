# 道具实物身份、异称与场次

## 判读原则

名称不是实物身份。先通读全剧，整理特指名称、简称、泛称和代词的实际出现位置，再判断属于哪件实物；不要先按名称建表再仅凭名称相似度去重。

- 明确同义说明：原文直接说明两种名称指同一物品。
- 连续交接：取出、拿着、递交、接过、使用形成无歧义的实物链，期间没有出现另一件同类物。
- 独特特征：同一特殊刻纹、缺口、编号等组合，结合持有与情境支持同物。常见材质、颜色、类型、同一持有人或相邻场次本身不足以确认。
- 同名不同物、仿制品、替换件、同套中的不同单件、容器与内容物不因名称相近而合并。原文只有集合且不区分个体时可保留集合道具，不凭空拆件。
- 证据不足则保留独立 ID，用 identity_relations 记录 uncertain，并在 note 写待确认场次与问题；不能为了减少重复项而猜测。

确认同物后采用一个稳定的原文特指主名 name，其他已确认特指名称写 aliases。泛称如“匕首”、局部称呼如“这把匕首”和代词“它”只写 mentions.raw_name，不作全剧 aliases。脚本列出的泛称并非完整词典，未被程序拦截的普通词也须按这一原则判读。

“登记本”等通用物件类别即使在一段中能确定指代，也不因此成为全剧特指异称：保留当地 raw_name，以 contextual/from 和该段引入记录证明实物归属。

同名不同实物使用带原文区别的展示名，如“匕首·凯尔”“匕首·莱拉”；展示限定词不当作原文引文。展示名与原文不同，必须用 source_name 保存未经限定的原文主称呼，如 name="屠龙匕首·凯尔"、source_name="屠龙匕首"。source_name 须关联实际 named/introduced 原文记录；不同实物可以共用 source_name，但不能共用 name/全局 aliases，检索命中仍须逐次判读归属。未设置 source_name 的旧数据默认使用 name，并补查 introduced 中已记录的非泛称；不能靠删记录逃避漏提检查。首次原文只有“匕首”时用 introduced 建立身份。holder 记录当次持有者，owner 记录主要归属；转手不换 ID、不拆状态，断裂等实际外观变化在同一 ID 下拆状态。

## 回查与记录

```bash
python3 $S/show_prop.py <scenes.json> <assets.json> --related
python3 $S/show_prop.py <scenes.json> <assets.json> PRP-001 --terms 龙骨匕首 匕首 它
python3 $S/show_prop.py <scenes.json> <assets.json> PRP-001 --json
```

工具只读，输出候选或整场上下文，不自动合并。--related 的同类型候选可能是不同物件；--terms 的泛称/代词可能指向其他资产。候选搜索仅覆盖已知称呼，不能发现所有未知异称，仍要通读相关动作并补充原文称呼清单。

每次实际称呼对应一条 mentions，按剧本呈现顺序、行号、字符位置排列。source.line 从该场 lines 数组的 1 开始；offset 从对应 line.text 的 0 开始，end_offset 不包含末端字符，按 Python 字符计数。raw_name 必须是该区间的原文，不用主名替换。

| 字段 | 含义 |
| --- | --- |
| id | 同一道具内唯一的 M001 等记录号 |
| source | scene_id、line、quote；quote 为该行真实原文，建议整行 |
| raw_name / start_offset / end_offset | 当地原文称呼及精确位置，同一词区间不能由两个出镜道具重复认领 |
| timeline | 有原文依据的实物连续段；闪回、梦境、跳时须重判，不为通过检查虚构段名 |
| basis=named | 使用 source_name（未填写时默认 name）或已确认 aliases 的原文特指称呼 |
| basis=introduced | 首次明确引入或独立重建实物身份；identity_reason 解释原文如何区分，不用它绕过有歧义的指代 |
| basis=contextual | 泛称/代词的局部指代；from 指向同一道具、同连续段的先前记录，identity_refs 包含该记录 source，identity_reason 解释交接或指代 |
| visibility=visible | 动作原文确有画面，state_id 必须指向实际外观状态 |
| visibility=reference | 台词/画外音等仅提及、未展示；state_id=null，note 写排除理由，不计场次 |
| holder / note | 当次持有者和局部疑点；未知持有者可为空 |

动作行内的“提到”“想起”也可能只是引用，不自动判为 visible。台词伴随可见动作时用独立动作依据记录画面；若解析器把舞台动作混入台词，先人工复核解析结构，不把台词名称命中直接当作出镜。

aliases 每项均须有 alias_evidence：alias、basis（explicit / continuity / distinctive）、reason、evidence_refs。explicit 的真实说明须同时包含两个独立称呼；另两类依据至少覆盖两个独立原文字符位置，包含该异称和原文主名/首次实物引入侧。同一行明确交接并改称时可引用该行，但两侧 mentions 必须指向不重叠的字符区间，引文须包含对应称呼。两个称呼出现在同一行本身不证明同物，仍须判读交接或独特特征，不能只用异称自身循环证明身份。

identity_relations 包含 other_id、decision（distinct / uncertain）、reason、evidence_refs。distinct 须有原文依据，uncertain 须同步在资产 note 标明疑点。脚本验证位置与结构，不能证明理由在语义上成立。

## 完整格式示例

以下示例对应动作原文 1-1:L1“凯尔拔出屠龙匕首。”、1-2:L1“凯尔把屠龙匕首又称作龙骨匕首。”、1-3:L1“莱拉接过这把匕首。”。示例只说明结构，不是输入剧本的事实。字符位置须对实际原文重新计算。

```json
{
  "id": "PRP-001",
  "name": "屠龙匕首",
  "source_name": "屠龙匕首",
  "aliases": ["龙骨匕首"],
  "owner": "凯尔",
  "description": "剧本未说明具体材质与尺寸，待设计确认。",
  "note": "",
  "alias_evidence": [{
    "alias": "龙骨匕首",
    "basis": "explicit",
    "reason": "原文明确又称作，指同一实物。",
    "evidence_refs": [{"scene_id": "1-2", "line": 1, "quote": "凯尔把屠龙匕首又称作龙骨匕首。"}]
  }],
  "identity_relations": [],
  "mentions": [
    {"id": "M001", "source": {"scene_id": "1-1", "line": 1, "quote": "凯尔拔出屠龙匕首。"}, "raw_name": "屠龙匕首", "start_offset": 4, "end_offset": 8, "basis": "named", "timeline": "连续段1", "visibility": "visible", "state_id": "S01", "holder": "凯尔", "note": ""},
    {"id": "M002", "source": {"scene_id": "1-2", "line": 1, "quote": "凯尔把屠龙匕首又称作龙骨匕首。"}, "raw_name": "屠龙匕首", "start_offset": 3, "end_offset": 7, "basis": "named", "timeline": "连续段1", "visibility": "reference", "state_id": null, "note": "仅说明名称，未新增画面展示。"},
    {"id": "M003", "source": {"scene_id": "1-2", "line": 1, "quote": "凯尔把屠龙匕首又称作龙骨匕首。"}, "raw_name": "龙骨匕首", "start_offset": 10, "end_offset": 14, "basis": "named", "timeline": "连续段1", "visibility": "reference", "state_id": null, "note": "同一名称说明，不计画面场次。"},
    {"id": "M004", "source": {"scene_id": "1-3", "line": 1, "quote": "莱拉接过这把匕首。"}, "raw_name": "这把匕首", "start_offset": 4, "end_offset": 8, "basis": "contextual", "timeline": "连续段1", "from": "M001", "identity_refs": [{"scene_id": "1-1", "line": 1, "quote": "凯尔拔出屠龙匕首。"}], "identity_reason": "连续段接过此前凯尔拔出的唯一匕首，未引入另一实物。", "visibility": "visible", "state_id": "S01", "holder": "莱拉", "note": ""}
  ],
  "states": [{"id": "S01", "name": "常态", "description": "具体外观未说明。", "scenes": ["1-1", "1-3"], "evidence": "1-1:L1 凯尔拔出屠龙匕首。", "note": ""}]
}
```

## 合并、迁移与导出

确定同一实物的旧重复项后保留该实物最早的有效 ID，先列旧 ID→保留 ID 映射，再移动异称及证据、实物记录。同一外观状态可归一，完整与断裂不能混为一个状态。重新分配资产内唯一记录号/状态号，更新 from、state_id、identity_relations.other_id 以及所有引用，完成全剧核对后才移除旧重复项。脚本不会替你自动执行合并。

旧版 props 只有 states[].scenes 时必须重读原文补 mentions 与异称证据，不能从旧列表伪造记录。结构骨架中的空 mentions/states 仅为提取起点，不是可校验交付数据。缺少或为空的 states 会阻止同步与导出；从未实际出镜、只被提及的物品不作为道具资产交付，已出镜道具的非画面提及仍保留 reference。

```bash
python3 $S/build_xlsx.py <scenes.json> <assets.json> --sync-prop-scenes
python3 $S/build_xlsx.py <scenes.json> <assets.json> --check
```

states[].scenes 只从 visible 记录派生，按剧本顺序去重；同场断裂前后可分别有两个状态记录，但每个状态只计该场一次。同步不修改身份判读、不选状态，遇到错误不写回。已确认的非泛称在原文中的每次名称命中均需被实物记录覆盖，或明确记录为 reference；这项检查不等于发现所有未知异称，也不证明某泛称归属正确。

Excel 道具表保留统一主名、异称与身份依据及单次备注，场次总表保留当地原文称呼。导出后抽查跨称呼、交接、同名不同物、破损前后和仅提及场次；有疑问先改实物记录、同步校验，再生成。
