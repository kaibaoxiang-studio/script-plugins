"""Build and execute a real Agent plugin with Chinese paths and inputs."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'runtime'))

from harness_core.common import write_json
from harness_core.engine import Engine
from harness_core.packages import build


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    target = args.output_dir.resolve()
    plugin = target / 'echo-plugin'
    workspace = target / '运行工作区'
    text = '中文路径验证：剧本 A'
    schema = {'type': 'object', 'additionalProperties': False,
              'properties': {'echo': {'type': 'string'}}, 'required': ['echo']}
    spec = {
        'schema_version': 'HarnessBlueprintV1',
        'plugin': {'name': 'echo-plugin', 'version': '0.1.0',
                   'description': 'Write and return an exact input string'},
        'goal': 'Verify a generated Agent plugin can write the exact supplied text.',
        'acceptance_criteria': ['Actual file and result match the supplied text'],
        'open_questions': [], 'files': {}, 'workflows': [], 'sources': [],
        'capabilities': [{
            'id': 'echo', 'skill_name': 'echo', 'description': 'Write exact text to a file',
            'instructions': ('Read inputs.text from the supplied task. Write its exact UTF-8 value '
                             'to artifact_dir/marker.txt. Return the required JSON envelope with '
                             'status succeeded, result {"echo": inputs.text}, artifacts '
                             '["marker.txt"], questions [], and error null. Do not paraphrase.'),
            'input_schema': {'type': 'object', 'additionalProperties': False,
                             'properties': {'text': {'type': 'string'}}, 'required': ['text']},
            'output_schema': schema, 'required_artifacts': ['marker.txt'],
            'execution': {'kind': 'agent', 'access': 'workspace-write', 'network': False}
        }]
    }
    built = build(spec, plugin, ROOT, confirmed=True)
    engine = Engine(plugin, workspace)
    workflow = {'id': 'echo-smoke', 'max_concurrency': 1, 'nodes': [{
        'id': 'echo', 'capability': 'echo', 'depends_on': [],
        'idempotent': False, 'retries': 0, 'timeout_seconds': 180,
        'bindings': {'text': {'from': 'inputs.text'}}
    }]}
    run_id = engine.create(workflow, {'text': text})
    state = engine.execute(run_id)
    if state['status'] != 'completed':
        raise AssertionError(f'Run did not complete: {state["status"]}')
    output = state['nodes']['echo']['output']
    if output['result']['echo'] != text:
        raise AssertionError('Agent result changed the text')
    artifact = Path(state['nodes']['echo']['artifacts'][0]['path'])
    if artifact.read_text(encoding='utf-8') != text:
        raise AssertionError('Agent artifact changed the text')
    report = {'status': 'passed', 'plugin': built['path'], 'run_id': run_id,
              'run_report': str(workspace / '.harness' / run_id / 'run-report.json'),
              'artifact': str(artifact)}
    write_json(target / 'end-to-end-report.json', report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
