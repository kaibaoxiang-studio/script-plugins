#!/usr/bin/env python3
"""Completion-gate regressions using authored semantic-review fixtures, not a model."""
from copy import deepcopy
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from asset_core import assets_digest, finalize, initial_work, write_json


def source_fixture(no_props=False):
    text = '林禾站在走廊，平静地看向邵叔。' if no_props else '林禾拿起铜钥匙，把手机递给邵叔。'
    return {'schema_version': 'standardized_screenplay_v1', 'input_kind': 'script',
            'needs_creative_pass': False, 'coverage': {'status': 'parsed', 'unassigned_source_refs': []},
            'episodes': [{'number': 1, 'scenes': [{'number': '1-1', 'location': '走廊',
                'source_heading': '1-1 走廊 内 日', 'characters': ['林禾', '邵叔'], 'source_refs': ['L1'],
                'blocks': [{'type': 'action', 'text': text, 'source_refs': ['L2'], 'origin': 'source'},
                           {'type': 'dialogue', 'speaker': '邵叔', 'text': '我知道了。',
                            'source_refs': ['L3'], 'origin': 'source'}]}]}]}


def reviewed_fixture(work, no_props=False):
    """Hand-authored choices for this tiny fixture; never used by the plugin."""
    work = deepcopy(work)
    for char in work['assets']['characters']:
        char['tier'] = '配角'
    prop_ids = []
    if not no_props:
        for index, name in enumerate(['铜钥匙', '手机'], 1):
            ev = {'scene_id': '1-1', 'text': work['scenes'][0]['blocks'][0]['text'],
                  'source_refs': ['L2'], 'origin': 'source'}
            aid = f'PRP-{index:03d}'
            prop_ids.append(aid)
            work['assets']['props'].append({'id': aid, 'name': name, 'aliases': [], 'alias_evidence': [],
                'script_facts': [], 'evidence': [ev], 'states': [{'id': 'S01', 'name': '常态',
                    'scenes': ['1-1'], 'script_facts': [], 'evidence': [ev]}]})
    prop_conclusion = ('人物只是站立、对话，没有画面使用或明确制作的可移动物件。' if no_props
                       else '铜钥匙被拿取、手机被交接，均有画面使用依据；归属和材质未说明不妨碍登记。')
    work['semantic_review'] = {'schema_version': 'asset_semantic_review_v1',
        'source_sha256': work['source']['sha256'], 'assets_sha256': assets_digest(work['assets']),
        'scenes': [{'scene_id': '1-1', 'blocks': [
            {'block_index': 0, 'source_refs': ['L2'], 'origin': 'source',
             'text': work['scenes'][0]['blocks'][0]['text'],
             'asset_ids': ['CHR-001', 'CHR-002', *prop_ids], 'conclusion': prop_conclusion},
            {'block_index': 1, 'source_refs': ['L3'], 'origin': 'source', 'text': '邵叔：我知道了。',
             'asset_ids': ['CHR-002'], 'conclusion': '邵叔对白，没有新增物件或视觉状态变化。'}],
          'categories': {
            'characters': {'asset_ids': ['CHR-001', 'CHR-002'], 'conclusion': '林禾与邵叔在场，按剧情配角登记。'},
            'locations': {'asset_ids': ['SCN-001'], 'conclusion': '本场只在走廊，无须拆分其他空间。'},
            'props': {'asset_ids': prop_ids, 'conclusion': prop_conclusion},
            'effects': {'asset_ids': [], 'conclusion': '仅日常对话和实物动作，没有独立制作特效。'}},
          'exclusions': []}]}
    return work


