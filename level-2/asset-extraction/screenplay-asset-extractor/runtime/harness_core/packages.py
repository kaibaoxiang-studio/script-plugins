from __future__ import annotations
import ast
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import zipfile
import yaml
from jsonschema import Draft202012Validator
from .common import inside, files, sha, read_json, write_json, write_text, require_name
from .contracts import graph_order, validate_data

RESERVED = {'capabilities.json','plugin.json','.codex-plugin/plugin.json','harness.py',
            'requirements.lock','scripts/bootstrap.py','generation-lock.json'}

def skill_metadata(path):
    text=Path(path).read_text(encoding='utf-8')
    match=re.match(r'\A---\s*\n(.*?)\n---\s*\n(.*)',text,re.S)
    if not match: raise ValueError(f'Missing YAML frontmatter: {path}')
    metadata=yaml.safe_load(match[1])
    if not isinstance(metadata,dict): raise ValueError('Skill metadata must be a mapping')
    require_name(metadata.get('name'))
    if not isinstance(metadata.get('description'),str) or not metadata['description'].strip():
        raise ValueError('Skill requires a description')
    if len(match[2].strip())<50 or re.search(r'\[TODO[^]]*\]|\bPLACEHOLDER\b',match[2]):
        raise ValueError(f'Unfinished skill body: {path}')
    return metadata,match[2]

def validate_plugin(root):
    root=Path(root).resolve()
    errors=[]
    try:
        manifest=read_json(root/'.codex-plugin/plugin.json')
        require_name(manifest['name'])
        if not re.fullmatch(r'\d+\.\d+\.\d+(?:-[a-zA-Z0-9.-]+)?',manifest['version']):
            raise ValueError('Plugin version must be semantic version')
        if manifest.get('skills')!='./skills/': raise ValueError('Plugin skills must use ./skills/')
        for field in ('description','author'):
            if not manifest.get(field): raise ValueError(f'Manifest missing {field}')
        catalog=read_json(root/'capabilities.json')
        if catalog.get('schema_version')!='CapabilityCatalogV1': raise ValueError('Invalid capability catalog')
        capabilities={}
        for item in catalog['capabilities']:
            require_name(item['id'])
            if item['id'] in capabilities: raise ValueError('Duplicate capability id')
            capabilities[item['id']]=item
            require_name(item['skill_name'])
            skill=inside(root,f'skills/{item["skill_name"]}/SKILL.md')
            metadata,_=skill_metadata(skill)
            if metadata['name']!=item['skill_name']: raise ValueError('Skill name does not match directory')
            for schema in ('input_schema','output_schema'):
                Draft202012Validator.check_schema(item[schema])
            execution=item['execution']
            if execution['kind'] not in {'agent','python'}: raise ValueError('Unknown execution kind')
            if execution['kind']=='python':
                script=inside(root,execution['script'])
                if not script.is_file() or script.suffix!='.py': raise ValueError('Python script missing')
            if execution.get('access','read-only') not in {'read-only','workspace-write'}:
                raise ValueError('Invalid Agent filesystem policy')
            if execution.get('network',False) and execution['kind']=='agent' and execution.get('access','read-only')=='read-only':
                raise ValueError('Network Agent nodes must explicitly declare workspace-write execution')
            for reference in item.get('knowledge_refs',[]):
                if not inside(root,reference).is_file(): raise ValueError(f'Missing knowledge: {reference}')
        if not capabilities: raise ValueError('Plugin has no capabilities')
        for workflow in catalog.get('workflows',[]): graph_order(workflow,capabilities)
        for path,relative in files(root):
            if path.suffix=='.py': ast.parse(path.read_text(encoding='utf-8'),filename=relative)
            if path.name=='SKILL.md':
                _,body=skill_metadata(path)
                for link in re.findall(r'\]\(([^)]+)\)',body):
                    if '://' in link or link.startswith('#'): continue
                    target=path.parent/link.split('#')[0]
                    if not target.resolve().is_relative_to(root) or not target.exists():
                        errors.append(f'{relative}: missing or escaping reference {link}')
            if path.name=='openai.yaml':
                value=yaml.safe_load(path.read_text(encoding='utf-8'))
                if not isinstance(value,dict) or not isinstance(value.get('interface'),dict):
                    errors.append(f'Invalid agent metadata: {relative}')
        lock=root/'knowledge-lock.json'
        if lock.exists():
            for record in read_json(lock).get('snapshots',[]):
                if sha(inside(root,record['path']))!=record['rules_sha256']:
                    errors.append(f'Knowledge snapshot modified outside maintenance: {record["path"]}')
        return {'valid':not errors,'errors':errors,'capabilities':len(capabilities),'skills':len(list((root/'skills').glob('*/SKILL.md')))}
    except (ValueError,KeyError,OSError,SyntaxError,yaml.YAMLError) as exc:
        return {'valid':False,'errors':[str(exc)],'capabilities':0}

