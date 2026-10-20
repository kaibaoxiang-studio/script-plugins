#!/usr/bin/env python3
"""Evidence-first asset extraction from standardized_screenplay_v1.

prepare SOURCE --output WORK_JSON creates a conservative, editable work file.
finalize WORK_JSON --output-dir DIR validates it and renders JSON/XLSX/findings.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re


TIERS = {"主角", "重要角色", "配角", "功能角色", "群演"}
KINDS = (("characters", "人物", "CHR"), ("locations", "场景", "SCN"),
         ("props", "道具", "PRP"), ("effects", "特效", "VFX"))
VISUAL_PACK = ("头像", "全身图", "四视图执行资产图", "九宫格表情")
FOUR_VIEW = "正面头像、侧面头像、正面全身、背面全身"


def read_json(path: str | Path) -> dict:
    with Path(path).open(encoding="utf-8") as stream:
        return json.load(stream)


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def scene_order(scene_id: str) -> tuple[int, int]:
    match = re.fullmatch(r"(\d+)-(\d+)", scene_id)
    if not match:
        raise ValueError(f"无效场号：{scene_id}")
    return int(match[1]), int(match[2])


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def checked_screenplay(source: dict) -> list[dict]:
    require(source.get("schema_version") == "standardized_screenplay_v1", "输入须为一级 standardized_screenplay_v1 JSON")
    require(not source.get("needs_creative_pass"), "一级细纲创作尚未完成")
    episodes = source.get("episodes")
    require(isinstance(episodes, list) and episodes, "缺少非空 episodes")
    seen: set[str] = set()
    scenes: list[dict] = []
    for episode in episodes:
        require(isinstance(episode.get("number"), int), "集号缺失")
        for scene in episode.get("scenes", []):
            sid = scene.get("number")
            require(isinstance(sid, str), "场号缺失")
            require(scene_order(sid)[0] == episode["number"], f"{sid} 与集号不符")
            require(sid not in seen, f"重复场号：{sid}")
            seen.add(sid)
            require(isinstance(scene.get("location"), str) and scene["location"].strip(), f"{sid} 缺少地点")
            require(isinstance(scene.get("characters", []), list), f"{sid} 人物表无效")
            require(isinstance(scene.get("blocks"), list), f"{sid} 内容块无效")
            refs = scene.get("source_refs", [])
            require(isinstance(refs, list) and refs, f"{sid} 缺少来源位置")
            for block in scene["blocks"]:
                require(block.get("origin") in {"source", "generated"}, f"{sid} 内容块 origin 无效")
                require(isinstance(block.get("source_refs"), list) and block["source_refs"], f"{sid} 内容块缺少来源位置")
            scenes.append({"scene_id": sid, "episode": episode["number"],
                           "episode_title": episode.get("title", ""),
                           "location": scene["location"].strip(),
                           "interior_exterior": scene.get("interior_exterior", ""),
                           "time": scene.get("time", ""),
                           "source_heading": scene.get("source_heading", ""),
                           "characters": scene.get("characters", []),
                           "source_refs": refs, "blocks": scene["blocks"]})
    require(bool(scenes), "剧本没有场次")
    return scenes


def evidence(scene: dict, *, text: str, refs: list[str], origin: str) -> dict:
    return {"scene_id": scene["scene_id"], "text": text, "source_refs": list(dict.fromkeys(refs)),
            "origin": origin}


def cast_evidence(scene: dict, name: str, input_kind: str) -> dict:
    for block in scene["blocks"]:
        if block.get("type") == "dialogue" and block.get("speaker") == name:
            return evidence(scene, text=name + "：" + block.get("text", ""),
                            refs=block["source_refs"], origin=block["origin"])
        if name in block.get("text", "") and block.get("type") == "action":
            return evidence(scene, text=block["text"], refs=block["source_refs"], origin=block["origin"])
    return evidence(scene, text="人物表：" + name, refs=scene["source_refs"],
                    origin="generated" if input_kind == "outline" else "source")


def initial_work(source_path: Path) -> dict:
    source = read_json(source_path)
    scenes = checked_screenplay(source)
    characters: dict[str, dict] = {}
    locations: dict[str, dict] = {}
    for scene in scenes:
        sid = scene["scene_id"]
        names = list(dict.fromkeys([*scene["characters"], *[b.get("speaker", "") for b in scene["blocks"]
                                                       if b.get("type") == "dialogue"]]))
        for name in names:
            name = name.strip()
            if not name:
                continue
            ev = cast_evidence(scene, name, source.get("input_kind", "script"))
            if name not in characters:
                cid = f"CHR-{len(characters) + 1:03d}"
                characters[name] = {"id": cid, "name": name, "aliases": [], "alias_evidence": [],
                                    "asset_type": "人物", "tier": "", "script_facts": [],
                                    "evidence": [ev], "states": [{"id": "S01", "name": "常态",
                                                           "script_facts": [], "scenes": [sid], "evidence": [ev]}],
                                    "extra_requirements": []}
            else:
                characters[name]["states"][0]["scenes"].append(sid)
                characters[name]["evidence"].append(ev)
        loc = scene["location"]
        ev = evidence(scene, text=scene["source_heading"] or loc,
                      refs=scene["source_refs"],
                      origin="generated" if source.get("input_kind") == "outline" else "source")
        if loc not in locations:
            lid = f"SCN-{len(locations) + 1:03d}"
            locations[loc] = {"id": lid, "name": loc, "aliases": [], "alias_evidence": [],
                              "script_facts": [], "evidence": [ev],
                              "subscenes": [{"name": loc, "scenes": [sid], "evidence": [ev]}],
                              "states": [{"id": "S01", "name": "常态", "script_facts": [],
                                          "scenes": [sid], "evidence": [ev]}]}
        else:
            locations[loc]["subscenes"][0]["scenes"].append(sid)
            locations[loc]["states"][0]["scenes"].append(sid)
            locations[loc]["evidence"].append(ev)
    return {"schema_version": "asset_extraction_work_v1",
            "source": {"path": str(source_path.resolve()),
                       "sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
                       "source_manifest": source.get("source_manifest", {}),
                       "input_kind": source.get("input_kind", "script")},
            "scenes": scenes,
            "assets": {"characters": list(characters.values()), "locations": list(locations.values()),
                       "props": [], "effects": []},
            "findings": [],
            "source_coverage": source.get("coverage", {})}


def all_refs(scene: dict) -> set[str]:
    return set(scene["source_refs"]) | {ref for block in scene["blocks"] for ref in block["source_refs"]}


def validate_evidence(entries: list[dict], label: str, scene_map: dict[str, dict],
                      input_kind: str = "script") -> None:
    require(isinstance(entries, list) and bool(entries), f"{label} 缺少证据")
    for ev in entries:
        sid = ev.get("scene_id")
        require(sid in scene_map, f"{label} 证据引用不存在场次 {sid}")
        refs = ev.get("source_refs")
        require(isinstance(refs, list) and refs and set(refs) <= all_refs(scene_map[sid]),
                f"{label} 证据来源位置无效：{sid}")
        require(ev.get("origin") in {"source", "generated"}, f"{label} 证据生成标记无效")
        require(isinstance(ev.get("text"), str) and ev["text"].strip(), f"{label} 证据文字为空")
        scene = scene_map[sid]
        supported = False
        for block in scene["blocks"]:
            if set(refs) <= set(block["source_refs"]) and ev["origin"] == block["origin"]:
                displayed = (block.get("speaker", "") + "：" if block.get("type") == "dialogue" else "") + block.get("text", "")
                if ev["text"] in displayed:
                    supported = True
                    break
        structure_origin = "generated" if input_kind == "outline" else "source"
        if ev["origin"] == structure_origin and set(refs) <= set(scene["source_refs"]):
            if ev["text"] in (scene["source_heading"] or scene["location"]):
                supported = True
            if ev["text"].startswith("人物表：") and ev["text"][4:] in scene["characters"]:
                supported = True
        require(supported, f"{label} 证据文字或 origin 与 {sid} 内容不符")


def validate_work(work: dict) -> tuple[dict[str, dict], list[dict]]:
    require(work.get("schema_version") == "asset_extraction_work_v1", "工作文件版本错误")
    source_path = Path(work["source"]["path"])
    require(source_path.is_file(), "一级 JSON 来源文件不存在")
    require(hashlib.sha256(source_path.read_bytes()).hexdigest() == work["source"]["sha256"],
            "一级 JSON 已变化，请重新 prepare")
    source_scenes = checked_screenplay(read_json(source_path))
    require(work.get("scenes") == source_scenes, "工作文件中的剧本场次被改动")
    scene_map = {s["scene_id"]: s for s in source_scenes}
    assets = work.get("assets", {})
    warnings: list[dict] = []
    ids: set[str] = set()
    all_names: dict[tuple[str, str], str] = {}
    input_kind = work["source"].get("input_kind", "script")
    for key, label, prefix in KINDS:
        require(isinstance(assets.get(key), list), f"缺少 {label} 数组")
        for asset in assets[key]:
            aid = asset.get("id")
            require(isinstance(aid, str) and re.fullmatch(prefix + r"-\d{3,}", aid) and aid not in ids,
                    f"{label} ID 无效或重复：{aid}")
            ids.add(aid)
            name = asset.get("name")
            require(isinstance(name, str) and name.strip(), f"{aid} 名称为空")
            validate_evidence(asset.get("evidence", []), aid, scene_map, input_kind)
            if key == "characters":
                require(asset.get("asset_type") in {"人物", "主要动物", "群演组"}, f"{aid} 人物类型无效")
                tier = asset.get("tier", "")
                require(tier in TIERS | {""}, f"{aid} 层级无效")
                if not tier:
                    warnings.append({"code": "tier_unset", "asset_id": aid,
                                     "message": f"{name} 尚未判定角色层级；制作套件暂按实际发声需求登记",
                                     "source_refs": asset["evidence"][0]["source_refs"]})
            for fact in asset.get("script_facts", []):
                validate_evidence(fact.get("evidence", []), f"{aid} 事实", scene_map, input_kind)
                require(isinstance(fact.get("text"), str) and fact["text"].strip(), f"{aid} 事实文字为空")
                require(any(fact["text"] in ev["text"] for ev in fact["evidence"]),
                        f"{aid} 事实不是证据原文片段")
            aliases = asset.get("aliases", [])
            require(isinstance(aliases, list) and all(isinstance(x, str) and x.strip() for x in aliases),
                    f"{aid} 别名格式错误")
            alias_evidence = asset.get("alias_evidence", [])
            for alias in aliases:
                matched = [item for item in alias_evidence if item.get("name") == alias]
                require(len(matched) == 1, f"{aid} 别名 {alias} 缺少唯一证据")
                validate_evidence(matched[0].get("evidence", []), f"{aid} 别名 {alias}", scene_map, input_kind)
                require(any(alias in ev["text"] for ev in matched[0]["evidence"]), f"{aid} 别名缺少原文称谓")
            for alias in [name, *aliases]:
                normalized = alias.strip()
                if key in {"characters", "locations"}:
                    name_key = (key, normalized)
                    require(name_key not in all_names or all_names[name_key] == aid,
                            f"别名 {normalized} 指向不同资产，请先拆分或报告疑点")
                    all_names[name_key] = aid
            states = asset.get("states", [])
            require(isinstance(states, list) and states, f"{aid} 没有状态")
            state_ids: set[str] = set()
            assigned: set[str] = set()
            for state in states:
                state_id = state.get("id")
                require(isinstance(state_id, str) and re.fullmatch(r"S\d{2,}", state_id)
                        and state_id not in state_ids, f"{aid} 状态 ID 无效或重复")
                state_ids.add(state_id)
                state_scenes = state.get("scenes")
                require(isinstance(state_scenes, list) and state_scenes, f"{aid}-{state_id} 未分配场次")
                for sid in state_scenes:
                    require(sid in scene_map, f"{aid}-{state_id} 引用不存在场次 {sid}")
                    require(sid not in assigned, f"{aid} 场次 {sid} 被重复分配状态")
                    assigned.add(sid)
                validate_evidence(state.get("evidence", []), f"{aid}-{state_id}", scene_map, input_kind)
                require(any(ev["scene_id"] in state_scenes for ev in state["evidence"]),
                        f"{aid}-{state_id} 触发证据不在所分配场次")
                for fact in state.get("script_facts", []):
                    validate_evidence(fact.get("evidence", []), f"{aid}-{state_id} 事实", scene_map, input_kind)
                    require(any(fact["text"] in ev["text"] for ev in fact["evidence"]),
                            f"{aid}-{state_id} 事实不是证据原文片段")
            if key == "locations":
                subscenes = asset.get("subscenes", [])
                require(isinstance(subscenes, list) and subscenes, f"{aid} 没有子场景")
                sub_ids: set[str] = set()
                for sub in subscenes:
                    require(sub.get("name"), f"{aid} 子场景无名称")
                    validate_evidence(sub.get("evidence", []), f"{aid} 子场景", scene_map, input_kind)
                    for sid in sub.get("scenes", []):
                        require(sid in scene_map, f"{aid} 子场景引用不存在场次 {sid}")
                        sub_ids.add(sid)
                require(sub_ids == assigned, f"{aid} 子场景与状态场次不一致")
    # Bidirectional cast-state and scene-location checks from the original skill.
    chars = {name: asset for asset in assets["characters"] for name in [asset["name"], *asset.get("aliases", [])]}
    locs = {name: asset for asset in assets["locations"] for name in [asset["name"], *asset.get("aliases", [])]}
    for sid, scene in scene_map.items():
        expected = set(scene["characters"]) | {b.get("speaker") for b in scene["blocks"]
                                                  if b.get("type") == "dialogue" and b.get("speaker")}
        for name in expected:
            require(name in chars, f"{sid} 人物 {name} 无资产")
            require(sum(sid in st["scenes"] for st in chars[name]["states"]) == 1,
                    f"{sid} 人物 {name} 未分配唯一状态")
        for asset in assets["characters"]:
            if any(sid in st["scenes"] for st in asset["states"]):
                require(bool(expected & {asset["name"], *asset.get("aliases", [])}) or
                        any(asset["name"] in b.get("text", "") for b in scene["blocks"] if b.get("type") == "action"),
                        f"{sid} 人物 {asset['name']} 被分配状态但无出场依据")
        require(scene["location"] in locs, f"{sid} 地点 {scene['location']} 无资产")
        require(sum(sid in st["scenes"] for st in locs[scene["location"]]["states"]) == 1,
                f"{sid} 地点未分配唯一状态")
    for finding in work.get("findings", []):
        validate_evidence(finding.get("evidence", []), "疑点", scene_map, input_kind)
    return scene_map, warnings


def voice_needed(asset: dict, scene_map: dict[str, dict]) -> tuple[bool, list[dict]]:
    names = {asset["name"], *asset.get("aliases", [])}
    results = []
    for scene in scene_map.values():
        for block in scene["blocks"]:
            if block.get("type") == "dialogue" and block.get("speaker") in names:
                results.append(evidence(scene, text=block["text"], refs=block["source_refs"],
                                        origin=block["origin"]))
            elif block.get("type") == "action" and any(
                    re.search(re.escape(name) + r"[^。；，]{0,12}(?:叫|喊|吼|啼|鸣|哭|笑出声|尖叫)",
                              block.get("text", "")) for name in names):
                results.append(evidence(scene, text=block["text"], refs=block["source_refs"],
                                        origin=block["origin"]))
    return bool(results), results


def requirements_for(asset: dict, scene_map: dict[str, dict]) -> list[dict]:
    requirements = []
    tier = asset.get("tier", "")
    if tier in {"主角", "重要角色"}:
        for state in asset["states"]:
            for kind in VISUAL_PACK[:3]:
                requirements.append({"type": kind, "state_id": state["id"],
                                     "description": FOUR_VIEW if kind == "四视图执行资产图" else "",
                                     "basis": "role_tier", "evidence": state["evidence"]})
        requirements.append({"type": "九宫格表情", "state_id": asset["states"][0]["id"],
                             "description": "", "basis": "role_tier", "evidence": asset["evidence"][:1]})
    for item in asset.get("extra_requirements", []):
        require(item.get("type") in {*VISUAL_PACK, "声音"}, f"{asset['id']} 制作需求类型无效")
        require(item.get("state_id") in {st["id"] for st in asset["states"]} | {None, ""},
                f"{asset['id']} 制作需求状态无效")
        if item.get("basis") == "script":
            validate_evidence(item.get("evidence", []), f"{asset['id']} 制作需求", scene_map)
        else:
            require(item.get("basis") == "production", f"{asset['id']} 制作需求缺少依据类型")
        requirements.append(item)
    has_voice, voice_evidence = voice_needed(asset, scene_map)
    if has_voice and not any(r["type"] == "声音" for r in requirements):
        requirements.append({"type": "声音", "state_id": None, "description": "",
                             "basis": "script", "evidence": voice_evidence})
    return requirements


def finalize(work_path: Path, output_dir: Path) -> dict:
    work = read_json(work_path)
    scene_map, warnings = validate_work(work)
    assets = deepcopy(work["assets"])
    for asset in assets["characters"]:
        asset["requirements"] = requirements_for(asset, scene_map)
    report = {"schema_version": "asset_findings_v1", "source": work["source"],
              "findings": [*work.get("findings", []), *warnings]}
    coverage = work.get("source_coverage", {})
    if coverage.get("unassigned_source_refs"):
        report["source_unassigned_refs"] = coverage["unassigned_source_refs"]
    result = {"schema_version": "screenplay_assets_v1", "source": work["source"],
              "characters": assets["characters"], "locations": assets["locations"],
              "props": assets["props"], "effects": assets["effects"],
              "scenes": [{"scene_id": s["scene_id"], "episode": s["episode"],
                          "episode_title": s["episode_title"], "location": s["location"],
                          "interior_exterior": s["interior_exterior"], "time": s["time"],
                          "characters": s["characters"], "source_refs": s["source_refs"]}
                         for s in scene_map.values()]}
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "assets.json", result)
    write_json(output_dir / "asset_findings.json", report)
    lines = ["# 资产提取疑点", "", f"共 {len(report['findings'])} 条。", ""]
    for index, finding in enumerate(report["findings"], 1):
        refs = finding.get("source_refs") or [ref for ev in finding.get("evidence", [])
                                              for ref in ev.get("source_refs", [])]
        lines += [f"## {index}. {finding.get('message', finding.get('code', '疑点'))}", "",
                  f"来源：{', '.join(dict.fromkeys(refs))}", ""]
        for ev in finding.get("evidence", [])[:2]:
            lines += [f"证据（{ev['scene_id']}，{ev['origin']}）：{ev['text'][:180]}", ""]
    if report.get("source_unassigned_refs"):
        lines += ["## 一级剧本未映射的来源段落", "",
                  ", ".join(report["source_unassigned_refs"]), ""]
    (output_dir / "asset_findings.md").write_text("\n".join(lines), encoding="utf-8")
    from asset_xlsx import render_workbook
    render_workbook(result, output_dir / "screenplay-asset-table.xlsx")
    return {"characters": len(result["characters"]), "locations": len(result["locations"]),
            "props": len(result["props"]), "effects": len(result["effects"]),
            "scenes": len(result["scenes"]), "findings": len(report["findings"])}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare")
    prepare.add_argument("source")
    prepare.add_argument("--output", required=True)
    final = commands.add_parser("finalize")
    final.add_argument("work")
    final.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        work = initial_work(Path(args.source))
        write_json(Path(args.output), work)
        print(json.dumps({"scenes": len(work["scenes"]),
                          "characters": len(work["assets"]["characters"]),
                          "locations": len(work["assets"]["locations"]),
                          "work": args.output}, ensure_ascii=False))
    else:
        print(json.dumps(finalize(Path(args.work), Path(args.output_dir)), ensure_ascii=False))


if __name__ == "__main__":
    main()