class CompletionGate(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory(prefix='asset-semantic-gate-')
        self.root = Path(self.tmp.name)
        self.source = self.root / 'source.json'
        write_json(self.source, source_fixture())
        self.seed = initial_work(self.source)
        self.good = reviewed_fixture(self.seed)

    def tearDown(self):
        self.tmp.cleanup()

    def export(self, work):
        path = self.root / 'work.json'
        write_json(path, work)
        return finalize(path, self.root / 'out')

    def test_seed_cannot_be_published(self):
        with self.assertRaisesRegex(ValueError, '层级未完成'):
            self.export(self.seed)
        self.assertFalse((self.root / 'out/assets.json').exists())

    def test_tiers_alone_are_not_semantic_completion(self):
        work = deepcopy(self.seed)
        for char in work['assets']['characters']:
            char['tier'] = '配角'
        work['semantic_review']['assets_sha256'] = assets_digest(work['assets'])
        with self.assertRaisesRegex(ValueError, '尚缺场次'):
            self.export(work)

    def test_explicit_pickup_and_handover_export_props(self):
        self.assertEqual(self.export(self.good)['props'], 2)
        result = json.loads((self.root / 'out/assets.json').read_text())
        self.assertEqual(result['semantic_review'], self.good['semantic_review'])

    def test_genuinely_no_props_is_valid_after_review(self):
        write_json(self.source, source_fixture(no_props=True))
        work = reviewed_fixture(initial_work(self.source), no_props=True)
        self.assertEqual(self.export(work)['props'], 0)

    def test_legacy_work_needs_review_not_blanket_rejection_of_old_outputs(self):
        work = deepcopy(self.good)
        del work['semantic_review']
        with self.assertRaisesRegex(ValueError, '旧工作文件须回查'):
            self.export(work)

    def test_missing_scene(self):
        work = deepcopy(self.good)
        work['semantic_review']['scenes'] = []
        with self.assertRaisesRegex(ValueError, '尚缺场次'):
            self.export(work)

    def test_missing_block(self):
        work = deepcopy(self.good)
        work['semantic_review']['scenes'][0]['blocks'].pop()
        with self.assertRaisesRegex(ValueError, '内容块审核未全覆盖'):
            self.export(work)

    def test_wrong_ref_and_origin_are_rejected(self):
        for field, value, message in [('source_refs', ['L999'], '来源位置不符'), ('origin', 'generated', 'origin 不符')]:
            with self.subTest(field=field):
                work = deepcopy(self.good)
                work['semantic_review']['scenes'][0]['blocks'][0][field] = value
                with self.assertRaisesRegex(ValueError, message):
                    self.export(work)

    def test_wrong_review_quote(self):
        work = deepcopy(self.good)
        work['semantic_review']['scenes'][0]['blocks'][0]['text'] = '并不存在的奖杯'
        with self.assertRaisesRegex(ValueError, '审核引文'):
            self.export(work)

    def test_unknown_asset_and_category_assignment_mismatch(self):
        work = deepcopy(self.good)
        work['semantic_review']['scenes'][0]['blocks'][0]['asset_ids'].append('PRP-999')
        with self.assertRaisesRegex(ValueError, '未登记'):
            self.export(work)
        work = deepcopy(self.good)
        work['semantic_review']['scenes'][0]['categories']['props']['asset_ids'] = []
        with self.assertRaisesRegex(ValueError, '实际状态场次不一致'):
            self.export(work)

    def test_prop_needs_block_decision(self):
        work = deepcopy(self.good)
        work['semantic_review']['scenes'][0]['blocks'][0]['asset_ids'] = ['CHR-001', 'CHR-002']
        with self.assertRaisesRegex(ValueError, '实际判读记录'):
            self.export(work)

    def test_empty_zero_result_conclusion(self):
        work = deepcopy(self.good)
        work['semantic_review']['scenes'][0]['categories']['effects']['conclusion'] = ''
        with self.assertRaisesRegex(ValueError, '零结果也须说明'):
            self.export(work)

    def test_old_asset_snapshot_is_rejected(self):
        work = deepcopy(self.good)
        work['assets']['props'][0]['states'][0]['name'] = '未损坏'
        with self.assertRaisesRegex(ValueError, '资产快照已变化'):
            self.export(work)

    def test_old_source_snapshot_is_rejected(self):
        work = deepcopy(self.good)
        work['semantic_review']['source_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, '来源已变化'):
            self.export(work)
        source = source_fixture()
        source['episodes'][0]['scenes'][0]['blocks'][0]['text'] += '随后离开。'
        write_json(self.source, source)
        with self.assertRaisesRegex(ValueError, '一级 JSON 已变化'):
            self.export(self.good)

    def test_exclusion_requires_actual_scene_evidence(self):
        work = deepcopy(self.good)
        work['semantic_review']['scenes'][0]['exclusions'] = [
            {'category': 'props', 'reason': '只被提到，不在画面中。',
             'evidence': [{'scene_id': '1-1', 'text': '虚构的衣柜', 'source_refs': ['L2'], 'origin': 'source'}]}]
        with self.assertRaisesRegex(ValueError, '证据文字'):
            self.export(work)

    def test_review_cannot_fake_coverage_with_duplicate_indices_or_scenes(self):
        for key in ['blocks', 'scenes']:
            with self.subTest(key=key):
                work = deepcopy(self.good)
                if key == 'blocks':
                    work['semantic_review']['scenes'][0]['blocks'][1] = deepcopy(work['semantic_review']['scenes'][0]['blocks'][0])
                else:
                    work['semantic_review']['scenes'].append(deepcopy(work['semantic_review']['scenes'][0]))
                with self.assertRaisesRegex(ValueError, '重复'):
                    self.export(work)


if __name__ == '__main__':
    unittest.main()
