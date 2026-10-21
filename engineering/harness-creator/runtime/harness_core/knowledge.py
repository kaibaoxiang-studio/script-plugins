from __future__ import annotations
from html.parser import HTMLParser
from pathlib import Path
import hashlib
import json
import shutil
import zipfile
import xml.etree.ElementTree as ET
from .common import read_json, write_json, write_text, digest, sha, now, inside, require_name
from .packages import patch

class PlainHTML(HTMLParser):
    def __init__(self):
        super().__init__(); self.skip=0; self.parts=[]
    def handle_starttag(self,tag,attrs):
        if tag in {'script','style','nav'}: self.skip+=1
        if not self.skip and tag in {'p','div','h1','h2','h3','li','tr','br'}: self.parts.append('\n')
    def handle_endtag(self,tag):
        if tag in {'script','style','nav'}: self.skip=max(0,self.skip-1)
        if not self.skip and tag in {'td','th'}: self.parts.append(' | ')
    def handle_data(self,data):
        if not self.skip: self.parts.append(data)

def extract(path):
    path=Path(path)
    if path.suffix.lower() in {'.html','.htm'}:
        parser=PlainHTML(); parser.feed(path.read_text(encoding='utf-8')); return ''.join(parser.parts)
    if path.suffix.lower()=='.docx':
        with zipfile.ZipFile(path) as archive:
            root=ET.fromstring(archive.read('word/document.xml'))
        namespace='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
        return '\n'.join(''.join(item.itertext()) for item in root.iter(namespace+'p'))
    if path.suffix.lower() not in {'.txt','.md','.markdown','.json','.csv'}:
        raise ValueError('Extract this format into UTF-8 text first, retaining page/paragraph evidence')
    return path.read_text(encoding='utf-8-sig')

def ingest(library,source,source_id=None,origin=None):
    library=Path(library).resolve(); source=Path(source).resolve()
    source_id=source_id or 'src-'+hashlib.sha256((origin or str(source)).encode()).hexdigest()[:12]
    require_name(source_id)
    catalog_path=library/'catalog.json'
    catalog=read_json(catalog_path) if catalog_path.exists() else {'schema_version':'KnowledgeSourcesV1','sources':{}}
    content_hash=sha(source); text=extract(source)
    folder=library/'sources'/source_id/content_hash
    folder.mkdir(parents=True,exist_ok=True)
    original=folder/('original'+source.suffix.lower())
    if not original.exists(): shutil.copy2(source,original)
    write_text(folder/'extracted.md',text)
    record=catalog['sources'].get(source_id,{'id':source_id,'revisions':[]})
    revision={'sha256':content_hash,'origin':origin or str(source),'captured_at':now(),
              'original':str(original.relative_to(library)),'extracted':str((folder/'extracted.md').relative_to(library)),
              'extracted_sha256':sha(folder/'extracted.md')}
    if not any(item['sha256']==content_hash for item in record['revisions']): record['revisions'].append(revision)
    record['current_sha256']=content_hash
    catalog['sources'][source_id]=record
    write_json(catalog_path,catalog)
    return {'source_id':source_id,**revision}

def publish(library,source_id,rules,plugin,capability_id,expected_source,confirmed=False,expected_current=None):
    if not confirmed: raise ValueError('Knowledge publication requires the requested/confirmed scope')
    library=Path(library).resolve(); plugin=Path(plugin).resolve()
    catalog=read_json(library/'catalog.json')
    source=catalog['sources'][source_id]
    if source['current_sha256']!=expected_source: raise ValueError('Source revision changed during authoring')
    revision=next(item for item in source['revisions'] if item['sha256']==expected_source)
    if sha(inside(library,revision['original']))!=expected_source: raise ValueError('Stored original was modified')
    body=Path(rules).read_text(encoding='utf-8')
    if len(body.strip())<40: raise ValueError('Write useful scoped rules and evidence, not an empty knowledge file')
    capabilities=read_json(plugin/'capabilities.json')
    capability=next((item for item in capabilities['capabilities'] if item['id']==capability_id),None)
    if capability is None: raise ValueError('Unknown target capability')
    lock_path=plugin/'knowledge-lock.json'
    lock=read_json(lock_path) if lock_path.exists() else {'schema_version':'KnowledgeSnapshotsV1','snapshots':[]}
    relative=f'references/knowledge/{capability_id}/{source_id}.md'
    target=inside(plugin,relative)
    prior=next((item for item in lock['snapshots'] if item['source_id']==source_id and item['path']==relative),None)
    if target.exists():
        baseline=expected_current or (prior or {}).get('rules_sha256')
        if sha(target)!=baseline: raise ValueError('Knowledge file has local edits; supply reviewed expected-current hash')
    # Only distilled rules and source attribution ship; no private source paths.
    rendered=f'<!-- source-id: {source_id}; revision: {expected_source} -->\n'+body
    refs=capability.setdefault('knowledge_refs',[])
    if relative not in refs: refs.append(relative)
    snapshot={'source_id':source_id,'source_sha256':expected_source,'origin':revision['origin'] if '://' in revision['origin'] else Path(revision['origin']).name,
              'path':relative,'rules_sha256':hashlib.sha256(rendered.encode()).hexdigest(),
              'capability_ids':[capability_id]}
    lock['snapshots']=[item for item in lock['snapshots'] if item['path']!=relative]+[snapshot]
    skill=plugin/f'skills/{capability["skill_name"]}/SKILL.md'
    instructions=skill.read_text(encoding='utf-8')
    link=f'../../{relative}'
    if link not in instructions:
        instructions+=f'\nRead [{source_id}]({link}) when this capability needs the supplied knowledge.\n'
    changes=[]
    for path,content in ((relative,rendered),('capabilities.json',json.dumps(capabilities,ensure_ascii=False,indent=2)+'\n'),
                         ('knowledge-lock.json',json.dumps(lock,ensure_ascii=False,indent=2)+'\n'),
                         (skill.relative_to(plugin).as_posix(),instructions)):
        original=inside(plugin,path)
        changes.append({'path':path,'expected_sha256':sha(original) if original.exists() else None,'content':content})
    return patch(plugin,{'changes':changes},True)

def status(library,plugin):
    sources=read_json(Path(library)/'catalog.json')['sources']
    lock=Path(plugin)/'knowledge-lock.json'
    snapshots=read_json(lock)['snapshots'] if lock.exists() else []
    return {'snapshots':[{**item,'source_newer':sources.get(item['source_id'],{}).get('current_sha256')!=item['source_sha256'],
                          'rules_intact':sha(inside(plugin,item['path']))==item['rules_sha256']} for item in snapshots]}
