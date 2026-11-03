from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'runtime'))

from harness_core.common import fingerprint, read_json, sha, write_json
from harness_core.delivery import capture_check, check_delivery, validate_plan
from harness_core.packages import build


def blueprint():
    return {
        'schema_version': 'HarnessBlueprintV1',
        'plugin': {'name': 'small-plugin', 'version': '0.1.0', 'description': 'A small plugin'},
        'goal': 'Return a grounded answer', 'acceptance_criteria': ['Real check passes'],
        'open_questions': [], 'files': {}, 'workflows': [], 'sources': [],
        'capabilities': [{
            'id': 'answer', 'skill_name': 'answer', 'description': 'Answer one request',
            'instructions': 'Read the supplied input, produce a grounded answer, and report the actual result with evidence.',
            'input_schema': {'type': 'object'}, 'output_schema': {'type': 'object'},
            'execution': {'kind': 'agent', 'access': 'read-only', 'network': False}
        }]
    }


def plan(blueprint_sha):
    return {'schema_version': 'DeliveryPlanV1', 'blueprint_sha256': blueprint_sha,
            'features': [{
                'id': 'answer-feature', 'title': 'Return an answer',
                'goal': 'The caller receives a checked answer', 'non_goals': [],
                'capability_ids': ['answer'], 'depends_on': [],
                'scenarios': [{'id': 'returns-answer', 'given': 'A request exists',
                               'when': 'The capability runs', 'then': 'A checked answer exists'}]
            }]}


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name)
        self.blueprint_path = self.workspace / 'blueprint.json'
        write_json(self.blueprint_path, blueprint())
        self.plan_path = self.workspace / 'delivery-plan.json'
        write_json(self.plan_path, plan(sha(self.blueprint_path)))
        self.evidence_dir = self.workspace / 'evidence'
        self.evidence_dir.mkdir()
        self.plugin = self.workspace / 'generated-plugin'
        build(blueprint(), self.plugin, ROOT, confirmed=True)

    def check(self):
        return capture_check(self.workspace, 'answer-feature', 'returns-answer',
                             [sys.executable, '-c', 'print("checked")'])

    def evidence(self, implementer_check, validator_check):
        report = self.workspace / 'validator-report.md'
        report.write_text('Accepted after independently rerunning the scenario.\n')
        return {'schema_version': 'FeatureEvidenceV1', 'feature_id': 'answer-feature',
                'plan_sha256': sha(self.plan_path),
                'implementation': {'session_id': 'build-session', 'summary': 'Implemented answer',
                                   'checks': [implementer_check], 'artifacts': []},
                'validation': {'session_id': 'review-session', 'verdict': 'accept',
                               'checks': [validator_check],
                               'plugin_fingerprint': fingerprint(self.plugin),
                               'report': {'path': 'validator-report.md', 'sha256': sha(report)}}}

    def test_plan_rejects_missing_capability_and_cycles(self):
        source = read_json(self.plan_path)
        self.assertEqual(len(validate_plan(source, blueprint())), 1)
        process = subprocess.run([sys.executable, str(ROOT / 'harness.py'), 'delivery-plan-check',
                                  '--blueprint', str(self.blueprint_path), '--plan', str(self.plan_path)],
                                 capture_output=True, text=True)
        self.assertEqual(process.returncode, 0, process.stderr)
        stamp = subprocess.run([sys.executable, str(ROOT / 'harness.py'), 'plugin-fingerprint',
                                '--plugin', str(self.plugin)], capture_output=True, text=True)
        self.assertEqual(stamp.returncode, 0, stamp.stderr)
        self.assertEqual(json.loads(stamp.stdout)['fingerprint'], fingerprint(self.plugin))
        bad = deepcopy(source)
        bad['features'][0]['capability_ids'] = ['missing']
        with self.assertRaisesRegex(ValueError, 'Unknown capability'):
            validate_plan(bad, blueprint())
        bad = deepcopy(source)
        bad['features'][0]['depends_on'] = ['answer-feature']
        with self.assertRaisesRegex(ValueError, 'cycle'):
            validate_plan(bad, blueprint())

    def test_check_captures_real_exit_code_and_tamper(self):
        failed = capture_check(self.workspace, 'answer-feature', 'returns-answer',
                               [sys.executable, '-c', 'raise SystemExit(4)'])
        self.assertEqual(failed['status'], 'failed')
        self.assertEqual(failed['exit_code'], 4)
        passed = self.check()
        review = self.check()
        write_json(self.evidence_dir / 'answer-feature.json', self.evidence(passed, review))
        self.assertTrue(check_delivery(self.workspace, self.blueprint_path,
                                       self.plan_path, self.evidence_dir, self.plugin)['valid'])
        process = subprocess.run([sys.executable, str(ROOT / 'harness.py'), 'delivery-check',
                                  '--plugin', str(self.plugin),
                                  '--workspace', str(self.workspace), '--blueprint', str(self.blueprint_path),
                                  '--plan', str(self.plan_path), '--evidence-dir', str(self.evidence_dir)],
                                 capture_output=True, text=True)
        self.assertEqual(process.returncode, 0, process.stderr)
        archive = self.workspace / 'released.zip'
        release = subprocess.run([sys.executable, str(ROOT / 'harness.py'), 'release-package',
                                  '--plugin', str(self.plugin), '--output', str(archive),
                                  '--workspace', str(self.workspace), '--blueprint', str(self.blueprint_path),
                                  '--plan', str(self.plan_path), '--evidence-dir', str(self.evidence_dir)],
                                 capture_output=True, text=True)
        self.assertEqual(release.returncode, 0, release.stderr)
        self.assertTrue(archive.is_file())
        (self.workspace / passed['log_path']).write_text('tampered')
        report = check_delivery(self.workspace, self.blueprint_path,
                                self.plan_path, self.evidence_dir, self.plugin)
        self.assertFalse(report['valid'])
        self.assertIn('changed', report['errors'][0])

    def test_release_rejects_self_review_and_reused_log(self):
        passed = self.check()
        review = self.check()
        record = self.evidence(passed, review)
        record['validation']['session_id'] = 'build-session'
        write_json(self.evidence_dir / 'answer-feature.json', record)
        self.assertFalse(check_delivery(self.workspace, self.blueprint_path,
                                        self.plan_path, self.evidence_dir, self.plugin)['valid'])
        record['validation']['session_id'] = 'review-session'
        record['validation']['checks'] = [passed]
        write_json(self.evidence_dir / 'answer-feature.json', record)
        self.assertIn('reused', check_delivery(self.workspace, self.blueprint_path,
                                              self.plan_path, self.evidence_dir, self.plugin)['errors'][0])

    def test_release_rejects_stale_plan_and_revise_verdict(self):
        passed = self.check()
        review = self.check()
        record = self.evidence(passed, review)
        record['validation']['verdict'] = 'revise'
        write_json(self.evidence_dir / 'answer-feature.json', record)
        self.assertFalse(check_delivery(self.workspace, self.blueprint_path,
                                        self.plan_path, self.evidence_dir, self.plugin)['valid'])
        record['validation']['verdict'] = 'accept'
        write_json(self.evidence_dir / 'answer-feature.json', record)
        altered = read_json(self.blueprint_path)
        altered['goal'] = 'Changed goal'
        write_json(self.blueprint_path, altered)
        with self.assertRaisesRegex(ValueError, 'Blueprint changed'):
            check_delivery(self.workspace, self.blueprint_path, self.plan_path, self.evidence_dir, self.plugin)

    def test_release_rejects_plugin_changed_after_review(self):
        record = self.evidence(self.check(), self.check())
        write_json(self.evidence_dir / 'answer-feature.json', record)
        skill = self.plugin / 'skills/answer/SKILL.md'
        skill.write_text(skill.read_text() + '\nA later unreviewed change.\n')
        report = check_delivery(self.workspace, self.blueprint_path,
                                self.plan_path, self.evidence_dir, self.plugin)
        self.assertFalse(report['valid'])
        self.assertIn('Plugin changed after validation', report['errors'][0])
        archive = self.workspace / 'must-not-release.zip'
        release = subprocess.run([sys.executable, str(ROOT / 'harness.py'), 'release-package',
                                  '--plugin', str(self.plugin), '--output', str(archive),
                                  '--workspace', str(self.workspace), '--blueprint', str(self.blueprint_path),
                                  '--plan', str(self.plan_path), '--evidence-dir', str(self.evidence_dir)],
                                 capture_output=True, text=True)
        self.assertNotEqual(release.returncode, 0)
        self.assertFalse(archive.exists())


if __name__ == '__main__':
    unittest.main()
