from __future__ import annotations
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
from .common import read_json, write_json, sha, now, redact
from .packages import build, revise, patch, package, validate_plugin
from .engine import Engine
from .store import Store
from . import knowledge, sources

def parser():
    p=argparse.ArgumentParser(description='Build, maintain and run standalone Codex capability plugins.')
    commands=p.add_subparsers(dest='command',required=True)
    commands.add_parser('doctor')
    validate=commands.add_parser('validate'); validate.add_argument('--plugin',type=Path)
    for name in ('build','revise'):
        cmd=commands.add_parser(name); cmd.add_argument('--spec',type=Path,required=True)
        cmd.add_argument('--output',type=Path,required=True); cmd.add_argument('--confirmed',action='store_true')
        if name=='revise': cmd.add_argument('--source',type=Path,required=True)
    cmd=commands.add_parser('patch'); cmd.add_argument('--plugin',type=Path,required=True)
    cmd.add_argument('--plan',type=Path,required=True); cmd.add_argument('--confirmed',action='store_true')
    cmd=commands.add_parser('package'); cmd.add_argument('--plugin',type=Path)
    cmd.add_argument('--output',type=Path,required=True)
    for name in ('run','run-capability','resume','status','replay','cancel'):
        cmd=commands.add_parser(name); cmd.add_argument('--plugin',type=Path)
        cmd.add_argument('--workspace',type=Path,required=True)
        if name in {'run','run-capability'}:
            cmd.add_argument('--inputs',type=Path,required=True); cmd.add_argument('--confirmed',action='store_true')
            cmd.add_argument('--workflow' if name=='run' else '--capability',required=True)
        else: cmd.add_argument('--run-id',required=True)
        if name=='resume': cmd.add_argument('--answers',type=Path)
    cmd=commands.add_parser('discover'); cmd.add_argument('--query',required=True); cmd.add_argument('--limit',type=int,default=8)
    cmd=commands.add_parser('fetch-source'); cmd.add_argument('--repo',required=True)
    cmd.add_argument('--revision',required=True); cmd.add_argument('--output',type=Path,required=True)
    cmd=commands.add_parser('inspect-source'); cmd.add_argument('--source',type=Path,required=True)
    cmd.add_argument('--origin'); cmd.add_argument('--revision'); cmd.add_argument('--output',type=Path)
    cmd=commands.add_parser('absorb'); cmd.add_argument('--source',type=Path,required=True)
    cmd.add_argument('--plugin',type=Path,required=True); cmd.add_argument('--recipe',type=Path,required=True)
    cmd.add_argument('--confirmed',action='store_true')
    cmd=commands.add_parser('knowledge-ingest'); cmd.add_argument('--library',type=Path,required=True)
    cmd.add_argument('--source',type=Path,required=True); cmd.add_argument('--source-id'); cmd.add_argument('--origin')
    cmd=commands.add_parser('knowledge-publish'); cmd.add_argument('--library',type=Path,required=True)
    cmd.add_argument('--source-id',required=True); cmd.add_argument('--rules',type=Path,required=True)
    cmd.add_argument('--plugin',type=Path,required=True); cmd.add_argument('--capability',required=True)
    cmd.add_argument('--expected-source',required=True); cmd.add_argument('--expected-current')
    cmd.add_argument('--confirmed',action='store_true')
    cmd=commands.add_parser('knowledge-status'); cmd.add_argument('--library',type=Path,required=True)
    cmd.add_argument('--plugin',type=Path,required=True)
    return p

