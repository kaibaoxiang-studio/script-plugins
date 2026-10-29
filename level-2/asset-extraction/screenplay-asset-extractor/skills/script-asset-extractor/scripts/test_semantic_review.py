"""人工定义的合成夹具；验证审核门槛，不冒充实际模型提取。"""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from semantic_review import (SCHEMA, asset_snapshot, canonical_sha256,
                             scene_asset_ids, validate_semantic_review)


def record_test_review(data, assets):
    """仅为本仓库已人工规定取舍的回归夹具附审核，不适用于真实素材。"""
    records = []
    for ep in data['episodes']:
        for scene in ep['scenes']:
            sid = scene['scene_id']
            ids = scene_asset_ids(assets, sid)
            rows = []
            for number, line in enumerate(scene['lines'], 1):
                line_ids = set(ids['scenes'])
                for char in assets['characters']:
                    if char['id'] in ids['characters'] and any(
                            rec['scene_id'] == sid and rec['start_line'] <= number <= rec['end_line']
                            for rec in char.get('appearances', [])):
                        line_ids.add(char['id'])
                for prop in assets['props']:
                    if prop['id'] in ids['props'] and any(
                            m['visibility'] == 'visible' and m['source']['scene_id'] == sid
                            and m['source']['line'] == number for m in prop.get('mentions', [])):
                        line_ids.add(prop['id'])
                rows.append({'line': number, 'quote': line['text'], 'asset_ids': sorted(line_ids),
                             'conclusion': '合成夹具预先规定：本行的出镜、变化和物件取舍与人工定义记录一致。'})
            records.append({'scene_id': sid, 'lines': rows,
                            'categories': {kind: {'asset_ids': sorted(value),
                                'conclusion': ('合成夹具预先规定：本场该类资产均已关联。' if value
                                               else '合成夹具预先规定：本场不另立该类资产。')}
                                for kind, value in ids.items()}, 'exclusions': []})
    assets['semantic_review'] = {'schema_version': SCHEMA, 'source_sha256': canonical_sha256(data),
        'assets_sha256': canonical_sha256(asset_snapshot(assets)), 'scenes': records}


def fixture(with_props=False):
    text = '一只手拿起铜钥匙，把手机放在桌上。' if with_props else '镜头停留在空房间，没有人物或可移动物品出镜。'
    scene = {'scene_id': '1-1', 'location': '房间', 'int_ext': '内', 'time': '日',
             'characters': [], 'lines': [{'type': 'action', 'text': text}]}
    data = {'episodes': [{'episode': 1, 'title': '合成测试', 'scenes': [scene]}]}
    assets = {'characters': [], 'scenes': [{'id': 'SCN-001', 'name': '房间', 'int_ext': '内',
        'times': ['日'], 'subscenes': [{'name': '房间', 'scenes': ['1-1']}]}], 'props': []}
    if with_props:
        for number, name in enumerate(['铜钥匙', '手机'], 1):
            low = text.index(name)
            assets['props'].append({'id': f'PRP-{number:03d}', 'name': name, 'aliases': [],
                'owner': '', 'alias_evidence': [], 'states': [{'id': 'S01', 'name': '常态', 'scenes': ['1-1']}],
                'mentions': [{'id': 'M001', 'raw_name': name, 'basis': 'named', 'visibility': 'visible',
                    'timeline': '现实', 'state_id': 'S01', 'start_offset': low, 'end_offset': low + len(name),
                    'source': {'scene_id': '1-1', 'line': 1, 'quote': text}}]})
    return data, assets


