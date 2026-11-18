import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'runtime'))
from harness_core.appserver import AppServer, envelope_schema

SERVER='''import json,sys
def emit(value): print(json.dumps(value),flush=True)
for line in sys.stdin:
 m=json.loads(line); method=m.get('method'); i=m.get('id'); p=m.get('params',{})
 if method=='initialize': emit({'id':i,'result':{'ok':True}})
 elif method=='thread/start': emit({'id':i,'result':{'thread':{'id':'thread-one','ephemeral':True}}})
 elif method=='turn/start':
  emit({'id':i,'result':{'turn':{'id':'turn-one','status':'inProgress'}}})
  emit({'method':'item/completed','params':{'threadId':'unrelated','turnId':'turn-one','item':{'type':'agentMessage','id':'wrong','text':'{"wrong":true}'}}})
  output={'status':'succeeded','result':{'value':7},'artifacts':[],'questions':[],'error':None}
  emit({'method':'item/completed','params':{'threadId':'thread-one','turnId':'turn-one','item':{'type':'agentMessage','id':'final','text':json.dumps(output)}}})
  emit({'method':'turn/completed','params':{'threadId':'thread-one','turn':{'id':'turn-one','status':'completed'}}})
 elif method=='turn/interrupt': emit({'id':i,'result':{}})
'''

class AppServerTests(unittest.TestCase):
    def test_item_events_supply_result_when_completion_omits_items(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); server=root/'fake_server.py'; server.write_text(SERVER)
            skill=root/'example/SKILL.md'; skill.parent.mkdir(); skill.write_text('test')
            client=AppServer([sys.executable,str(server)])
            try:
                output,thread=client.run(skill,{'inputs':{}},envelope_schema({'type':'object'}),root,timeout=3)
                self.assertEqual(output['result'],{'value':7}); self.assertEqual(thread,'thread-one')
            finally: client.close()

    def test_rejects_missing_or_false_ephemeral_confirmation(self):
        for confirmation in ({'id':'thread-one'}, {'id':'thread-one','ephemeral':False}):
            with self.subTest(confirmation=confirmation):
                client=AppServer()
                calls=[]
                client.start=lambda:None
                def request(method,params):
                    calls.append((method,params))
                    return {'thread':confirmation}
                client.request=request
                with tempfile.TemporaryDirectory() as directory:
                    with self.assertRaisesRegex(RuntimeError,'did not confirm an ephemeral'):
                        client.run(Path(directory)/'SKILL.md',{}, {},directory)
                self.assertEqual([method for method,_ in calls],['thread/start'])
                self.assertIs(calls[0][1]['ephemeral'],True)

    def test_prior_thread_id_never_resumes_a_saved_chat(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); server=root/'fake_server.py'; server.write_text(SERVER)
            skill=root/'example/SKILL.md'; skill.parent.mkdir(); skill.write_text('test')
            client=AppServer([sys.executable,str(server)])
            calls=[]; original_request=client.request
            def request(method,params,**kwargs):
                calls.append((method,params))
                return original_request(method,params,**kwargs)
            client.request=request
            try:
                output,thread=client.run(skill,{'inputs':{}},envelope_schema({'type':'object'}),root,
                                         timeout=3,thread_id='old-persistent-thread')
                self.assertEqual(output['result'],{'value':7})
                self.assertEqual(thread,'thread-one')
                self.assertNotIn('thread/resume',[method for method,_ in calls])
                starts=[params for method,params in calls if method=='thread/start']
                self.assertEqual(len(starts),1)
                self.assertIs(starts[0]['ephemeral'],True)
            finally: client.close()

if __name__=='__main__': unittest.main()
