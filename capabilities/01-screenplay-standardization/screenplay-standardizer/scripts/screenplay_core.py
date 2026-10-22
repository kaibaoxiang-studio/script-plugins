#!/usr/bin/env python3
"""Traceable screenplay intake, rendering, and evidence-first review.

This module is intentionally independent of the unlicensed SN2S source code.
The model-facing Skill handles creative decisions; this module handles file IO,
source anchors, conservative structure extraction, and deterministic checks.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from xml.etree import ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
EPISODE = re.compile(r"^第\s*([0-9一二三四五六七八九十百零]+)\s*集(?:\s*[｜|・·:：—-]\s*[《]?(.+?)[》]?)?\s*$")
NUMBERED_SCENE = re.compile(r"^(\d+)[-‑－—–](\d+)\s+(.+)$")
PLAIN_SCENE = re.compile(r"^(.{2,60}?)\s+(日|夜|晨|早|午|晚|黄昏|凌晨|清晨|傍晚)\s+(内|外|内/外|外/内)$")
DIALOGUE = re.compile(r"^([^：:]{1,45}?)(?:\s*[：:]\s*)(.*)$")
SECTION = re.compile(r"^(?:[一二三四五六七八九十0-9]+[、.．]\s*)?(最终剧本|双语剧本|中文剧本|正式剧本|剧本正文|分集细纲|剧情大纲|剧本|正文)\s*$")
SUMMARY = re.compile(r"^(?:>\s*)?本集概要\s*[：:]\s*(.*)$")
OUTLINE_FIELD = re.compile(r"^(?:【(剧情|开场钩子|冲突点|卡点|情绪爆点)】|(?:剧情|开场钩子|冲突点|卡点)\s*[：:])")
PLACEHOLDER = "（需依据本集内容补写）"


class SourceError(ValueError):
    pass


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _chinese_number(value: str) -> int:
    if value.isdigit():
        return int(value)
    digits = {"零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
              "六": 6, "七": 7, "八": 8, "九": 9}
    if value == "十":
        return 10
    if "百" in value:
        left, right = value.split("百", 1)
        return (digits.get(left, 1) or 1) * 100 + (_chinese_number(right) if right else 0)
    if "十" in value:
        left, right = value.split("十", 1)
        return (digits.get(left, 1) or 1) * 10 + (digits.get(right, 0) if right else 0)
    return digits.get(value, 0)


def _docx_lines(raw: bytes) -> list[dict]:
    try:
        with zipfile.ZipFile(__import__("io").BytesIO(raw)) as archive:
            root = ET.fromstring(archive.read("word/document.xml"))
    except (zipfile.BadZipFile, KeyError, ET.ParseError) as exc:
        raise SourceError("DOCX 文件无法读取或缺少 word/document.xml") from exc
    body = root.find(W + "body")
    if body is None:
        raise SourceError("DOCX 正文为空")
    result: list[dict] = []
    # iter() keeps paragraphs in their document order, including table cells.
    for para in body.iter(W + "p"):
        pieces: list[str] = []
        annotations: list[dict] = []
        offset = 0
        for run in para.iter(W + "r"):
            segment = "".join((node.text or "") if node.tag == W + "t" else
                              ("\t" if node.tag == W + "tab" else "\n")
                              for node in run.iter() if node.tag in {W + "t", W + "tab", W + "br"})
            if not segment:
                continue
            color = run.find("./" + W + "rPr/" + W + "color")
            if color is not None and color.get(W + "val") not in (None, "auto", "000000"):
                annotations.append({"start": offset, "end": offset + len(segment),
                                    "color": color.get(W + "val"), "text": segment})
            pieces.append(segment)
            offset += len(segment)
        result.append({"text": "".join(pieces).strip(), "ref": f"P{len(result)+1}",
                       "annotations": annotations})
    return result


def read_source(path: str | Path) -> dict:
    source = Path(path).expanduser().resolve()
    if not source.is_file():
        raise SourceError(f"输入文件不存在：{source}")
    raw = source.read_bytes()
    suffix = source.suffix.lower()
    if suffix == ".docx":
        lines = _docx_lines(raw)
        kind = "docx"
    elif suffix in {".txt", ".md", ".markdown"}:
        kind = "markdown" if suffix != ".txt" else "txt"
        decoded = None
        for codec in ("utf-8-sig", "utf-16", "gb18030"):
            try:
                decoded = raw.decode(codec)
                break
            except UnicodeDecodeError:
                pass
        if decoded is None:
            raise SourceError("TXT/Markdown 编码无法识别")
        lines = [{"text": line.strip(), "ref": f"L{index}", "annotations": []}
                 for index, line in enumerate(decoded.replace("\r\n", "\n").replace("\r", "\n").split("\n"), 1)]
    else:
        raise SourceError("首版仅支持 DOCX、TXT、MD、Markdown")
    if not any(row["text"] for row in lines):
        raise SourceError("输入文件没有可读取的正文")
    return {"manifest": {"filename": source.name, "format": kind, "source_sha256": _sha(raw),
                         "reference_scheme": "paragraph" if kind == "docx" else "line",
                         "source_unit_count": len(lines)}, "lines": lines}


def _is_scene(text: str) -> bool:
    return bool(NUMBERED_SCENE.match(text) or PLAIN_SCENE.match(text))


def _script_score(lines: list[dict]) -> tuple[int, int, int]:
    scenes = sum(_is_scene(row["text"]) for row in lines)
    casts = sum(row["text"].startswith(("人物：", "出场人物：")) for row in lines)
    dialogue = sum(bool(DIALOGUE.match(row["text"])) for row in lines)
    return scenes, casts, dialogue


def choose_primary(lines: list[dict], selected_section: int | None = None) -> dict:
    markers = [(index, row["text"], SECTION.match(row["text"]).group(1))
               for index, row in enumerate(lines) if SECTION.match(row["text"])]
    candidates: list[dict] = []
    if markers:
        for number, (start, heading, label) in enumerate(markers, 1):
            end = markers[number][0] if number < len(markers) else len(lines)
            segment = lines[start + 1:end]
            scenes, casts, dialogue = _script_score(segment)
            if scenes or (label == "分集细纲" and sum(bool(EPISODE.match(r["text"])) for r in segment)):
                display_label = "含剧本的复合段" if scenes and label in {"剧情大纲", "分集细纲"} else label
                candidates.append({"number": number, "label": display_label, "heading": heading, "start": start + 1,
                                   "end": end, "scenes": scenes, "casts": casts,
                                   "dialogue": dialogue})
    if not candidates:
        candidates = [{"number": 1, "label": "全文", "start": 0, "end": len(lines),
                       "scenes": _script_score(lines)[0], "casts": _script_score(lines)[1],
                       "dialogue": _script_score(lines)[2]}]
    if selected_section is not None:
        chosen = next((x for x in candidates if x["number"] == selected_section), None)
        if chosen is None:
            raise SourceError(f"指定的正文段 {selected_section} 不存在；可选：{[x['number'] for x in candidates]}")
    else:
        scripted = [x for x in candidates if x["scenes"] > 0]
        rank = {"最终剧本": 3, "正式剧本": 3, "剧本正文": 2, "剧本": 2,
                "正文": 2, "中文剧本": 1, "双语剧本": 1}
        labelled = [x for x in scripted if x["label"] in rank]
        if labelled:
            highest = max(rank[x["label"]] for x in labelled)
            preferred = [x for x in labelled if rank[x["label"]] == highest]
            if len(preferred) > 1:
                raise SourceError("多份剧本正文同权，无法安全选择；请指定 selected_section")
            chosen = preferred[0]
        elif len(scripted) == 1:
            chosen = scripted[0]
        elif len(scripted) > 1:
            raise SourceError("多份剧本正文同权，无法安全选择；请指定 selected_section")
        else:
            chosen = candidates[-1]
    other = [x for x in candidates if x is not chosen]
    notices = []
    if other:
        notices.append({"code": "multiple_versions", "message":
                        f"已选第 {chosen['number']} 段“{chosen['label']}”为主稿；其他版本仅作为参考，可用 selected_section 改选。"})
    return {"chosen": chosen, "candidates": candidates, "notices": notices}


def _scene_parts(text: str) -> tuple[int | None, int | None, str, str, str] | None:
    match = NUMBERED_SCENE.match(text)
    if match:
        ep, number, body = int(match.group(1)), int(match.group(2)), match.group(3)
    else:
        match = PLAIN_SCENE.match(text)
        if not match:
            return None
        ep, number, body = None, None, text
    body = body.replace("／", "/")
    tokens = body.split()
    times = {"日", "夜", "晨", "早", "午", "晚", "黄昏", "凌晨", "清晨", "傍晚", "连续"}
    inouts = {"内", "外", "内/外", "外/内"}
    time = next((x for x in tokens if x in times), "未标")
    inside = next((x for x in tokens if x in inouts), "未标")
    location = " ".join(x for x in tokens if x not in times | inouts).strip() or "未标地点"
    return ep, number, location, inside, time


def _block(kind: str, text: str, row: dict, **extra) -> dict:
    result = {"type": kind, "text": text, "source_refs": [row["ref"]],
              "origin": "source", "extracted_text": text,
              "annotations": [dict(item, source_ref=row["ref"])
                                                for item in row.get("annotations", [])]}
    result.update(extra)
    return result


def _dialogue(row: dict) -> dict | None:
    text = row["text"]
    match = DIALOGUE.match(text)
    if not match:
        return None
    label, content = match.group(1).strip(), match.group(2)
    if label.startswith(("人物", "出场人物", "本集概要", "剧情", "时长", "冲突点", "情绪", "画面", "镜头", "特写", "空镜")) or label in {"手机", "屏幕", "字幕", "灯光", "音效"}:
        return None
    if len(label) > 34 or label.startswith(("▲", "【")):
        return None
    voice = None
    voice_match = re.search(r"\[\s*(OS|VO)\s*\]|(?<=[\w）)])(os|vo)(?=\s*[（(]|$)", label, re.I)
    if voice_match:
        voice = (voice_match.group(1) or voice_match.group(2)).upper()
        label = (label[:voice_match.start()] + label[voice_match.end():]).strip()
    if label in {"旁白", "画外音", "系统提示音"}:
        voice = "VO"
    tone = None
    tone_match = re.search(r"[（(]([^）)]{1,25})[）)]$", label)
    if tone_match:
        tone = tone_match.group(1).strip()
        label = label[:tone_match.start()].strip()
    after_tone = re.match(r"^[（(]([^）)]{1,25})[）)]\s*(.*)$", content)
    if after_tone and not tone:
        tone, content = after_tone.group(1).strip(), after_tone.group(2)
    language = "en" if re.fullmatch(r"[A-Z][A-Z0-9 .'-]{1,35}", label) and re.search(r"[A-Za-z]{3}", content) else "zh"
    return _block("dialogue", content.strip(), row, speaker=label, tone=tone, voice=voice, language=language)


def _cast(text: str) -> list[str]:
    text = re.sub(r"^(?:出场)?人物\s*[：:]\s*", "", text)
    return [part.strip() for part in re.split(r"[、,，;；\s]+", text) if part.strip()]


def _title_from_content(ep: dict) -> str:
    for scene in ep["scenes"]:
        for block in scene["blocks"]:
            if block["type"] == "action":
                snippet = re.sub(r"[。！？.!?].*$", "", block["text"])
                snippet = re.sub(r"^[【][^】]+[】]", "", snippet).strip()
                if snippet:
                    return snippet[:14].rstrip("，、 ")
    return "本集剧情"


def _summary_from_content(ep: dict) -> str:
    acts = [block["text"] for scene in ep["scenes"] for block in scene["blocks"] if block["type"] == "action"]
    if not acts:
        return PLACEHOLDER
    opening = acts[0].rstrip("。！!？?")
    ending = acts[-1].rstrip("。！!？?")
    if opening == ending:
        return opening[:80] + "。"
    return opening[:48] + "；" + ending[:48] + "。"


def _split_script(lines: list[dict], notices: list[dict]) -> tuple[list[dict], list[dict]]:
    episodes: list[dict] = []
    front: list[dict] = []
    episode: dict | None = None
    scene: dict | None = None
    source_count = 0
    for index, row in enumerate(lines):
        text = row["text"].strip()
        if not text:
            continue
        ep_match = EPISODE.match(text)
        if ep_match:
            number = _chinese_number(ep_match.group(1)) or len(episodes) + 1
            episode = {"id": f"ep-{len(episodes)+1:03d}", "number": number,
                       "title": (ep_match.group(2) or "").strip("《》 "), "summary": "",
                       "source_refs": [row["ref"]], "scenes": []}
            episodes.append(episode)
            scene = None
            continue
        if text in {"：", ":"} and episode is not None:
            episode["source_refs"].append(row["ref"])
            episode = None
            scene = None
            continue
        parts = _scene_parts(text)
        if parts:
            stated_ep, stated_scene, location, inout, time = parts
            if episode is None:
                episode = {"id": f"ep-{len(episodes)+1:03d}", "number": len(episodes)+1,
                           "title": "", "summary": "", "source_refs": [row["ref"]], "scenes": []}
                episodes.append(episode)
            expected = len(episode["scenes"]) + 1
            if stated_ep is not None and stated_ep != episode["number"]:
                notices.append({"code": "scene_episode_number", "source_refs": [row["ref"]],
                                "message": f"原场号 {stated_ep}-{stated_scene} 与当前集号不一致"})
            if stated_scene is not None and stated_scene != expected:
                notices.append({"code": "scene_sequence", "source_refs": [row["ref"]],
                                "message": f"原场号 {stated_scene} 与本集顺序 {expected} 不一致"})
            scene = {"id": f"scn-{sum(len(e['scenes']) for e in episodes)+1:03d}",
                     "number": f"{episode['number']}-{expected}", "source_heading": text,
                     "location": location, "interior_exterior": inout, "time": time,
                     "characters": [], "source_refs": [row["ref"]], "blocks": []}
            episode["scenes"].append(scene)
            continue
        sum_match = SUMMARY.match(text)
        if sum_match and episode is not None and scene is None:
            episode["summary"] = sum_match.group(1).strip()
            episode["source_refs"].append(row["ref"])
            continue
        if scene is None:
            front.append({"text": text, "source_refs": [row["ref"]], "annotations": row.get("annotations", [])})
            continue
        if text.startswith(("人物：", "人物:", "出场人物：", "出场人物:")):
            scene["characters"] = _cast(text)
            scene["source_refs"].append(row["ref"])
            continue
        if not scene["characters"] and index > 0 and re.fullmatch(r"[\w\u3400-\u9fff·、，,\s若干]+", text) and len(text) < 80:
            names = _cast(text)
            if 1 <= len(names) <= 12:
                scene["characters"] = names
                scene["source_refs"].append(row["ref"])
                continue
        if text in {"闪回", "【闪回】", "闪出", "【闪出】"}:
            scene["blocks"].append(_block("marker", "【闪回】" if "闪回" in text else "【闪出】", row))
            source_count += 1
            continue
        block = _dialogue(row)
        if block is not None and not block["text"].strip():
            notices.append({"code": "empty_dialogue", "source_refs": [row["ref"]],
                            "message": f"{scene['number']} 的“{block['speaker']}”对白在原稿中为空；已略去空正文块，请核对并补写原稿对白"})
            continue
        if block is None:
            action = text.lstrip("▲").strip()
            block = _block("action", action, row)
        scene["blocks"].append(block)
        source_count += 1
    if not episodes or not any(e["scenes"] for e in episodes):
        raise SourceError("未识别到可标准化的场景；纯细纲请使用 Agent 创作入口")
    for ep in episodes:
        if not ep["title"]:
            ep["title"] = _title_from_content(ep)
            ep["title_origin"] = "heuristic_generated"
        else:
            ep["title_origin"] = "source"
        if not ep["summary"]:
            ep["summary"] = _summary_from_content(ep)
            ep["summary_origin"] = "heuristic_generated"
        else:
            ep["summary_origin"] = "source"
        depth = 0
        for sc in ep["scenes"]:
            for block in sc["blocks"]:
                if block["type"] == "marker" and block["text"] == "【闪回】":
                    depth += 1
                elif block["type"] == "marker" and block["text"] == "【闪出】":
                    depth -= 1
            if not sc["characters"]:
                sc["characters"] = list(dict.fromkeys(b["speaker"] for b in sc["blocks"]
                                                            if b["type"] == "dialogue" and b["speaker"] not in {"旁白", "画外音"}))
                notices.append({"code": "cast_inferred", "source_refs": sc["source_refs"],
                                "message": f"{sc['number']} 缺少人物表，已从对白标签推断；请核对"})
            else:
                extras = []
                for block in sc["blocks"]:
                    if block["type"] != "dialogue":
                        continue
                    name = block["speaker"]
                    covered = (name in sc["characters"] or name in {"旁白", "画外音", "系统提示音", "系统"}
                               or any(label.endswith("若干") and name.startswith(label[:-2]) for label in sc["characters"]))
                    if name and not covered and name not in extras:
                        extras.append(name)
                if extras:
                    sc["characters"].extend(extras)
                    notices.append({"code": "cast_extended", "source_refs": sc["source_refs"],
                                    "message": f"{sc['number']} 人物表已补入原稿中实际发话的标签：{'、'.join(extras)}；请核对姓名"})
        if depth > 0 and ep["scenes"] and ep["scenes"][-1]["blocks"]:
            last_scene = ep["scenes"][-1]
            anchor = last_scene["blocks"][-1]["source_refs"]
            for _ in range(depth):
                last_scene["blocks"].append({"type": "marker", "text": "【闪出】",
                                             "source_refs": anchor, "origin": "generated", "annotations": []})
            notices.append({"code": "flashback_auto_closed", "source_refs": anchor,
                            "message": f"第 {ep['number']} 集原稿闪回未闭合，暂在集末补闪出；请核对正确位置"})
    return episodes, front


def prepare(source_path: str, input_kind: str = "auto", selected_section: int | None = None) -> dict:
    source = read_source(source_path)
    selection = choose_primary(source["lines"], selected_section)
    chosen = selection["chosen"]
    primary = source["lines"][chosen["start"]:chosen["end"]]
    episode_headers = sum(bool(EPISODE.match(x["text"])) for x in primary)
    scenes = sum(_is_scene(x["text"]) for x in primary)
    kind = input_kind if input_kind != "auto" else ("script" if scenes else "outline" if episode_headers else "unknown")
    if kind not in {"script", "outline"}:
        raise SourceError("无法判断输入是剧本还是分集细纲")
    notices = list(selection["notices"])
    episodes: list[dict] = []
    front: list[dict] = []
    if kind == "script":
        episodes, front = _split_script(primary, notices)
    else:
        notices.append({"code": "outline_creation", "message": "纯细纲须由创作 Agent 补成场景和对白；生成内容应逐项标明来源。"})
        front = []
    used_refs = {ref for item in front for ref in item["source_refs"]}
    for ep in episodes:
        used_refs.update(ep["source_refs"])
        for scene in ep["scenes"]:
            used_refs.update(scene["source_refs"])
            for block in scene["blocks"]:
                used_refs.update(block["source_refs"])
    omitted_refs = {ref for notice in notices if notice.get("code") == "empty_dialogue"
                    for ref in notice.get("source_refs", [])}
    used_refs.update(omitted_refs)
    if kind == "outline":
        used_refs.update(row["ref"] for row in primary if row["text"])
    unassigned = [row["ref"] for row in primary if row["text"] and row["ref"] not in used_refs]
    if unassigned:
        notices.append({"code": "unassigned_source", "source_refs": unassigned[:20],
                        "message": f"主稿有 {len(unassigned)} 个非空来源段落未映射到剧本结构；详见 coverage.unassigned_source_refs"})
    supporting_rows = [row for index, row in enumerate(source["lines"])
                       if row["text"] and not chosen["start"] <= index < chosen["end"]]
    return {"schema_version": "standardized_screenplay_v1", "source_manifest": source["manifest"],
            "source_annotations": {row["ref"]: row["annotations"] for row in source["lines"] if row["annotations"]},
            "input_kind": kind, "selected_section": chosen, "section_candidates": selection["candidates"],
            "front_matter": front, "episodes": episodes, "notices": notices,
            "outline_source": [{"text": row["text"], "source_refs": [row["ref"]]}
                               for row in primary if row["text"]] if kind == "outline" else [],
            "reference_material": [x for x in selection["candidates"] if x["number"] != chosen["number"]],
            "support_material": [{"text": row["text"], "source_refs": [row["ref"]],
                                  "annotations": row.get("annotations", [])} for row in supporting_rows],
            "needs_creative_pass": kind == "outline", "coverage": {"status": "pending" if kind == "outline" else "parsed",
            "primary_source_refs": [row["ref"] for row in primary if row["text"]],
            "support_source_refs": [row["ref"] for row in supporting_rows],
            "omitted_source_refs": [row["ref"] for row in primary if row["ref"] in omitted_refs],
            "unassigned_source_refs": unassigned}}


def _render_text(text: str, annotations: list[dict]) -> str:
    rendered = html.escape(text, quote=False)
    unmatched = False
    for mark in annotations:
        fragment = html.escape(mark.get("text", ""), quote=False)
        if not fragment or fragment not in rendered:
            unmatched = True
            continue
        color = re.sub(r"[^0-9A-Fa-f]", "", mark.get("color", ""))[:6]
        if len(color) == 6:
            rendered = rendered.replace(fragment,
                f'<span data-source-color="#{color}" style="color:#{color}">{fragment}</span>', 1)
        else:
            unmatched = True
    if unmatched:
        rendered += ' <sup>〔原稿标色范围见 JSON〕</sup>'
    return rendered


def render_markdown(document: dict) -> str:
    lines: list[str] = []
    for ep in document["episodes"]:
        lines.extend([f"# 第 {ep['number']} 集｜{ep['title']}", "",
                      f"> 本集概要：{ep['summary']}", ""])
        for sc in ep["scenes"]:
            lines.extend([f"## {sc['number']} {sc['location']} {sc['interior_exterior']} {sc['time']}",
                          "", "人物：" + "、".join(sc["characters"]), ""])
            for block in sc["blocks"]:
                text = _render_text(block["text"], block.get("annotations", []))
                if block["type"] == "action":
                    lines.append("▲ " + text)
                elif block["type"] == "marker":
                    lines.append(text)
                elif block["type"] == "dialogue":
                    label = block["speaker"]
                    if block.get("tone"):
                        label += "（" + block["tone"] + "）"
                    if block.get("voice"):
                        label += " [" + block["voice"] + "]"
                    if block.get("language") not in {None, "zh"}:
                        label += " [lang:" + block["language"] + "]"
                    lines.append(label + "：" + text)
                lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _finding(code: str, message: str, refs: list[str], *, certainty: str = "explicit",
             confidence: str = "high", suggestion: str = "核对原稿与剧情设定") -> dict:
    return {"code": code, "message": message, "source_refs": refs, "certainty": certainty,
            "confidence": confidence, "suggestion": suggestion}


def audit(document: dict, mode: str = "light") -> dict:
    if mode not in {"light", "deep"}:
        raise SourceError("review_mode 只能是 light 或 deep")
    notices = [dict(n) for n in document.get("notices", []) if not n.get("source_refs")]
    findings = [_finding(n["code"], n["message"], n["source_refs"],
                         confidence="high" if n["code"] == "empty_dialogue" else "medium",
                         suggestion="补入原稿对白或确认确无对白" if n["code"] == "empty_dialogue" else "核对后保留或修订")
                for n in document.get("notices", []) if n.get("source_refs")]
    speakers: dict[str, list[tuple[int, str]]] = defaultdict(list)
    names: dict[str, set[str]] = defaultdict(set)
    co_present: set[tuple[str, str]] = set()
    for ep in document.get("episodes", []):
        for sc in ep.get("scenes", []):
            if sc.get("interior_exterior") == "未标" or sc.get("time") == "未标":
                findings.append(_finding("scene_heading_incomplete", f"场景 {sc['number']} 的内外景或时段不完整",
                                         sc.get("source_refs", [])))
            cast = set(sc.get("characters", []))
            for one in cast:
                for two in cast:
                    if one != two:
                        co_present.add((one, two))
            previous_action = None
            for block in sc.get("blocks", []):
                if block["type"] == "dialogue":
                    speaker = block.get("speaker", "")
                    if previous_action:
                        cue = next((name for name in cast if name != speaker and
                                    re.search(r"(?:^|[，。；\s])" + re.escape(name) +
                                              r"(?:说|问|喊|答|低语)(?:道|着)?[：:]?$", previous_action["text"])), None)
                        if cue:
                            findings.append(_finding("action_dialogue_mismatch",
                                f"{sc['number']} 动作提示为“{cue}”发话，随后对白标签却是“{speaker}”",
                                previous_action["source_refs"] + block["source_refs"],
                                certainty="inferred", confidence="medium",
                                suggestion="核对动作提示与对白说话人"))
                    if not block["text"].strip():
                        findings.append(_finding("empty_dialogue", f"{sc['number']} 的“{speaker}”对白为空",
                                                 block["source_refs"], suggestion="补入原稿对白或确认确无对白"))
                    group_match = any(name.endswith("若干") and speaker.startswith(name[:-2]) for name in cast)
                    generic_group = speaker in {"众人", "三女", "人群", "医生", "护士"} and any(
                        name.endswith("若干") or name in {"医生", "护士", "观众"} for name in cast)
                    if cast and speaker not in cast and not group_match and not generic_group and speaker not in {"旁白", "画外音", "系统提示音", "系统"}:
                        findings.append(_finding("speaker_not_in_cast", f"{sc['number']} 说话人“{speaker}”不在人物表",
                                                 block["source_refs"], suggestion="核对人物表或说话人标签"))
                    speakers[speaker].append((ep["number"], block["source_refs"][0]))
                    if speaker:
                        names[re.sub(r"[·•\s]", "", speaker)].add(speaker)
                    previous_action = None
                elif block["type"] == "action":
                    if previous_action and re.search(r"(?:说|问|喊|答|低语|解释)[：:]?\s*[。.!！?？]*$", previous_action["text"]):
                        findings.append(_finding("possible_missing_dialogue", f"{sc['number']} 的动作提示后疑似缺台词",
                                                 previous_action["source_refs"], certainty="inferred", confidence="low"))
                    previous_action = block
                else:
                    if previous_action and re.search(r"(?:说|问|喊|答|低语|解释)[：:]?\s*[。.!！?？]*$", previous_action["text"]):
                        findings.append(_finding("possible_missing_dialogue", f"{sc['number']} 的动作提示后疑似缺台词",
                                                 previous_action["source_refs"], certainty="inferred", confidence="low"))
                    previous_action = None
            if previous_action and re.search(r"(?:说|问|喊|答|低语|解释)[：:]?\s*[。.!！?？]*$", previous_action["text"]):
                findings.append(_finding("possible_missing_dialogue", f"{sc['number']} 的动作提示后疑似缺台词",
                                         previous_action["source_refs"], certainty="inferred", confidence="low"))
    # A short one-character divergence with repeated nearby labels is a candidate only.
    common = {k: v for k, v in speakers.items() if len(v) >= 2 and len(k) >= 2}
    allowed_changes = {(item.get("from"), item.get("to")) for item in document.get("name_changes", [])}
    allowed_changes |= {(right, left) for left, right in allowed_changes}
    for candidate, occurrences in speakers.items():
        if len(candidate) < 2 or candidate in common or candidate in {"旁白", "画外音"}:
            continue
        for canonical, anchor in common.items():
            if (candidate, canonical) in allowed_changes or (candidate, canonical) in co_present:
                continue
            if len(candidate) == len(canonical) and sum(a != b for a, b in zip(candidate, canonical)) == 1:
                findings.append(_finding("possible_name_variant", f"“{candidate}”与反复出现的“{canonical}”仅一字之差，需检查是否改名或另有人物",
                                         [occurrences[0][1], anchor[0][1]], certainty="inferred", confidence="low"))
                break
    if mode == "deep":
        for extra in document.get("extra_findings", []):
            if all(key in extra for key in ("code", "message", "source_refs", "certainty", "confidence", "suggestion")) and extra["source_refs"]:
                findings.append({key: extra[key] for key in
                                 ("code", "message", "source_refs", "certainty", "confidence", "suggestion")})
    if mode == "deep" and not document.get("deep_review_complete"):
        notices.append({"code": "deep_review_pending", "message":
                        "确定性检查已完成；跨集因果、合法改名及细纲对白覆盖仍须模型依据原文深审"})
    for index, finding in enumerate(findings, 1):
        finding["id"] = f"fnd-{index:03d}"
    return {"schema_version": "screenplay_findings_v1", "review_mode": mode,
            "source_sha256": document["source_manifest"]["source_sha256"], "findings": findings,
            "notices": notices,
            "counts": dict(Counter(item["code"] for item in findings))}


def render_findings(report: dict) -> str:
    lines = ["# 剧本疑点报告", "", f"审查模式：{report['review_mode']}", "",
             f"疑点数：{len(report['findings'])}", ""]
    if report.get("notices"):
        lines.extend(["## 处理提示", ""])
        for notice in report["notices"]:
            lines.append(f"- {notice['code']}：{notice['message']}")
        lines.append("")
    if not report["findings"]:
        lines.append("未发现有明确文本依据的轻审查疑点。")
    for item in report["findings"]:
        lines.extend([f"## {item['id']} {item['code']}", "", item["message"], "",
                      f"来源：{', '.join(item['source_refs']) or '待补证据'}", "",
                      f"置信度：{item['confidence']}；建议：{item['suggestion']}", ""])
    return "\n".join(lines).rstrip() + "\n"


def validate_document(document: dict) -> list[str]:
    errors = []
    if document.get("needs_creative_pass"):
        errors.append("纯细纲尚未完成创作 Agent 处理")
    if document.get("input_kind") == "outline" and document.get("coverage", {}).get("status") != "created":
        errors.append("纯细纲未标记创作完成")
    if not document.get("episodes"):
        errors.append("没有分集")
    for index, ep in enumerate(document.get("episodes", []), 1):
        flashback_depth = 0
        if ep.get("number") != index:
            errors.append(f"集号应连续：期望 {index}")
        if not ep.get("title") or not ep.get("summary"):
            errors.append(f"第 {index} 集缺少标题或概要")
        if not ep.get("scenes"):
            errors.append(f"第 {index} 集没有场景")
        for number, sc in enumerate(ep.get("scenes", []), 1):
            if sc.get("number") != f"{index}-{number}":
                errors.append(f"场号应为 {index}-{number}")
            if not sc.get("blocks"):
                errors.append(f"{index}-{number} 缺少动作或对白")
            for block_number, block in enumerate(sc.get("blocks", []), 1):
                if not isinstance(block.get("text"), str) or not block["text"].strip():
                    errors.append(f"{index}-{number} 第 {block_number} 个正文块为空")
                if not block.get("source_refs"):
                    errors.append(f"{index}-{number} 内容块缺少来源")
                for ref in block.get("source_refs", []):
                    match = re.fullmatch(r"[PL](\d+)", ref)
                    if not match or int(match.group(1)) > document.get("source_manifest", {}).get("source_unit_count", 0):
                        errors.append(f"{index}-{number} 内容块来源位置无效：{ref}")
                if block.get("origin") not in {"source", "generated"}:
                    errors.append(f"{index}-{number} 内容块来源类型无效")
                if document.get("input_kind") == "outline" and block.get("origin") != "generated":
                    errors.append(f"{index}-{number} 细纲创作块未标记 generated")
                if block.get("origin") == "source" and block.get("extracted_text") != block.get("text"):
                    errors.append(f"{index}-{number} 来源块正文已修改但未标记 generated")
                if block["type"] == "marker":
                    if block["text"] == "【闪回】":
                        flashback_depth += 1
                    elif block["text"] == "【闪出】":
                        flashback_depth -= 1
                    if flashback_depth < 0:
                        errors.append(f"{index}-{number} 出现未配对闪出")
                        flashback_depth = 0
        if flashback_depth:
            errors.append(f"第 {index} 集闪回未配对")
    return errors


def _omit_empty_dialogue_blocks(document: dict) -> None:
    """Repair editable intermediate JSON without inventing missing dialogue."""
    notices = document.setdefault("notices", [])
    coverage = document.setdefault("coverage", {})
    omitted = list(coverage.get("omitted_source_refs", []))
    recorded = {(item.get("code"), tuple(item.get("source_refs", []))) for item in notices}
    for ep in document.get("episodes", []):
        for scene in ep.get("scenes", []):
            kept = []
            for block in scene.get("blocks", []):
                refs = block.get("source_refs", [])
                empty_dialogue = (block.get("type") == "dialogue" and
                                  isinstance(block.get("text"), str) and not block["text"].strip())
                if not empty_dialogue or not refs:
                    kept.append(block)
                    continue
                key = ("empty_dialogue", tuple(refs))
                if key not in recorded:
                    notices.append({"code": "empty_dialogue", "source_refs": refs,
                                    "message": f"{scene['number']} 的“{block.get('speaker', '未标说话人')}”对白正文为空；已略去空正文块，请核对来源并补写对白"})
                    recorded.add(key)
                omitted.extend(refs)
            scene["blocks"] = kept
    coverage["omitted_source_refs"] = list(dict.fromkeys(omitted))
    if "unassigned_source_refs" in coverage:
        coverage["unassigned_source_refs"] = [ref for ref in coverage["unassigned_source_refs"]
                                              if ref not in coverage["omitted_source_refs"]]


def write_outputs(document: dict, output_dir: str | Path, review_mode: str = "light",
                  report_only: bool = False) -> dict:
    out = Path(output_dir).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    _omit_empty_dialogue_blocks(document)
    errors = validate_document(document) if not report_only else []
    if errors:
        raise SourceError("；".join(errors))
    paths: dict[str, str] = {}
    if not report_only:
        json_path = out / "标准化剧本.json"
        md_path = out / "标准化剧本.md"
        json_path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        md_path.write_text(render_markdown(document), encoding="utf-8")
        paths.update({"screenplay_json": str(json_path), "screenplay_markdown": str(md_path)})
    report = audit(document, review_mode)
    fj = out / "剧本疑点报告.json"
    fm = out / "剧本疑点报告.md"
    fj.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    fm.write_text(render_findings(report), encoding="utf-8")
    paths.update({"findings_json": str(fj), "findings_markdown": str(fm)})
    return {"paths": paths, "episodes": len(document.get("episodes", [])),
            "scenes": sum(len(ep["scenes"]) for ep in document.get("episodes", [])),
            "findings": len(report["findings"])}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare", help="只读抽取、选择主版本并构建待审剧本 JSON")
    p.add_argument("source")
    p.add_argument("--output", required=True)
    p.add_argument("--input-kind", choices=("auto", "script", "outline"), default="auto")
    p.add_argument("--selected-section", type=int)
    q = sub.add_parser("finalize", help="校验结构并输出标准剧本和疑点报告")
    q.add_argument("work_json")
    q.add_argument("--output-dir", required=True)
    q.add_argument("--review-mode", choices=("light", "deep"), default="light")
    t = sub.add_parser("review", help="独立审查 JSON 或原始剧本")
    t.add_argument("source")
    t.add_argument("--output-dir", required=True)
    t.add_argument("--review-mode", choices=("light", "deep"), default="light")
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            data = prepare(args.source, args.input_kind, args.selected_section)
            target = Path(args.output)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(json.dumps({"input_kind": data["input_kind"], "episodes": len(data["episodes"]),
                              "selected_section": data["selected_section"], "notices": data["notices"]}, ensure_ascii=False))
        elif args.command == "finalize":
            data = json.loads(Path(args.work_json).read_text(encoding="utf-8"))
            print(json.dumps(write_outputs(data, args.output_dir, args.review_mode), ensure_ascii=False))
        else:
            path = Path(args.source)
            if path.suffix.lower() == ".json":
                data = json.loads(path.read_text(encoding="utf-8"))
            else:
                data = prepare(path)
            print(json.dumps(write_outputs(data, args.output_dir, args.review_mode, report_only=True), ensure_ascii=False))
        return 0
    except (OSError, SourceError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