def execute(args,root):
    command=args.command
    plugin=getattr(args,'plugin',None) or root
    if command=='doctor':
        codex=shutil.which('codex')
        return {'python':sys.version.split()[0],'python_supported':sys.version_info>=(3,12),
                'codex':codex,'codex_version':subprocess.check_output([codex,'--version'],text=True).strip() if codex else None,
                'plugin':validate_plugin(root)}
    if command=='validate': return validate_plugin(plugin)
    if command=='build': return build(read_json(args.spec),args.output,root,args.confirmed)
    if command=='revise': return revise(args.source,read_json(args.spec),args.output,root,args.confirmed)
    if command=='patch': return patch(plugin,read_json(args.plan),args.confirmed)
    if command=='package': return package(plugin,args.output)
    if command in {'run','run-capability','resume','status','replay','cancel'}:
        database=args.workspace.resolve()/'.harness/runs.sqlite3'
        if command in {'status','replay','cancel'}:
            if not database.exists(): raise FileNotFoundError(database)
            store=Store(database)
            if command=='replay': return store.replay(args.run_id)
            if command=='cancel': return store.append(args.run_id,'status',{'status':'canceled'})
            return store.get(args.run_id)
        if command!='resume' and not args.confirmed: raise ValueError('Run requires the requested/confirmed task (--confirmed)')
        validation=validate_plugin(plugin)
        if not validation['valid']: raise ValueError('; '.join(validation['errors']))
        engine=Engine(plugin,args.workspace)
        if command=='resume':
            return engine.execute(args.run_id,read_json(args.answers) if args.answers else None)
        inputs=read_json(args.inputs)
        if command=='run-capability':
            if args.capability not in engine.capabilities: raise ValueError('Unknown capability')
            workflow={'id':args.capability,'max_concurrency':1,'nodes':[{'id':args.capability,
                'capability':args.capability,'depends_on':[],'idempotent':False,'retries':0,
                'bindings':{key:{'from':'inputs.'+key} for key in inputs}}]}
        else:
            workflow=next((item for item in engine.catalog.get('workflows',[]) if item['id']==args.workflow),None)
            if workflow is None: raise ValueError('Unknown workflow')
        run_id=engine.create(workflow,inputs)
        print(json.dumps({'run_id':run_id,'event':'created'}),file=sys.stderr,flush=True)
        return engine.execute(run_id)
    if command=='discover': return sources.discover(args.query,args.limit)
    if command=='fetch-source': return sources.fetch(args.repo,args.revision,args.output)
    if command=='inspect-source':
        result=sources.inspect(args.source,args.origin,args.revision)
        if args.output: write_json(args.output,result)
        return result
    if command=='absorb':
        recipe=read_json(args.recipe)
        plan=sources.absorption_plan(args.source,recipe)
        receipt_path=plugin/'sources.lock.json'
        receipts=read_json(receipt_path) if receipt_path.exists() else {'schema_version':'SourceReceiptsV1','sources':[]}
        receipts['sources'].append({key:value for key,value in recipe.items() if key!='selections'} | {
            'selected_files':[{key:value for key,value in item.items() if key!='content'} for item in recipe['selections']],
            'integrated_at':now()})
        plan['changes'].append({'path':'sources.lock.json','expected_sha256':sha(receipt_path) if receipt_path.exists() else None,
                               'content':json.dumps(receipts,ensure_ascii=False,indent=2)+'\n'})
        return patch(plugin,plan,args.confirmed)
    if command=='knowledge-ingest': return knowledge.ingest(args.library,args.source,args.source_id,args.origin)
    if command=='knowledge-publish':
        return knowledge.publish(args.library,args.source_id,args.rules,plugin,args.capability,
                                 args.expected_source,args.confirmed,args.expected_current)
    if command=='knowledge-status': return knowledge.status(args.library,plugin)
    raise ValueError(command)

def main(root):
    args=parser().parse_args()
    try:
        result=execute(args,Path(root).resolve())
        print(json.dumps(result,ensure_ascii=False,indent=2))
        if result.get('valid') is False or result.get('status')=='failed': return 1
        if result.get('status')=='awaiting_input': return 3
        return 0
    except (ValueError,KeyError,OSError,StopIteration,subprocess.SubprocessError) as exc:
        print(json.dumps({'status':'error','error':redact(exc)},ensure_ascii=False),file=sys.stderr)
        return 2