class SemanticReviewTests(unittest.TestCase):
    def test_handling_key_and_phone_without_review_is_blocked(self):
        from build_xlsx import validate
        data, assets = fixture(True)
        assets['props'] = []
        errors, _ = validate(data, assets)
        self.assertTrue(any('semantic_review' in error for error in errors), errors)

    def test_completed_flag_without_records_does_not_pass(self):
        data, assets = fixture()
        assets['semantic_review'] = {'schema_version': SCHEMA, 'completed': True,
            'source_sha256': canonical_sha256(data), 'assets_sha256': canonical_sha256(asset_snapshot(assets)), 'scenes': []}
        self.assertTrue(any('场次覆盖不完整' in error for error in validate_semantic_review(data, assets)))

    def test_genuinely_empty_props_can_pass_with_review(self):
        from build_xlsx import validate
        data, assets = fixture()
        record_test_review(data, assets)
        assets['semantic_review']['scenes'][0]['categories']['props']['conclusion'] = '本场仅为空房间静景，原文明确没有可移动物品出镜，无需独立道具。'
        self.assertEqual(validate(data, assets), ([], []))

    def test_actual_props_pass_and_unknown_owner_is_allowed(self):
        from build_xlsx import validate
        data, assets = fixture(True)
        record_test_review(data, assets)
        self.assertEqual(validate(data, assets), ([], []))

    def test_missing_line_and_category_conclusion_are_blocked(self):
        data, assets = fixture()
        record_test_review(data, assets)
        review = assets['semantic_review']['scenes'][0]
        review['lines'] = []
        review['categories']['props']['conclusion'] = ''
        errors = validate_semantic_review(data, assets)
        self.assertTrue(any('未完成逐行' in e for e in errors), errors)
        self.assertTrue(any('类别结论' in e for e in errors), errors)

    def test_partial_or_fabricated_line_quote_is_blocked(self):
        data, assets = fixture(True)
        record_test_review(data, assets)
        assets['semantic_review']['scenes'][0]['lines'][0]['quote'] = '一只手'
        self.assertTrue(any('完整对应' in e for e in validate_semantic_review(data, assets)))

    def test_source_edit_and_asset_state_edit_invalidate_review(self):
        for target in ['source', 'assets']:
            data, assets = fixture(True)
            record_test_review(data, assets)
            if target == 'source': data['episodes'][0]['scenes'][0]['time'] = '夜'
            else: assets['props'][0]['states'][0]['name'] = '折断'
            self.assertTrue(any('快照已变化' in e for e in validate_semantic_review(data, assets)))

    def test_ids_must_match_actual_scene_allocation(self):
        data, assets = fixture(True)
        record_test_review(data, assets)
        assets['semantic_review']['scenes'][0]['categories']['props']['asset_ids'] = ['PRP-999']
        self.assertTrue(any('实际状态/子场景不一致' in e for e in validate_semantic_review(data, assets)))

    def test_prop_usage_must_be_linked_to_line_review(self):
        data, assets = fixture(True)
        record_test_review(data, assets)
        assets['semantic_review']['scenes'][0]['lines'][0]['asset_ids'] = ['SCN-001']
        self.assertTrue(any('未关联逐行审核' in e for e in validate_semantic_review(data, assets)))

    def test_exclusion_requires_real_source_evidence(self):
        data, assets = fixture(True)
        record_test_review(data, assets)
        review = assets['semantic_review']['scenes'][0]
        review['exclusions'] = [{'category': 'props', 'reason': '桌子为固定陈设，归场景',
            'evidence': [{'scene_id': '1-1', 'line': 1, 'quote': '桌上'}]}]
        self.assertEqual(validate_semantic_review(data, assets), [])
        review['exclusions'][0]['evidence'][0]['quote'] = '原文没有这句话'
        self.assertTrue(any('证据与当前原文不符' in e for e in validate_semantic_review(data, assets)))

    def test_malformed_review_returns_errors_without_traceback(self):
        for malformed in [None, [], {'schema_version': SCHEMA, 'scenes': [None, {'scene_id': []}]}]:
            data, assets = fixture()
            assets['semantic_review'] = malformed
            self.assertTrue(validate_semantic_review(data, assets))

    def test_cli_blocks_formal_export_and_plan_without_review(self):
        with tempfile.TemporaryDirectory(prefix='docx-review-gate-') as folder:
            root = Path(folder)
            data, assets = fixture(True)
            source, extracted = root / 'scenes.json', root / 'assets.json'
            source.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
            extracted.write_text(json.dumps(assets, ensure_ascii=False), encoding='utf-8')
            before = extracted.read_bytes()
            command = [sys.executable, str(Path(__file__).with_name('build_xlsx.py')), str(source), str(extracted)]
            for mode in [['--check'], [str(root / 'assets.xlsx')], ['--export-spec', str(root / 'plan.json')]]:
                result = subprocess.run(command + mode, capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('semantic_review', result.stdout)
                self.assertNotIn('Traceback', result.stdout + result.stderr)
            self.assertFalse((root / 'assets.xlsx').exists())
            self.assertFalse((root / 'plan.json').exists())
            self.assertEqual(extracted.read_bytes(), before)

    def test_empty_source_cannot_be_marked_complete(self):
        data = {'episodes': []}
        assets = {'characters': [], 'scenes': [], 'props': []}
        record_test_review(data, assets)
        self.assertTrue(any('没有有效场次' in e for e in validate_semantic_review(data, assets)))

    def test_cli_reviewed_empty_scene_exports_and_saved_workbook_is_checked(self):
        with tempfile.TemporaryDirectory(prefix='docx-reviewed-empty-') as folder:
            root = Path(folder)
            data, assets = fixture()
            record_test_review(data, assets)
            source, extracted, output = root / 'scenes.json', root / 'assets.json', root / 'assets.xlsx'
            source.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
            extracted.write_text(json.dumps(assets, ensure_ascii=False), encoding='utf-8')
            result = subprocess.run([sys.executable, str(Path(__file__).with_name('build_xlsx.py')),
                                     str(source), str(extracted), str(output)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            result = subprocess.run([sys.executable, str(Path(__file__).with_name('check_workbook.py')),
                                     str(source), str(extracted), str(output)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__': unittest.main(verbosity=2)
