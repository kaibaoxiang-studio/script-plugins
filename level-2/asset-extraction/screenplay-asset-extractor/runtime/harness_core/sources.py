from __future__ import annotations
import json
from pathlib import Path
import re
import stat
import subprocess
import urllib.parse
import urllib.request
import zipfile
import io
from .common import files, sha, inside, now

def discover(query,limit=8):
    url='https://api.github.com/search/repositories?'+urllib.parse.urlencode({'q':query,'per_page':min(limit,20)})
    request=urllib.request.Request(url,headers={'User-Agent':'harness-creator/0.1','Accept':'application/vnd.github+json'})
    with urllib.request.urlopen(request,timeout=30) as response:
        result=json.load(response)
    return {'query':query,'candidates':[{'repository':item['full_name'],'url':item['html_url'],
            'description':item.get('description'),'default_branch':item['default_branch'],
            'updated_at':item['updated_at'],'license':(item.get('license') or {}).get('spdx_id')}
            for item in result['items']]}

def fetch(repo,revision,destination):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repo): raise ValueError('Expected owner/repository')
    if not re.fullmatch(r'[0-9a-f]{40}',revision): raise ValueError('Fetch requires an exact 40-character commit SHA')
    destination=Path(destination).resolve()
    if destination.exists(): raise FileExistsError(destination)
    request=urllib.request.Request(f'https://codeload.github.com/{repo}/zip/{revision}',headers={'User-Agent':'harness-creator/0.1'})
    with urllib.request.urlopen(request,timeout=60) as response:
        raw=response.read(40_000_001)
    if len(raw)>40_000_000: raise ValueError('Candidate archive exceeds 40 MB')
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        records=archive.infolist()
        if sum(item.file_size for item in records)>100_000_000 or len(records)>10000:
            raise ValueError('Candidate archive exceeds inspection limits')
        material=[]
        for item in records:
            mode=(item.external_attr>>16)&0o170000
            if mode==stat.S_IFLNK: raise ValueError('Candidate archive contains symlinks')
            parts=Path(item.filename).parts
            if len(parts)<2 or item.is_dir(): continue
            relative=Path(*parts[1:]).as_posix()
            inside(destination,relative)
            material.append((relative,archive.read(item)))
        destination.mkdir(parents=True)
        for relative,content in material:
            target=inside(destination,relative); target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(content)
    return inspect(destination,origin=f'https://github.com/{repo}',revision=revision)

def inspect(root,origin=None,revision=None):
    root=Path(root).resolve()
    if not root.is_dir(): raise ValueError('Candidate root is not a directory')
    if revision is None and (root/'.git').exists():
        revision=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()
    inventory=[]; signals=[]; licenses=[]; entrypoints=[]
    patterns={'network':r'\b(requests\.|urllib|curl\s|wget\s|fetch\(|socket\.)',
              'process':r'\b(subprocess|os\.system|child_process|exec\(|spawn\()',
              'destructive':r'\b(rm\s+-rf|shutil\.rmtree|git\s+reset\s+--hard)',
              'credentials':r'\b(keychain|\.ssh|\.aws|os\.environ|getenv)\b'}
    for path,relative in files(root):
        if path.stat().st_size>5_000_000:
            signals.append({'file':relative,'signal':'large_file_requires_manual_review'}); continue
        inventory.append({'path':relative,'sha256':sha(path),'bytes':path.stat().st_size})
        if path.name=='SKILL.md' or path.name in {'plugin.json','AGENTS.md','pyproject.toml','package.json'}:
            entrypoints.append(relative)
        if path.name.lower().startswith(('license','copying')):
            licenses.append({'path':relative,'sha256':sha(path)})
        try: text=path.read_text(encoding='utf-8')
        except UnicodeError: continue
        for label,pattern in patterns.items():
            if re.search(pattern,text,re.I): signals.append({'file':relative,'signal':label})
    return {'schema_version':'SourceInspectionV1','origin':origin or str(root),
            'revision':revision,'inspected_at':now(),'entrypoints':entrypoints,'licenses':licenses,
            'files':inventory,'review_signals':signals,
            'status':'inspection_only','note':'Signals identify code to read; absence of signals is not an execution approval.'}

def absorption_plan(root,recipe):
    """Translate reviewed source selections to an explicit patch; never execute candidates."""
    root=Path(root).resolve()
    if not recipe.get('origin') or not recipe.get('revision') or not recipe.get('adaptation'):
        raise ValueError('Absorption requires origin, exact revision and adaptation rationale')
    changes=[]
    for item in recipe.get('selections',[]):
        source=inside(root,item['source'])
        if sha(source)!=item['source_sha256']: raise ValueError('Inspected source changed')
        mode=item.get('mode')
        if mode=='copy':
            if not recipe.get('license') or not recipe.get('license_files'):
                raise ValueError('Copying requires a recorded license and included license files')
            content=source.read_text(encoding='utf-8')
        elif mode=='adapt':
            content=item.get('content')
            if not isinstance(content,str) or not content.strip(): raise ValueError('Provide authored adapted content')
            if not recipe.get('license') or not recipe.get('license_files'):
                raise ValueError('Unlicensed source can inform research; do not adapt its text or code')
        elif mode=='independent':
            content=item['content']
            if not item.get('method_summary'): raise ValueError('Independent implementation requires a method summary')
        else: raise ValueError('Selection mode must be copy, adapt or independent')
        changes.append({'path':item['target'],'expected_sha256':item.get('expected_target_sha256'),'content':content})
    for item in recipe.get('license_files',[]):
        source=inside(root,item['source'])
        if sha(source)!=item['source_sha256']: raise ValueError('Source license changed')
        changes.append({'path':item['target'],'expected_sha256':item.get('expected_target_sha256'),
                        'content':source.read_text(encoding='utf-8')})
    if not changes: raise ValueError('No source selections')
    return {'changes':changes}
