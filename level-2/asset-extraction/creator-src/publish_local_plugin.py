#!/usr/bin/env python3
"""Create a local Codex marketplace for the built asset-extractor plugin."""
from __future__ import annotations

import json
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "screenplay-asset-extractor"
MARKETPLACE = ROOT / "dist" / "local-marketplace"
DESTINATION = MARKETPLACE / "plugins" / "screenplay-asset-extractor"


def main() -> None:
    if not (PLUGIN / "capabilities.json").is_file():
        raise SystemExit("先用 Harness Creator 构建 screenplay-asset-extractor")
    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(PLUGIN, DESTINATION, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    catalog = {
        "name": "screenplay-asset-extractor-local",
        "interface": {"displayName": "剧本资产表提取 Local"},
        "plugins": [{
            "name": "screenplay-asset-extractor",
            "source": {"source": "local", "path": "./plugins/screenplay-asset-extractor"},
            "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
            "category": "Productivity"}]}
    target = MARKETPLACE / ".agents/plugins/marketplace.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(MARKETPLACE)


if __name__ == "__main__":
    main()
