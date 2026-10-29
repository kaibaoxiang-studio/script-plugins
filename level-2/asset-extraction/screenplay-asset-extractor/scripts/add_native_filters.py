"""后端缺少原生筛选 API 时的定向 OOXML 格式补丁；只设置 autoFilter。"""
import argparse
import json
import os
import posixpath
import tempfile
import zipfile
import xml.etree.ElementTree as ET


def add_filters(filename, plan):
    ns = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
    relns = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
    package = 'http://schemas.openxmlformats.org/package/2006/relationships'
    ET.register_namespace('', ns)
    with zipfile.ZipFile(filename) as archive:
        workbook = ET.fromstring(archive.read('xl/workbook.xml'))
        relations = ET.fromstring(archive.read('xl/_rels/workbook.xml.rels'))
        targets = {item.get('Id'): item.get('Target') for item in relations.findall('{'+package+'}Relationship')}
        specs = {spec['name']: spec for spec in plan['sheets']}
        replacements = {}
        for sheet in workbook.find('{'+ns+'}sheets'):
            target = targets[sheet.get('{'+relns+'}id')]
            path = target.lstrip('/') if target.startswith('/') else posixpath.normpath(posixpath.join('xl', target))
            root = ET.fromstring(archive.read(path))
            old = root.find('{'+ns+'}autoFilter')
            if old is not None: root.remove(old)
            auto = ET.Element('{'+ns+'}autoFilter', {'ref': specs[sheet.get('name')]['filter']})
            # ECMA-376 worksheet sequence: autoFilter follows sheetData and sheetProtection etc., precedes mergeCells.
            after = {'sheetPr', 'dimension', 'sheetViews', 'sheetFormatPr', 'cols', 'sheetData', 'sheetCalcPr',
                     'sheetProtection', 'protectedRanges', 'scenarios'}
            index = 0
            while index < len(root) and root[index].tag.split('}')[-1] in after: index += 1
            root.insert(index, auto)
            replacements[path] = ET.tostring(root, encoding='utf-8', xml_declaration=True)
        handle, temporary = tempfile.mkstemp(prefix='native-filters-', suffix='.xlsx', dir=os.path.dirname(os.path.abspath(filename)))
        os.close(handle)
        try:
            with zipfile.ZipFile(temporary, 'w', compression=zipfile.ZIP_DEFLATED) as output:
                for item in archive.infolist(): output.writestr(item, replacements.get(item.filename, archive.read(item.filename)))
            os.replace(temporary, filename)
        finally:
            if os.path.exists(temporary): os.unlink(temporary)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workbook'); parser.add_argument('plan')
    args = parser.parse_args()
    with open(args.plan, encoding='utf-8') as file: plan = json.load(file)
    add_filters(args.workbook, plan)
    print('已设置四表原生筛选；未修改数据及其他格式。')
