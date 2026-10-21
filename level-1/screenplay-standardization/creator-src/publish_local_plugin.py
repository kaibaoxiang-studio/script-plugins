#!/usr/bin/env python3
"""Prepare a Codex-selectable local marketplace from the Harness plugin."""

from __future__ import annotations

import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "screenplay-standardizer"
MARKETPLACE = ROOT / "dist" / "local-marketplace"
DESTINATION = MARKETPLACE / "plugins" / "screenplay-standardizer"
INTERFACE = {
    "displayName": "剧本标准化",
    "shortDescription": "剧本标准化与证据化问题审查",
    "longDescription": "将 DOCX、TXT 或 Markdown 剧本及分集细纲整理为可追溯的标准剧本，并可独立审查疑似问题。",
    "developerName": "开宝箱工作室",
    "category": "Productivity",
    "defaultPrompt": "Use $screenplay-standardizer to select $standardize-screenplay or $review-screenplay for my request. Preserve source evidence and report uncertain findings separately.",
}


def update_json(path: Path, updater) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    updater(data)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    if not (PLUGIN / "capabilities.json").is_file():
        raise SystemExit("先用 Harness Creator 构建 screenplay-standardizer")

    update_json(PLUGIN / ".codex-plugin" / "plugin.json",
                lambda data: data.update(interface=INTERFACE))
    update_json(PLUGIN / "plugin.json",
                lambda data: data.setdefault("extensions", {}).setdefault("com.openai", {}).update(interface=INTERFACE))

    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    if DESTINATION.exists():
        shutil.rmtree(DESTINATION)
    shutil.copytree(PLUGIN, DESTINATION, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))

    catalog = {
        "name": "screenplay-standardizer-local",
        "interface": {"displayName": "剧本标准化 Local"},
        "plugins": [{
            "name": "screenplay-standardizer",
            "source": {"source": "local", "path": "./plugins/screenplay-standardizer"},
            "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
            "category": "Productivity",
        }],
    }
    target = MARKETPLACE / ".agents" / "plugins" / "marketplace.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(MARKETPLACE)


if __name__ == "__main__":
    main()
