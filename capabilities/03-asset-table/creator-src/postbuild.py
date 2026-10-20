#!/usr/bin/env python3
"""Apply pinned Excel dependency and Codex marketplace display metadata."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "screenplay-asset-extractor"
DEPENDENCIES = (
    "openpyxl==3.1.5 --hash=sha256:5282c12b107bffeef825f4617dc029afaf41d0ea60823bbb665ef3079dc79de2",
    "et_xmlfile==2.0.0 --hash=sha256:7a91720bc756843502c3b7504c77b8fe44217c85c537d85037f0f536151b2caa",
)
INTERFACE = {
    "displayName": "剧本资产表提取",
    "shortDescription": "从标准剧本提取可追溯的资产表",
    "longDescription": "从一级标准剧本 JSON 提取人物、场景、道具、关键特效和制作需求，交付资产表与独立疑点报告。",
    "developerName": "开宝箱工作室",
    "category": "Productivity",
    "defaultPrompt": "Use $extract-asset-table to extract evidence-backed assets from my standardized_screenplay.json.",
}
NOTICES = """# 第三方来源

- 插件携带的 Harness Creator 0.1.0 运行时借鉴并改写 Bird's Nest / Skill Orchestrator 的事件存储、DAG 调度与 App Server 客户端；上游提交 `3f5a5f348c2f71b3c5c046128e0c679089ab801a`，MIT 许可见 `licenses/Bird-s-Nest-MIT.txt`。本资产插件未收录 Grill Me Skill。
- Skill 编写方法参考本机 OpenAI Skill Creator 的指导原则；其 Apache-2.0 许可见 `licenses/skill-creator-Apache-2.0.txt`。本资产插件运行时不调用该 Skill。
- Python 第三方依赖版本与发行文件哈希见 `requirements.lock`，安装时应保留各库自身许可证。
- 仓库旧 `script-asset-extractor` 提供业务流程与四表结构的迁移依据；新插件独立实现 JSON 输入、证据校验和导出，来源修订记录见 `sources.lock.json`。
"""


def update_json(path: Path, updater) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    updater(data)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    lock = PLUGIN / "requirements.lock"
    lines = lock.read_text(encoding="utf-8").splitlines()
    for dependency in DEPENDENCIES:
        if dependency not in lines:
            lines.append(dependency)
    lock.write_text("\n".join(lines) + "\n", encoding="utf-8")
    update_json(PLUGIN / ".codex-plugin" / "plugin.json", lambda data: data.update(interface=INTERFACE))
    update_json(PLUGIN / "plugin.json",
                lambda data: data.setdefault("extensions", {}).setdefault("com.openai", {}).update(interface=INTERFACE))
    (PLUGIN / "THIRD_PARTY_NOTICES.md").write_text(NOTICES, encoding="utf-8")
    generation = PLUGIN / "generation-lock.json"
    data = json.loads(generation.read_text(encoding="utf-8"))
    for relative in ("requirements.lock", ".codex-plugin/plugin.json", "plugin.json",
                     "THIRD_PARTY_NOTICES.md"):
        data["files"][relative] = hashlib.sha256((PLUGIN / relative).read_bytes()).hexdigest()
    generation.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(PLUGIN)


if __name__ == "__main__":
    main()