def validate_spec(spec):
    validate_data(spec,read_json(Path(__file__).resolve().parents[2]/'schemas/blueprint.schema.json'))
    if spec.get('schema_version')!='HarnessBlueprintV1': raise ValueError('Expected HarnessBlueprintV1')
    if spec.get('open_questions',[]): raise ValueError('Resolve consequential questions before building')
    for key in ('goal','acceptance_criteria','plugin','capabilities'):
        if not spec.get(key): raise ValueError(f'Blueprint missing {key}')
    require_name(spec['plugin']['name'])
    for capability in spec['capabilities']:
        for field in ('id','skill_name','description','instructions','input_schema','output_schema','execution'):
            if field not in capability: raise ValueError(f'Capability missing {field}')
        if len(capability['instructions'].strip())<50:
            raise ValueError('Provide authored behavior, not a placeholder')
    for path in spec.get('files',{}):
        if path in RESERVED or path.startswith(('runtime/','.harness/')):
            raise ValueError(f'Generator-owned resource: {path}')
    for source in spec.get('sources',[]):
        if not all(source.get(key) for key in ('origin','revision','adaptation')):
            raise ValueError('Source receipt needs origin, revision and adaptation')
        if source.get('copied_files') and not source.get('license'):
            raise ValueError('Copied source requires a recorded license')

def _skill(root,name,description,body,explicit=False):
    target=root/'skills'/name
    target.mkdir(parents=True,exist_ok=True)
    write_text(target/'SKILL.md',f'---\nname: {name}\ndescription: {json.dumps(description,ensure_ascii=False)}\n---\n\n{body.strip()}\n')
    write_text(target/'agents/openai.yaml',yaml.safe_dump({
        'interface':{'display_name':name,'short_description':description[:64],
                     'default_prompt':f'Use ${name} to complete the requested task.'},
        'policy':{'allow_implicit_invocation':not explicit}},allow_unicode=True,sort_keys=False))

def build(spec,output,core_root,confirmed=False):
    if not confirmed: raise ValueError('Build requires the confirmed design (--confirmed)')
    validate_spec(spec)
    output=Path(output).resolve()
    if output.exists(): raise FileExistsError(f'Output already exists: {output}')
    output.parent.mkdir(parents=True,exist_ok=True)
    staging=Path(tempfile.mkdtemp(prefix='.harness-build-',dir=output.parent))
    try:
        plugin=spec['plugin']
        manifest={**plugin,'skills':'./skills/','requires_local_executor':True}
        manifest['author']=plugin.get('author',{'name':'Local creator'})
        write_json(staging/'.codex-plugin/plugin.json',manifest)
        write_json(staging/'plugin.json',{'$schema':'https://agent-plugins.org/schemas/1.0.0/plugin.schema.json',
            **plugin,'extensions':{'com.openai':{'requires_local_executor':True}}})
        catalog={'schema_version':'CapabilityCatalogV1','capabilities':[], 'workflows':spec.get('workflows',[])}
        for capability in spec['capabilities']:
            item={key:value for key,value in capability.items() if key!='instructions'}
            catalog['capabilities'].append(item)
            refs='\n'.join(f'- [{path}](../../{path})' for path in item.get('knowledge_refs',[]))
            body=capability['instructions']
            if refs: body+='\n\n## Packaged references\n\n'+refs
            _skill(staging,item['skill_name'],item['description'],body,capability.get('explicit_only',False))
        if plugin['name'] not in {item['skill_name'] for item in spec['capabilities']}:
            routes='\n'.join(f'- `${item["skill_name"]}`: {item["description"]}' for item in spec['capabilities'])
            _skill(staging,plugin['name'],plugin['description'],
                f'# {plugin["name"]}\n\n{spec["goal"]}\n\nMatch the request to a capability below. Read its SKILL.md and relevant references. '
                'Ask only for missing consequential inputs; preserve established decisions. Run Python-backed capabilities through the bundled harness. '
                'Use the workspace selected by the user and report actual artifacts and remaining failures.\n\n'+routes+
                '\n\nSee [runtime instructions](../../RUNTIME.md).',True)
        write_json(staging/'capabilities.json',catalog)
        for relative,content in spec.get('files',{}).items():
            if not isinstance(content,str): raise ValueError('Blueprint file contents must be text')
            write_text(inside(staging,relative),content)
        core_root=Path(core_root).resolve()
        shutil.copytree(core_root/'runtime',staging/'runtime',ignore=shutil.ignore_patterns('__pycache__'))
        for relative in ('harness.py','scripts/bootstrap.py','requirements.lock','RUNTIME.md','THIRD_PARTY_NOTICES.md'):
            target=staging/relative; target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(core_root/relative,target)
        shutil.copytree(core_root/'licenses',staging/'licenses')
        shutil.copytree(core_root/'schemas',staging/'schemas',dirs_exist_ok=True)
        write_json(staging/'harness-blueprint.json',spec)
        write_json(staging/'sources.lock.json',{'schema_version':'SourceReceiptsV1','sources':spec.get('sources',[])})
        result=validate_plugin(staging)
        if not result['valid']: raise ValueError('; '.join(result['errors']))
        write_json(staging/'generation-lock.json',{'files':{relative:sha(path) for path,relative in files(staging)}})
        os.replace(staging,output)
        return {'status':'built','path':str(output),'validation':result}
    finally:
        if staging.exists(): shutil.rmtree(staging)

