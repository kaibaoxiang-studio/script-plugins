"""Exercise host-default boundaries without opening a real dispatcher chat."""
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'runtime'))
from harness_core.cli import parser
from harness_core.engine import Engine, Executor, HostDelegationRequired
from harness_core.packages import build, validate_plugin
from test_harness import specification, node, result


def agent_specification():
    spec=specification()
    spec['capabilities'][0]['execution']={'kind':'agent'}
    spec['capabilities'][0]['required_artifacts']=[]
    spec['capabilities'][0]['instructions']=(
        'Use the supplied character evidence to design concrete facial and hairstyle details, '
        'preserving approved identity constraints. Return the actual design to the parent.')
    return spec


class HostExecutionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name)
        self.plugin=self.base/'plugin'
        build(agent_specification(),self.plugin,ROOT,True)

    def test_default_agent_execution_does_not_start_appserver_or_retry(self):
        with patch('harness_core.engine.AppServer') as appserver:
            engine=Engine(self.plugin,self.base/'work')
            run=engine.create({'nodes':[node('design')]},{'text':'A reserved artist'})
            state=engine.execute(run)
        appserver.assert_not_called()
        self.assertEqual(state['status'],'failed')
        failed=state['nodes']['design']
        self.assertEqual(failed['status'],'failed')
        self.assertEqual(failed['attempt'],1)
        self.assertIn('not executed',failed['error'])
        self.assertNotIn('output',failed)

    def test_explicit_appserver_opt_in_uses_compatibility_executor(self):
        with patch('harness_core.engine.AppServer') as appserver:
            appserver.return_value.run.return_value=(result(7),'ephemeral-thread')
            engine=Engine(self.plugin,self.base/'work',agent_backend='appserver')
            run=engine.create({'nodes':[node('design')]},{'text':'A reserved artist'})
            state=engine.execute(run)
        appserver.assert_called_once_with()
        appserver.return_value.start.assert_called_once_with()
        appserver.return_value.run.assert_called_once()
        appserver.return_value.close.assert_called_once_with()
        self.assertEqual(state['status'],'completed')
        self.assertEqual(state['nodes']['design']['output']['result'],{'characters':7})

    def test_injected_executor_preserves_old_python_callback_contract(self):
        class InjectedExecutor:
            def __bool__(self): return False
            def __call__(self,capability,task,node,canceled,thread_id,on_thread):
                return result(len(task['inputs']['text'])),None
        injected=InjectedExecutor()
        with patch('harness_core.engine.AppServer') as appserver:
            engine=Engine(self.plugin,self.base/'work',executor=injected)
            self.assertIs(engine.executor,injected)
            run=engine.create({'nodes':[node('design')]},{'text':'original callback'})
            state=engine.execute(run)
        appserver.assert_not_called()
        self.assertEqual(state['status'],'completed')
        self.assertEqual(state['nodes']['design']['output']['result'],{'characters':17})

    def test_cli_defaults_host_and_requires_explicit_compatibility_flag(self):
        for command in ('run','run-capability','resume'):
            argv=[command,'--workspace','/tmp/harness-test']
            if command=='resume': argv+=['--run-id','existing-run']
            else:
                argv+=['--inputs','inputs.json','--confirmed']
                argv+=['--workflow','example'] if command=='run' else ['--capability','counter']
            self.assertEqual(parser().parse_args(argv).agent_backend,'host')
            self.assertEqual(parser().parse_args(argv+['--agent-backend','appserver']).agent_backend,'appserver')

    def test_generated_agent_package_contains_resolvable_host_instructions(self):
        self.assertTrue(validate_plugin(self.plugin)['valid'])
        guide=self.plugin/'HOST_EXECUTION.md'
        self.assertEqual(guide.read_bytes(),(ROOT/'HOST_EXECUTION.md').read_bytes())
        for path in (self.plugin/'skills/count-text/SKILL.md',
                     self.plugin/'skills/counter-plugin/SKILL.md'):
            text=path.read_text()
            self.assertIn('native subagent',text)
            self.assertIn('HOST_EXECUTION.md',text)
            self.assertIn('ordinary',text)


if __name__=='__main__': unittest.main()
