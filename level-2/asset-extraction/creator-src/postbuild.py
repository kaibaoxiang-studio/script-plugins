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
    "longDescription": "JSON 和 DOCX 入口均需逐场语义审核后导出，支持人物状态、道具身份与可追溯 Excel；内置 workflow v0.3.2。",
    "developerName": "开宝箱工作室",
    "category": "Productivity",
    "defaultPrompt": "Use $screenplay-asset-extractor to select this plugin’s JSON or DOCX workflow and extract fully reviewed, evidence-backed assets.",
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
    for dependency in (*DEPENDENCIES, *(Path(__file__).parent / "docx-requirements.lock").read_text().splitlines()):
        if dependency not in lines:
            lines.append(dependency)
    lock.write_text("\n".join(lines) + "\n", encoding="utf-8")
    update_json(PLUGIN / ".codex-plugin" / "plugin.json", lambda data: data.update(interface=INTERFACE))
    update_json(PLUGIN / "plugin.json",
                lambda data: data.setdefault("extensions", {}).setdefault("com.openai", {}).update(interface=INTERFACE))
    (PLUGIN / "THIRD_PARTY_NOTICES.md").write_text(NOTICES, encoding="utf-8")
    # Dispatch is always transient. Resume from on-disk artifacts, never saved chats.
    appserver = PLUGIN / "runtime/harness_core/appserver.py"
    text = appserver.read_text(encoding="utf-8")
    old = """        if thread_id:
            thread = self.request('thread/resume', {'threadId':thread_id})['thread']
        else:
            thread = self.request('thread/start', {
                'cwd':str(Path(workdir).resolve()), 'approvalPolicy':'never',
                'sandbox':'workspace-write' if writable else 'read-only', 'ephemeral':False})['thread']
        thread_id = thread['id']"""
    new = """        thread = self.request('thread/start', {
            'cwd':str(Path(workdir).resolve()), 'approvalPolicy':'never',
            'sandbox':'workspace-write' if writable else 'read-only', 'ephemeral':True})['thread']
        if thread.get('ephemeral') is not True:
            raise RuntimeError('App Server did not confirm an ephemeral dispatcher thread; refusing persistent fallback')
        thread_id = thread['id']"""
    if old in text:
        appserver.write_text(text.replace(old, new), encoding="utf-8")
    elif new not in text:
        raise ValueError("Unexpected AppServer dispatch code; review before patching")
    engine = PLUGIN / "runtime/harness_core/engine.py"
    content = engine.read_text(encoding="utf-8")
    guard = """    if result['status'] == 'succeeded' and capability['id'] == 'extract-asset-table':
        verifier = Path(__file__).resolve().parents[2] / 'scripts/verify_delivery.py'
        checked = subprocess.run([sys.executable, str(verifier), str(Path(artifact_dir).resolve()),
                                  '--expected-counts', json.dumps(result['result'])],
                                 capture_output=True, text=True)
        if checked.returncode:
            raise ValueError('Asset completion postcondition failed: ' + (checked.stderr or checked.stdout).strip())
"""
    marker = '    return artifacts\n\nclass Executor'
    if guard not in content:
        if marker not in content:
            raise ValueError('Unexpected Engine verification code; review before patching')
        content = content.replace(marker, guard + marker)
        engine.write_text(content, encoding="utf-8")
    # Explicit source identity prevents same-name installed Skills taking precedence.
    text = appserver.read_text(encoding="utf-8")
    anchor = "        sandbox = ({'type':'workspaceWrite'"
    route = r"""        prompt += ('\nExact Skill source for this task: ' + str(skill_path)
                   + '\nRead that exact SKILL.md and resolve its references/scripts from plugin root '
                   + str(skill_path.parents[2])
                   + '. Do not substitute a same-named installed or personal Skill. '
                   'This run must use this source version and its completion gates.')
"""
    if route not in text:
        if anchor not in text:
            raise ValueError('Unexpected AppServer prompt; review before patching')
        appserver.write_text(text.replace(anchor, route + anchor), encoding="utf-8")
    generation = PLUGIN / "generation-lock.json"
    data = json.loads(generation.read_text(encoding="utf-8"))
    for path in sorted(PLUGIN.rglob("*")):
        relative = path.relative_to(PLUGIN).as_posix()
        if path.is_file() and "__pycache__" not in path.parts and path.suffix not in {".pyc", ".pyo"} and relative != "generation-lock.json":
            data["files"][relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    generation.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(PLUGIN)


if __name__ == "__main__":
    main()