def package(root,destination):
    root=Path(root).resolve(); destination=Path(destination).resolve()
    validation=validate_plugin(root)
    if not validation['valid']: raise ValueError('; '.join(validation['errors']))
    if destination.exists(): raise FileExistsError(destination)
    if destination.is_relative_to(root) and 'dist' not in destination.relative_to(root).parts:
        raise ValueError('Package output must be outside the source tree or in dist/')
    destination.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED) as archive:
        for path,relative in files(root):
            if relative.startswith('tests/'): continue
            archive.write(path,root.name+'/'+relative)
    return {'path':str(destination),'sha256':sha(destination),'validation':validation}

def patch(root,plan,confirmed=False):
    if not confirmed: raise ValueError('Patch requires the requested or confirmed change')
    root=Path(root).resolve()
    changes=plan.get('changes',[])
    if not changes: raise ValueError('No changes')
    names=[item['path'] for item in changes]
    if len(names)!=len(set(names)): raise ValueError('Duplicate patch destination')
    for change in changes:
        path=inside(root,change['path'])
        actual=sha(path) if path.is_file() else None
        if actual!=change.get('expected_sha256'):
            raise ValueError(f'Concurrent/user edit conflict: {change["path"]}')
        if path.exists() and not path.is_file(): raise ValueError('Patch target must be a file')
    parent=Path(tempfile.mkdtemp(prefix='.harness-patch-',dir=root.parent))
    candidate=parent/'candidate'
    backup={}
    try:
        shutil.copytree(root,candidate,ignore=shutil.ignore_patterns('.venv','.git','.harness','__pycache__','dist'))
        for change in changes:
            path=inside(candidate,change['path'])
            if change.get('delete'): path.unlink(missing_ok=True)
            else: write_text(path,change['content'])
        validation=validate_plugin(candidate)
        if not validation['valid']: raise ValueError('; '.join(validation['errors']))
        # Recheck after validation; roll back file replacements on an I/O error.
        for change in changes:
            path=inside(root,change['path'])
            if (sha(path) if path.is_file() else None)!=change.get('expected_sha256'):
                raise ValueError('Target changed during patch validation')
            backup[change['path']]=path.read_bytes() if path.exists() else None
        try:
            for change in changes:
                path=inside(root,change['path'])
                if change.get('delete'): path.unlink(missing_ok=True)
                else: write_text(path,change['content'])
        except OSError:
            for relative,raw in backup.items():
                path=inside(root,relative)
                if raw is None: path.unlink(missing_ok=True)
                else: path.write_bytes(raw)
            raise
        return {'status':'updated','changed':names,'validation':validation}
    finally:
        shutil.rmtree(parent)

def revise(source,spec,output,core_root,confirmed=False):
    source=Path(source).resolve(); output=Path(output).resolve()
    if output==source or output.is_relative_to(source):
        raise ValueError('Revision must be a separate candidate directory')
    baseline=read_json(source/'generation-lock.json')['files']
    build(spec,output,core_root,confirmed)
    conflicts=[]
    try:
        proposed={relative:sha(path) for path,relative in files(output)}
        for relative,original in baseline.items():
            if not inside(source,relative).exists() and relative in proposed:
                if proposed[relative]==original: inside(output,relative).unlink()
                else: conflicts.append(relative)
        for path,relative in files(source):
            if relative=='generation-lock.json': continue
            original=baseline.get(relative)
            if original is None:
                if relative in proposed and proposed[relative]!=sha(path): conflicts.append(relative)
                elif relative not in proposed:
                    target=inside(output,relative); target.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(path,target)
            elif sha(path)!=original:
                if proposed.get(relative)==original:
                    shutil.copy2(path,inside(output,relative))
                elif proposed.get(relative)!=sha(path): conflicts.append(relative)
        if conflicts: raise ValueError('User edits require a merged blueprint: '+', '.join(conflicts))
        validation=validate_plugin(output)
        if not validation['valid']: raise ValueError('; '.join(validation['errors']))
        write_json(output/'generation-lock.json',{'files':{relative:sha(path) for path,relative in files(output) if relative!='generation-lock.json'}})
        return {'status':'candidate','path':str(output),'validation':validation}
    except Exception:
        shutil.rmtree(output)
        raise
