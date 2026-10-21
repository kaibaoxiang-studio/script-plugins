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
 elif method=='thread/start': emit({'id':i,'result':{'thread':{'id':'thread-one'}}})
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

if __name__=='__main__': unittest.main()
