"""先检查 JSON 容器及字段类型，让校验器能安全返回错误而不崩溃。"""


def input_errors(data, assets):
    errors = []

    def field(obj, key, kind, path, required=False):
        if key not in obj:
            if required:
                errors.append(f'{path}.{key} 缺少必填字段')
            return False
        value = obj[key]
        if not isinstance(value, kind) or (kind is int and isinstance(value, bool)):
            errors.append(f'{path}.{key} 类型错误，应为 {kind.__name__}')
            return False
        return True

    def objects(obj, key, path, required=False):
        if not field(obj, key, list, path, required):
            return []
        output = []
        for i, item in enumerate(obj[key]):
            item_path = f'{path}.{key}[{i}]'
            if isinstance(item, dict):
                output.append((item, item_path))
            else:
                errors.append(f'{item_path} 类型错误，应为 dict')
        return output

    def strings(obj, key, path, required=False):
        if field(obj, key, list, path, required):
            for i, value in enumerate(obj[key]):
                if not isinstance(value, str):
                    errors.append(f'{path}.{key}[{i}] 类型错误，应为 str')

    def refs(obj, key, path):
        for ref, ref_path in objects(obj, key, path):
            for name, kind in [('scene_id', str), ('line', int), ('quote', str)]:
                field(ref, name, kind, ref_path, True)

    if not isinstance(data, dict) or not isinstance(assets, dict):
        return ['scenes.json 和 assets.json 顶层必须为对象']

    if field(data, 'source', dict, 'script'):
        field(data['source'], 'path', str, 'script.source', True)
        field(data['source'], 'sha256', str, 'script.source', True)
    if field(data, 'parse_report', dict, 'script'):
        report = data['parse_report']
        for key in ('nonempty_paragraphs', 'unrecognized_count', 'max_consecutive_unrecognized', 'table_text_count'):
            if field(report, key, int, 'script.parse_report', True) and report[key] < 0:
                errors.append(f'script.parse_report.{key} 不能为负数')
        for item, path in objects(report, 'unrecognized', 'script.parse_report', True):
            field(item, 'paragraph', int, path, True)
            field(item, 'text', str, path, True)

    for ep, ep_path in objects(data, 'episodes', 'script', True):
        field(ep, 'episode', int, ep_path, True)
        if 'title' not in ep:
            errors.append(f'{ep_path}.title 缺少必填字段')
        if ep.get('title') is not None:  # 解析器允许未写标题时为 null。
            field(ep, 'title', str, ep_path)
        for scene, scene_path in objects(ep, 'scenes', ep_path, True):
            for key in ('scene_id', 'location', 'int_ext', 'time'):
                field(scene, key, str, scene_path, True)
            strings(scene, 'characters', scene_path, True)
            for line, line_path in objects(scene, 'lines', scene_path, True):
                field(line, 'type', str, line_path, True)
                field(line, 'text', str, line_path, True)
                for key in ('speaker', 'emotion', 'voice'):
                    field(line, key, str, line_path)

    for kind in ('characters', 'scenes', 'props'):
        for asset, path in objects(assets, kind, 'assets', True):
            field(asset, 'id', str, path, True)
            field(asset, 'name', str, path, True)
            strings(asset, 'aliases', path)
            for key in ('int_ext', 'times'):
                if key in asset:
                    if isinstance(asset[key], list):
                        strings(asset, key, path)
                    elif not isinstance(asset[key], str):
                        errors.append(f'{path}.{key} 类型错误，应为 str 或字符串数组')
            for key in ('description', 'note', 'role', 'owner'):
                field(asset, key, str, path)
            if kind == 'props':
                field(asset, 'source_name', str, path)
            for state, state_path in objects(asset, 'states', path):
                field(state, 'id', str, state_path, True)
                field(state, 'name', str, state_path, True)
                strings(state, 'scenes', state_path)
                for key in ('basis', 'description', 'note', 'evidence'):
                    field(state, key, str, state_path)
                refs(state, 'evidence_refs', state_path)
                if field(state, 'visual', dict, state_path):
                    for key, value in state['visual'].items():
                        if not isinstance(value, str):
                            errors.append(f'{state_path}.visual.{key} 类型错误，应为 str')
            for sub, sub_path in objects(asset, 'subscenes', path):
                field(sub, 'name', str, sub_path, True)
                field(sub, 'description', str, sub_path)
                strings(sub, 'scenes', sub_path, True)
            for rec, rec_path in objects(asset, 'appearances', path):
                for key in ('id', 'scene_id', 'state_id', 'timeline', 'instance', 'basis', 'boundary'):
                    field(rec, key, str, rec_path, True)
                for key in ('segment', 'note', 'continuity'):
                    field(rec, key, str, rec_path)
                if rec.get('from') is not None:
                    field(rec, 'from', str, rec_path)
                for key in ('start_line', 'end_line'):
                    field(rec, key, int, rec_path, True)
                for key in ('start_offset', 'end_offset'):
                    field(rec, key, int, rec_path)
                refs(rec, 'evidence_refs', rec_path)
                if field(rec, 'presence', dict, rec_path):
                    field(rec['presence'], 'kind', str, rec_path + '.presence', True)
                    refs(rec['presence'], 'refs', rec_path + '.presence')
            for review, review_path in objects(asset, 'change_reviews', path):
                for key in ('candidate_id', 'decision', 'reason'):
                    field(review, key, str, review_path, True)
                strings(review, 'appearance_ids', review_path, True)
                if field(review, 'source', dict, review_path, True):
                    for key, typ in [('scene_id', str), ('line', int), ('quote', str)]:
                        field(review['source'], key, typ, review_path + '.source', True)
            for link, link_path in objects(asset, 'alias_evidence', path):
                for key in ('alias', 'basis', 'reason'):
                    field(link, key, str, link_path, True)
                refs(link, 'evidence_refs', link_path)
            for mention, mention_path in objects(asset, 'mentions', path):
                for key in ('id', 'raw_name', 'basis', 'visibility', 'timeline'):
                    field(mention, key, str, mention_path, True)
                for key in ('holder', 'identity_reason', 'note'):
                    field(mention, key, str, mention_path)
                for key in ('from', 'state_id'):
                    if mention.get(key) is not None:
                        field(mention, key, str, mention_path)
                for key in ('start_offset', 'end_offset'):
                    field(mention, key, int, mention_path, True)
                refs(mention, 'identity_refs', mention_path)
                if field(mention, 'source', dict, mention_path, True):
                    for key, typ in [('scene_id', str), ('line', int), ('quote', str)]:
                        field(mention['source'], key, typ, mention_path + '.source', True)
            for relation, relation_path in objects(asset, 'identity_relations', path):
                for key in ('other_id', 'decision', 'reason'):
                    field(relation, key, str, relation_path, True)
                refs(relation, 'evidence_refs', relation_path)
    return errors
