"""Create a local Codex marketplace from the validated plugin directory."""

import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "scene-log-extractor"
MARKET = ROOT / "dist" / "local-marketplace"
TARGET = MARKET / "plugins" / "scene-log-extractor"

if not (PLUGIN / ".codex-plugin" / "plugin.json").is_file():
    raise SystemExit("先构建并验证 scene-log-extractor 插件")
if TARGET.exists():
    shutil.rmtree(TARGET)
TARGET.parent.mkdir(parents=True, exist_ok=True)
shutil.copytree(PLUGIN, TARGET, ignore=shutil.ignore_patterns("__pycache__", ".harness"))
manifest = {
    "name": "scene-log-extractor-local",
    "interface": {"displayName": "场记表提取 Local"},
    "plugins": [{"name": "scene-log-extractor",
                 "source": {"source": "local", "path": "./plugins/scene-log-extractor"},
                 "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
                 "category": "Productivity"}],
}
location = MARKET / ".agents" / "plugins" / "marketplace.json"
location.parent.mkdir(parents=True, exist_ok=True)
location.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(MARKET)
