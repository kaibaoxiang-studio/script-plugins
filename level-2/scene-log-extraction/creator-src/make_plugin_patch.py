"""Prepare Harness Creator's hash-checked post-build metadata/dependency patch."""

import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / "scene-log-extractor"


def change(relative, content):
    path = PLUGIN / relative
    return {"path": relative, "expected_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "content": content}


lock = (PLUGIN / "requirements.lock").read_text(encoding="utf-8")
for requirement in (
    "et-xmlfile==2.0.0 --hash=sha256:7a91720bc756843502c3b7504c77b8fe44217c85c537d85037f0f536151b2caa",
    "openpyxl==3.1.5 --hash=sha256:5282c12b107bffeef825f4617dc029afaf41d0ea60823bbb665ef3079dc79de2",
):
    if requirement.split("==")[0] not in lock:
        lock += requirement + "\n"

manifest = json.loads((PLUGIN / "plugin.json").read_text(encoding="utf-8"))
manifest["extensions"]["com.openai"]["interface"] = {
    "displayName": "场记表提取", "shortDescription": "标准剧本转可追溯场记表",
    "longDescription": "从一级标准化剧本 JSON 提取整剧场记表、待审制作建议与独立疑点报告。",
    "developerName": "开宝箱工作室", "category": "Productivity",
    "defaultPrompt": "Use $ai-continuity-sheet to extract a scene log from my standardized_screenplay_v1 JSON.",
}

patch = {"changes": [change("requirements.lock", lock),
                     change("plugin.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")]}
destination = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else ROOT / "creator-src" / "plugin-patch.json"
destination.write_text(json.dumps(patch, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(destination)
