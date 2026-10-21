from __future__ import annotations
from copy import deepcopy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'runtime'))
from harness_core.common import sha, read_json, write_json
from harness_core.packages import build, patch, revise, package, validate_plugin
from harness_core.contracts import graph_order, validate_data
from harness_core.engine import Engine, verify_result
from harness_core.store import Store
from harness_core import knowledge,sources

SCRIPT='''import argparse,json
from pathlib import Path
p=argparse.ArgumentParser(); p.add_argument('--input'); p.add_argument('--output'); a=p.parse_args()
task=json.loads(Path(a.input).read_text()); text=task['inputs']['text']
result={'characters':len(text)}
Path(task['artifact_dir'],'count.json').write_text(json.dumps(result))
Path(a.output).write_text(json.dumps({'status':'succeeded','result':result,'artifacts':['count.json'],'questions':[],'error':None}))
'''

def specification():
    return {'schema_version':'HarnessBlueprintV1',
      'plugin':{'name':'counter-plugin','version':'0.1.0','description':'Count supplied Unicode text','author':{'name':'Test'}},
      'goal':'Provide reusable text counting','acceptance_criteria':['Counts actual inputs'], 'open_questions':[],
      'capabilities':[{'id':'counter','skill_name':'count-text','description':'Count supplied text',
         'instructions':'Read the supplied text and count all Unicode characters, including whitespace. Use the bundled runtime to invoke the Python capability, write count.json, and report its actual value and path.',
         'input_schema':{'type':'object','properties':{'text':{'type':'string'}},'required':['text'],'additionalProperties':False},
         'output_schema':{'type':'object','properties':{'characters':{'type':'integer'}},'required':['characters'],'additionalProperties':False},
         'execution':{'kind':'python','script':'scripts/count.py'},'required_artifacts':['count.json'],'knowledge_refs':[]}],
      'files':{'scripts/count.py':SCRIPT,'references/method.md':'Count Unicode code points with Python len; preserve whitespace.'},
      'sources':[],'workflows':[]}

def node(name,depends=None):
    return {'id':name,'capability':'counter','depends_on':depends or [],'bindings':{'text':{'from':'inputs.text'}},
            'idempotent':True,'retries':1,'timeout_seconds':5}

def result(value=1,status='succeeded'):
    return {'status':status,'result':{'characters':value} if status=='succeeded' else None,
            'artifacts':[],'questions':['Which value?'] if status=='blocked' else [],'error':None}

class HarnessTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name); self.plugin=self.base/'plugin'
        build(specification(),self.plugin,ROOT,True)

    def fake(self,callback=None):
        capabilities=read_json(self.plugin/'capabilities.json')
        capabilities['capabilities'][0]['required_artifacts']=[]
        write_json(self.plugin/'capabilities.json',capabilities)
        return callback or (lambda cap,task,node,cancel,thread,remember:(result(len(task['inputs']['text'])),None))

    def test_self_contained_package_runs_real_python(self):
        engine=Engine(self.plugin,self.base/'work')
        run=engine.create({'nodes':[node('count')]},{'text':'剧本 a'})
        output=engine.execute(run)
        self.assertEqual(output['status'],'completed')
        self.assertEqual(output['nodes']['count']['output']['result']['characters'],4)
        path=Path(output['nodes']['count']['artifacts'][0]['path'])
        self.assertEqual(read_json(path),{'characters':4})

    def test_generated_launcher_and_zip_are_portable(self):
        archive=self.base/'plugin.zip'; package(self.plugin,archive)
        relocated=self.base/'relocated'
        with zipfile.ZipFile(archive) as z:
            self.assertFalse(any('/.venv/' in name or '/.harness/' in name for name in z.namelist()))
            z.extractall(relocated)
        relocated_plugin=relocated/'plugin'
        process=subprocess.run([sys.executable,str(relocated_plugin/'harness.py'),'validate'],capture_output=True,text=True,cwd=self.base)
        self.assertEqual(process.returncode,0,process.stderr)
        self.assertTrue(json.loads(process.stdout)['valid'])
        self.assertTrue((relocated_plugin/'generation-lock.json').is_file())

    def test_build_refuses_overwrite_and_unconfirmed(self):
        with self.assertRaises(FileExistsError): build(specification(),self.plugin,ROOT,True)
        with self.assertRaises(ValueError): build(specification(),self.base/'other',ROOT)

    def test_blueprint_rejects_missing_script_and_path_escape(self):
        spec=specification(); spec['files']={'../escaped.py':'bad'}
        with self.assertRaises(ValueError): build(spec,self.base/'bad',ROOT,True)
        self.assertFalse((self.base/'escaped.py').exists())
        spec=specification(); spec['files'].pop('scripts/count.py')
        with self.assertRaises(ValueError): build(spec,self.base/'bad-script',ROOT,True)

    def test_reference_and_python_validation(self):
        path=self.plugin/'skills/count-text/SKILL.md'
        path.write_text(path.read_text()+'\n[Missing](references/missing.md)\n')
        self.assertFalse(validate_plugin(self.plugin)['valid'])

    def test_dag_rejects_cycle_and_undeclared_binding(self):
        capabilities={'counter':{}}
        with self.assertRaises(ValueError): graph_order({'nodes':[node('a',['b']),node('b',['a'])]},capabilities)
        bad=node('a'); bad['bindings']={'text':{'from':'b.value'}}
        with self.assertRaises(ValueError): graph_order({'nodes':[bad,node('b')]},capabilities)

    def test_schema_checks_types_and_refuses_remote_refs(self):
        with self.assertRaises(ValueError): validate_data({'characters':'four'},specification()['capabilities'][0]['output_schema'])
        with self.assertRaises(ValueError): validate_data({}, {'$ref':'https://example.org/schema'})

    def test_parallel_topology_and_bound_results(self):
        active=peak=0; lock=threading.Lock(); finished=[]
        def execute(cap,task,definition,cancel,thread,remember):
            nonlocal active,peak
            with lock: active+=1; peak=max(active,peak)
            time.sleep(.07)
            with lock: active-=1; finished.append(definition['id'])
            return result(),None
        engine=Engine(self.plugin,self.base/'work',self.fake(execute))
        downstream=node('c',['a','b']); downstream['bindings']={'text':{'from':'inputs.text'}}
        run=engine.create({'nodes':[node('a'),node('b'),downstream]},{'text':'x'})
        self.assertEqual(engine.execute(run)['status'],'completed')
        self.assertGreaterEqual(peak,2); self.assertEqual(finished[-1],'c')

    def test_retry_invalid_outputs_and_non_idempotent_failure(self):
        calls=[]
        def execute(cap,task,definition,cancel,thread,remember):
            calls.append(task['task_id'])
            return ({'status':'succeeded','result':{'characters':'invalid'},'artifacts':[],'questions':[],'error':None} if len(calls)==1 else result()),None
        engine=Engine(self.plugin,self.base/'work',self.fake(execute))
        run=engine.create({'nodes':[node('count')]},{'text':'x'})
        state=engine.execute(run)
        self.assertEqual(state['status'],'completed'); self.assertEqual(state['nodes']['count']['attempt'],2)
        bad=node('bad'); bad.update(idempotent=False,retries=0)
        def fail(*args): raise RuntimeError('expected failure')
        engine.executor=fail
        second=engine.create({'nodes':[bad]},{'text':'x'})
        self.assertEqual(engine.execute(second)['nodes']['bad']['attempt'],1)

    def test_blocked_answers_resume_same_task(self):
        def execute(cap,task,*args): return (result(3) if task['answers'] else result(status='blocked')),None
        engine=Engine(self.plugin,self.base/'work',self.fake(execute))
        run=engine.create({'nodes':[node('count')]},{'text':'x'})
        self.assertEqual(engine.execute(run)['status'],'awaiting_input')
        state=engine.execute(run,{'value':'3'})
        self.assertEqual(state['status'],'completed'); self.assertEqual(state['nodes']['count']['attempt'],1)

    def test_blocked_answers_resume_all_nodes_across_worker_waves(self):
        def execute(cap,task,*args): return (result(3) if task['answers'] else result(status='blocked')),None
        engine=Engine(self.plugin,self.base/'work',self.fake(execute))
        run=engine.create({'max_concurrency':1,'nodes':[node('first'),node('second')]},{'text':'x'})
        self.assertEqual(engine.execute(run)['status'],'awaiting_input')
        self.assertEqual(engine.execute(run,{'value':'3'})['status'],'completed')

    def test_unresolved_binding_produces_failed_report(self):
        engine=Engine(self.plugin,self.base/'work',self.fake())
        run=engine.create({'nodes':[node('count')]},{'other':'missing text'})
        state=engine.execute(run)
        self.assertEqual(state['status'],'failed')
        self.assertIn('Unresolved input binding',state['nodes']['count']['error'])
        self.assertTrue((self.base/'work/.harness'/run/'run-report.json').is_file())

    def test_recovery_replay_and_changed_package(self):
        engine=Engine(self.plugin,self.base/'work',self.fake())
        run=engine.create({'nodes':[node('count')]},{'text':'x'})
        engine.store.append(run,'node',{'id':'count','status':'running','attempt':1})
        state=engine.execute(run)
        self.assertEqual(state['nodes']['count']['attempt'],2)
        self.assertEqual(state,engine.store.replay(run))
        (self.plugin/'references/method.md').write_text('changed')
        with self.assertRaisesRegex(ValueError,'Plugin changed'): engine.execute(run)

    def test_changed_input_and_completed_artifact_rejected(self):
        source=self.base/'source.txt'; source.write_text('one')
        engine=Engine(self.plugin,self.base/'work',self.fake())
        run=engine.create({'nodes':[node('count')]},{'text':'x','source':str(source)})
        source.write_text('two')
        with self.assertRaisesRegex(ValueError,'Input files changed'): engine.execute(run)
        engine=Engine(self.plugin,self.base/'real')
        second=engine.create({'nodes':[node('real')]},{'text':'x'})
        state=engine.execute(second)
        Path(state['nodes']['real']['artifacts'][0]['path']).write_text('tampered')
        with self.assertRaisesRegex(ValueError,'artifact changed'): engine.execute(second)

    def test_artifact_traversal_and_missing_required_file(self):
        with self.assertRaises(ValueError): verify_result(result(),specification()['capabilities'][0],self.base)
        escaped=result(); escaped['artifacts']=['../outside']
        with self.assertRaises(ValueError): verify_result(escaped,specification()['capabilities'][0],self.base)

    def test_cancel_terminates_python_node(self):
        path=self.plugin/'scripts/count.py'
        path.write_text('import time\ntime.sleep(20)\n'+SCRIPT)
        engine=Engine(self.plugin,self.base/'work')
        run=engine.create({'nodes':[node('sleep')]},{'text':'x'})
        error=[]
        def invoke():
            try: engine.execute(run)
            except Exception as exc: error.append(exc)
        thread=threading.Thread(target=invoke); thread.start()
        deadline=time.monotonic()+3
        while time.monotonic()<deadline:
            if engine.store.get(run)['nodes']: break
            time.sleep(.02)
        engine.store.append(run,'status',{'status':'canceled'})
        thread.join(3)
        self.assertFalse(thread.is_alive()); self.assertEqual(error,[])
        self.assertEqual(engine.store.get(run)['status'],'canceled')

    def test_patch_conflict_and_failed_candidate_preserve_original(self):
        path=self.plugin/'references/method.md'; original=path.read_text()
        with self.assertRaises(ValueError): patch(self.plugin,{'changes':[{'path':'references/method.md','expected_sha256':'wrong','content':'bad'}]},True)
        self.assertEqual(path.read_text(),original)
        script=self.plugin/'scripts/count.py'; before=script.read_text()
        with self.assertRaises(ValueError): patch(self.plugin,{'changes':[{'path':'scripts/count.py','expected_sha256':sha(script),'content':'invalid python ('}]},True)
        self.assertEqual(script.read_text(),before)

    def test_revision_preserves_user_edits_and_detects_conflicts(self):
        path=self.plugin/'references/method.md'; path.write_text('User maintained rule')
        spec=specification(); spec['plugin']['version']='0.2.0'
        candidate=self.base/'v2'; revise(self.plugin,spec,candidate,ROOT,True)
        self.assertEqual((candidate/'references/method.md').read_text(),'User maintained rule')
        spec['files']['references/method.md']='Both changed'
        with self.assertRaisesRegex(ValueError,'User edits'): revise(self.plugin,spec,self.base/'conflict',ROOT,True)
        self.assertFalse((self.base/'conflict').exists())

    def test_source_absorption_uses_reviewed_hash_and_preserves_license(self):
        source=self.base/'upstream'; source.mkdir()
        (source/'LICENSE').write_text('MIT test license'); (source/'method.md').write_text('Reviewed method')
        report=sources.inspect(source,origin='https://github.com/example/source',revision='a'*40)
        self.assertEqual(report['status'],'inspection_only')
        recipe={'origin':report['origin'],'revision':report['revision'],'license':'MIT','adaptation':'Scoped text method',
            'selections':[{'source':'method.md','source_sha256':sha(source/'method.md'),'target':'references/adapted.md',
                'mode':'adapt','content':'Adapted concrete method for target capability.','expected_target_sha256':None}],
            'license_files':[{'source':'LICENSE','source_sha256':sha(source/'LICENSE'),'target':'licenses/source.txt'}]}
        patch(self.plugin,sources.absorption_plan(source,recipe),True)
        self.assertTrue((self.plugin/'licenses/source.txt').is_file())
        (source/'method.md').write_text('changed after review')
        with self.assertRaises(ValueError): sources.absorption_plan(source,recipe)

    def test_symlink_source_rejected(self):
        source=self.base/'external'; source.mkdir(); (source/'escape').symlink_to(self.plugin)
        with self.assertRaises(ValueError): sources.inspect(source)

    def test_complete_harness_source_is_adapted_to_portable_interface(self):
        source=self.base/'legacy-harness'; (source/'skills/legacy').mkdir(parents=True)
        (source/'LICENSE').write_text('MIT license retained for this fixture')
        (source/'runner.py').write_text('def count(text):\n    return len(text)\n')
        (source/'skills/legacy/SKILL.md').write_text('Legacy entry, depends on runner.py')
        report=sources.inspect(source,origin='fixture:complete-harness',revision='v1')
        self.assertIn('runner.py',[entry['path'] for entry in report['files']])
        recipe={'origin':'fixture:complete-harness','revision':'v1','license':'MIT',
            'adaptation':'Extract counting rule; replace legacy entry and global state with node envelope.',
            'license_files':[{'source':'LICENSE','source_sha256':sha(source/'LICENSE'),'target':'licenses/legacy-MIT.txt'}],
            'selections':[{'source':'runner.py','source_sha256':sha(source/'runner.py'),
                'mode':'adapt','target':'scripts/count.py','content':SCRIPT,'expected_target_sha256':sha(self.plugin/'scripts/count.py')}]}
        patch(self.plugin,sources.absorption_plan(source,recipe),True)
        engine=Engine(self.plugin,self.base/'work')
        run=engine.create({'nodes':[node('count')]},{'text':'converted Harness'})
        self.assertEqual(engine.execute(run)['nodes']['count']['output']['result']['characters'],17)

    def test_creator_self_upgrade_uses_separate_validated_candidate(self):
        candidate=self.base/'creator-candidate'
        shutil.copytree(ROOT,candidate,ignore=shutil.ignore_patterns('.venv','.harness','.git','__pycache__','dist'))
        current=sha(ROOT/'README.md')
        text=(candidate/'README.md').read_text()+'\nCandidate upgrade verification.\n'
        patch(candidate,{'changes':[{'path':'README.md','expected_sha256':sha(candidate/'README.md'),'content':text}]},True)
        self.assertTrue(validate_plugin(candidate)['valid'])
        self.assertEqual(sha(ROOT/'README.md'),current)
        self.assertIn('Candidate upgrade verification.',(candidate/'README.md').read_text())

    def test_knowledge_point_update_and_source_revision(self):
        library=self.base/'library'; source=self.base/'facts.md'; source.write_text('Source evidence with facts about counting characters and whitespace.')
        ingest=knowledge.ingest(library,source,'count-rules',origin='https://example.org/count')
        rules=self.base/'rules.md'; rules.write_text('# Counting\n\nCount Unicode code points with len. Preserve all whitespace. Evidence: source paragraph 1.')
        untouched=sha(self.plugin/'scripts/count.py')
        knowledge.publish(library,'count-rules',rules,self.plugin,'counter',ingest['sha256'],True)
        state=knowledge.status(library,self.plugin)
        self.assertFalse(state['snapshots'][0]['source_newer'])
        self.assertEqual(untouched,sha(self.plugin/'scripts/count.py'))
        self.assertIn('references/knowledge/counter/count-rules.md',read_json(self.plugin/'capabilities.json')['capabilities'][0]['knowledge_refs'])
        source.write_text('New source revision changed the counting method.')
        knowledge.ingest(library,source,'count-rules',origin='https://example.org/count')
        self.assertTrue(knowledge.status(library,self.plugin)['snapshots'][0]['source_newer'])
        with self.assertRaises(ValueError): knowledge.publish(library,'count-rules',rules,self.plugin,'counter',ingest['sha256'],True)

if __name__=='__main__': unittest.main()
