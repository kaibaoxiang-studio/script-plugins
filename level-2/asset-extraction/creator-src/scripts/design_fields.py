"""设计补全层：原文事实之外，供美术/制作直接使用的完整描述。

design 只用于展示和制作，不参与状态拆分、场次分配或出镜判断；原文事实仍写在 description/evidence。
"""
import re

CHARACTER_BASE = [('age', '年龄段'), ('build', '身高体型'), ('face', '脸型五官'), ('hair', '发型发色'),
                  ('skin', '肤色'), ('temperament', '气质神态'), ('signature', '标志性特征'),
                  ('identity', '身份与时代背景')]
CHARACTER_STATE = [('costume', '服装款式'), ('color_material', '颜色材质'), ('accessories', '配饰'),
                   ('hair_makeup', '妆发'), ('injury_stains', '伤势污损'), ('difference', '与其他状态差异')]
SUBSCENE = [('layout', '空间结构与尺度'), ('furnishings', '主要陈设'), ('material_color', '材质色调'),
            ('lighting', '光源光线'), ('style', '时代风格'), ('atmosphere', '氛围')]
PROP_BASE = [('shape_size', '外形尺寸'), ('material_color', '材质颜色'), ('structure', '结构细节'),
             ('markings', '标记纹饰'), ('usage', '使用方式')]
PROP_STATE = [('appearance', '本状态外观'), ('damage', '破损污损'), ('difference', '与其他状态差异')]
# 群演按群组制作，只填精简版；需要单独设计的改为配角即按全套要求。
CROWD_BASE = [('age', '年龄段'), ('identity', '身份与时代背景'), ('overall', '整体外形特征')]
CROWD_STATE = [('costume', '服装款式'), ('color_material', '颜色材质')]
# 场景首个状态即子场景设计本身；之后的布置/破坏状态另写设计。
SCENE_STATE = [('appearance', '本状态布置或破坏'), ('difference', '与常态差异')]


def character_fields(character):
    """按角色类型返回 (基础设定字段, 状态字段)。"""
    if (character.get('role') or '').strip() == '群演':
        return CROWD_BASE, CROWD_STATE
    return CHARACTER_BASE, CHARACTER_STATE

# 设计层必须给出可制作的结论；信息缺口写进 design_basis 的推断理由，而不是字段值。
BANNED = re.compile(r'未说明|未描写|未明示|未写明|未提及|未交代|不详(?![细尽])|待设计|待确认|待补充|待定|暂无|无法确定|剧本未|原文未')
EMPTY = re.compile(r'^(?:无|—+|-+|略|同上|同前|见上|见原文|N/?A)[。.]?$', re.I)


def design_text(item, fields):
    design = item.get('design') if isinstance(item.get('design'), dict) else {}
    lines = [f'{label}：{design[key]}' for key, label in fields if design.get(key)]
    if item.get('design_basis'):
        lines.append('【依据】' + item['design_basis'])
    return '\n'.join(lines)


def facts_only(text):
    # 去掉「…未说明」之类的缺口分句，由【设计】段补足；按句、分号、逗号切分并保留原标点。
    # 整段都是缺口说法时返回空，由 combined_text 退回原文显示。
    pieces = re.findall(r'[^。；;，,\n]+[。；;，,\n]?', text or '')
    kept = ''.join(p for p in pieces if p.strip() and not BANNED.search(p)).strip()
    kept = kept.rstrip('。；;，,\n')
    return kept + '。' if kept else ''


def combined_text(item, fields):
    """同一单元格内分段展示：【原文】剧本事实，【设计】可制作的设计补全及依据。

    原文被完全过滤时仍保留原文，因为「未说明」本身也是事实，交付表应如实显示。
    """
    desc = item.get('description', '')
    original = facts_only(desc)
    parts = []
    if desc:
        # 有原文就显示；过滤只去掉「未说明」类占位句，但不让整段原文消失
        parts.append('【原文】' + (original if original else desc))
    design = design_text(item, fields)
    if design:
        parts.append('【设计】\n' + design)
    return '\n'.join(parts)


def _check(item, fields, label, errors):
    design = item.get('design')
    if not isinstance(design, dict):
        errors.append(f'{label} 缺少 design 设计补全（须填写：{"、".join(l for _, l in fields)}）')
        return
    for key, name in fields:
        value = design.get(key)
        if not isinstance(value, str) or not value.strip():
            errors.append(f'{label}.design.{key}（{name}）未填写')
        elif BANNED.search(value) or EMPTY.match(value.strip()):
            errors.append(f'{label}.design.{key}（{name}）不能写占位或「未说明」，须给出可制作的具体设计：{value[:30]}')
    basis = item.get('design_basis')
    if not isinstance(basis, str) or len(basis.strip()) < 6:
        errors.append(f'{label} 缺少 design_basis：写明哪些来自原文、设定文件，哪些按身份/时代/剧情推断')


def design_errors(assets):
    errors = []
    for c in assets.get('characters', []):
        label = f'[人物] {c.get("id")} {c.get("name")}'
        base, state_fields = character_fields(c)
        _check(c, base, label, errors)
        for st in c.get('states', []):
            _check(st, state_fields, f'{label}-{st.get("id")}', errors)
    for a in assets.get('scenes', []):
        label = f'[场景] {a.get("id")} {a.get("name")}'
        if a.get('subscenes'):
            for sub in a['subscenes']:
                _check(sub, SUBSCENE, f'{label}/{sub.get("name")}', errors)
        else:
            _check(a, SUBSCENE, label, errors)
        for st in a.get('states', [])[1:]:
            _check(st, SCENE_STATE, f'{label}-{st.get("id")} {st.get("name")}', errors)
    for p in assets.get('props', []):
        label = f'[道具] {p.get("id")} {p.get("name")}'
        _check(p, PROP_BASE, label, errors)
        for st in p.get('states', []):
            _check(st, PROP_STATE, f'{label}-{st.get("id")}', errors)
    return errors
