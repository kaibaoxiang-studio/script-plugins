"""Run a real Codex App Server file-writing check under a Chinese path."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'runtime'))

from harness_core.appserver import AppServer, envelope_schema
from harness_core.engine import verify_result
from harness_core.common import write_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    target = args.output_dir.resolve()
    artifact_dir = target / 'artifacts'
    skill = target / 'skills' / 'echo-proof' / 'SKILL.md'
    skill.parent.mkdir(parents=True, exist_ok=True)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    skill.write_text('''---
name: echo-proof
description: Verify a Codex Agent can write an exact file in a Chinese path.
---

# Echo Proof

Read `inputs.text` from the supplied task. Write the exact UTF-8 text to
`artifact_dir/marker.txt`. Return the required JSON envelope with status
`succeeded`, result `{"echo": inputs.text}`, artifacts `["marker.txt"]`,
questions `[]`, and error `null`. Do not paraphrase the text.
''', encoding='utf-8')
    schema = {'type': 'object', 'additionalProperties': False,
              'required': ['echo'], 'properties': {'echo': {'type': 'string'}}}
    capability = {'output_schema': schema, 'required_artifacts': ['marker.txt']}
    task = {'task_id': 'real-codex-chinese-path-smoke',
            'objective': 'Write and report the exact supplied text.',
            'inputs': {'text': '中文路径验证：剧本 A'},
            'answers': {}, 'artifact_dir': str(artifact_dir)}
    client = AppServer()
    try:
        output, thread_id = client.run(skill, task, envelope_schema(schema),
                                       artifact_dir, writable=True, timeout=180)
        artifacts = verify_result(output, capability, artifact_dir)
        if output['result']['echo'] != task['inputs']['text']:
            raise AssertionError('Codex returned a changed value')
        if (artifact_dir / 'marker.txt').read_text(encoding='utf-8') != task['inputs']['text']:
            raise AssertionError('Codex wrote changed file content')
        report = {'status': 'passed', 'thread_id': thread_id,
                  'output': output, 'artifacts': artifacts}
        write_json(target / 'smoke-report.json', report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
    except Exception as exc:
        write_json(target / 'smoke-report.json', {'status': 'failed',
                   'error_type': type(exc).__name__, 'error': str(exc),
                   'codex_stderr': client.stderr[-20:]})
        raise
    finally:
        client.close()


if __name__ == '__main__':
    main()
