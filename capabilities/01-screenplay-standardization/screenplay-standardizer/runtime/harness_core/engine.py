from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time
import uuid

from .appserver import AppServer, envelope_schema
from .common import inside, fingerprint, sha, read_json, write_json, now, redact
from .contracts import graph_order, bind_inputs, validate_data
from .store import Store

def input_files(value):
    found={}
    def visit(item):
        if isinstance(item,dict):
            for child in item.values(): visit(child)
        elif isinstance(item,list):
            for child in item: visit(child)
        elif isinstance(item,str) and len(item)<4096:
            try:
                path=Path(item)
                if path.is_absolute() and path.is_file(): found[str(path.resolve())]=sha(path)
            except OSError: pass
    visit(value)
    return found

def verify_result(result, capability, artifact_dir):
    validate_data(result,envelope_schema(capability['output_schema']))
    artifacts=[]
    if result['status']=='succeeded':
        validate_data(result['result'],capability['output_schema'])
        for relative in result['artifacts']:
            path=inside(artifact_dir,relative)
            if not path.is_file() or path.is_symlink():
                raise ValueError(f'Missing or invalid artifact: {relative}')
            artifacts.append({'path':str(path.resolve()),'sha256':sha(path)})
        for required in capability.get('required_artifacts',[]):
            if required not in result['artifacts']:
                raise ValueError(f'Required artifact not declared: {required}')
    return artifacts

class Executor:
    def __init__(self, root):
        self.root=Path(root).resolve()
        self.client=None
        self.client_lock=threading.Lock()

    def __call__(self, capability, task, node, canceled, thread_id, on_thread):
        directory=Path(task['artifact_dir'])
        directory.mkdir(parents=True,exist_ok=True)
        validate_data(task['inputs'],capability['input_schema'])
        execution=capability['execution']
        timeout=node.get('timeout_seconds',600)
        if execution['kind']=='agent':
            with self.client_lock:
                if self.client is None:
                    self.client=AppServer()
                    self.client.start()
            return self.client.run(inside(self.root,f'skills/{capability["skill_name"]}/SKILL.md'),
                task,envelope_schema(capability['output_schema']),directory,
                writable=execution.get('access','read-only')=='workspace-write',
                network=execution.get('network',False),timeout=timeout,cancel=canceled,
                thread_id=thread_id,on_thread=on_thread)
        write_json(directory/'input.json',task)
        result_path=directory/'result.json'
        result_path.unlink(missing_ok=True)
        script=inside(self.root,execution['script'])
        env={**os.environ,'PYTHONPATH':str(self.root/'runtime')}
        with (directory/'stdout.log').open('w') as stdout, (directory/'stderr.log').open('w') as stderr:
            process=subprocess.Popen([sys.executable,str(script),'--input',str(directory/'input.json'),
                                      '--output',str(result_path)],cwd=directory,env=env,
                                     stdout=stdout,stderr=stderr,start_new_session=os.name!='nt')
            deadline=time.monotonic()+timeout
            try:
                while process.poll() is None:
                    if canceled.is_set(): raise InterruptedError('Task canceled')
                    if time.monotonic()>=deadline: raise TimeoutError('Python node timed out')
                    time.sleep(0.05)
                if process.returncode:
                    raise RuntimeError(f'Python node exited {process.returncode}; see {directory / "stderr.log"}')
                if not result_path.is_file(): raise ValueError('Python node did not write result.json')
                return read_json(result_path),None
            finally:
                if process.poll() is None:
                    if os.name=='nt': process.kill()
                    else: os.killpg(process.pid,signal.SIGKILL)
                    process.wait()

    def close(self):
        if self.client: self.client.close()

class Engine:
    def __init__(self, root, workspace, executor=None):
        self.root=Path(root).resolve()
        self.workspace=Path(workspace).resolve()
        self.catalog=read_json(self.root/'capabilities.json')
        self.capabilities={item['id']:item for item in self.catalog['capabilities']}
        self.store=Store(self.workspace/'.harness/runs.sqlite3')
        self.executor=executor or Executor(self.root)

    def create(self,workflow,inputs):
        graph_order(workflow,self.capabilities)
        run_id='run-'+uuid.uuid4().hex[:16]
        self.store.append(run_id,'created',{'run_id':run_id,'graph':workflow,'inputs':inputs,
            'plugin_hash':fingerprint(self.root),'input_files':input_files(inputs),'created_at':now()})
        return run_id

    def execute(self,run_id,answers=None):
        base=self.workspace/'.harness'/run_id
        base.mkdir(parents=True,exist_ok=True)
        lock=base/'scheduler.lock'
        if lock.exists():
            try:
                os.kill(int(lock.read_text()),0)
            except ProcessLookupError:
                lock.unlink()
            else:
                raise RuntimeError('A scheduler already owns this run')
        fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
        os.write(fd,str(os.getpid()).encode()); os.close(fd)
        try:
            return self._execute(run_id,base,answers)
        finally:
            lock.unlink(missing_ok=True)
            close=getattr(self.executor,'close',None)
            if close: close()

    def _execute(self,run_id,base,answers):
        state=self.store.get(run_id)
        if state['status']=='canceled': raise ValueError('Canceled runs are immutable; create a new run')
        if fingerprint(self.root)!=state['plugin_hash']:
            raise ValueError('Plugin changed; create a new run with current capabilities')
        if input_files(state['inputs'])!=state['input_files']:
            raise ValueError('Input files changed; create a new run')
        graph=state['graph']
        order=graph_order(graph,self.capabilities)
        nodes={node['id']:node for node in graph['nodes']}
        for node_id,prior in list(state['nodes'].items()):
            if prior['status']=='succeeded':
                recorded=verify_result(prior['output'],self.capabilities[nodes[node_id]['capability']],
                                       base/node_id/f'attempt-{prior["attempt"]}')
                if recorded!=prior.get('artifacts',[]):
                    raise ValueError('Completed artifact changed; create a new run')
            if prior['status']=='running':
                can_retry=nodes[node_id].get('idempotent',False) and prior['attempt']<=nodes[node_id].get('retries',1)
                self.store.append(run_id,'node',{**prior,'status':'retry' if can_retry else 'failed',
                                                'error':'Previous scheduler interrupted'})
        if answers: self.store.append(run_id,'answers',answers)
        resumable = {key for key,value in self.store.get(run_id)['nodes'].items()
                     if value['status']=='blocked'} if answers else set()
        self.store.append(run_id,'status',{'status':'running'})
        cap=min(3,max(1,graph.get('max_concurrency',3)))
        canceled=threading.Event()
        futures={}
        with ThreadPoolExecutor(max_workers=cap) as pool:
            while True:
                state=self.store.get(run_id)
                if state['status']=='canceled':
                    canceled.set()
                    for future in futures: future.cancel()
                    break
                completed={key:value for key,value in state['nodes'].items() if value['status']=='succeeded'}
                if len(completed)==len(nodes):
                    self.store.append(run_id,'status',{'status':'completed'})
                    break
                active={value[0] for value in futures.values()}
                ready=[]
                for node_id in order:
                    prior=state['nodes'].get(node_id,{})
                    if node_id in active or node_id in completed: continue
                    if prior.get('status') in {'failed','blocked'}:
                        if not (prior['status']=='blocked' and node_id in resumable): continue
                    if all(dep in completed for dep in nodes[node_id].get('depends_on',[])):
                        ready.append(node_id)
                for node_id in ready[:cap-len(futures)]:
                    node=nodes[node_id]
                    prior=state['nodes'].get(node_id,{})
                    attempt=prior.get('attempt',0)+(0 if prior.get('status')=='blocked' else 1)
                    attempt=max(1,attempt)
                    directory=base/node_id/f'attempt-{attempt}'
                    try:
                        inputs=bind_inputs(node,state['inputs'],{key:value['output']['result'] for key,value in completed.items()})
                    except (ValueError, KeyError, TypeError) as exc:
                        self.store.append(run_id,'node',{'id':node_id,'status':'failed','attempt':attempt,
                            'error':redact(exc),'finished_at':now()})
                        continue
                    resumable.discard(node_id)
                    task={'task_id':f'{run_id}:{node_id}:{attempt}','objective':node.get('objective',''),
                          'inputs':inputs,'answers':state.get('answers',{}),'artifact_dir':str(directory)}
                    record={'id':node_id,'status':'running','attempt':attempt,
                            'thread_id':prior.get('thread_id'),'started_at':now()}
                    self.store.append(run_id,'node',record)
                    def remember(thread_id,record=record):
                        self.store.append(run_id,'node',{**record,'thread_id':thread_id})
                    future=pool.submit(self.executor,self.capabilities[node['capability']],task,node,canceled,
                                       prior.get('thread_id'),remember)
                    futures[future]=(node_id,attempt,directory)
                if not futures:
                    blocked=[value for value in state['nodes'].values() if value['status']=='blocked']
                    status='awaiting_input' if blocked else 'failed'
                    questions=[q for value in blocked for q in value.get('output',{}).get('questions',[])]
                    self.store.append(run_id,'status',{'status':status,'questions':list(dict.fromkeys(questions))})
                    break
                done,_=wait(futures,timeout=0.2,return_when=FIRST_COMPLETED)
                for future in done:
                    node_id,attempt,directory=futures.pop(future)
                    if self.store.get(run_id)['status']=='canceled': continue
                    prior=self.store.get(run_id)['nodes'][node_id]
                    try:
                        output,thread_id=future.result()
                        artifacts=verify_result(output,self.capabilities[nodes[node_id]['capability']],directory)
                        status=output['status']
                        if status=='failed': raise ValueError(output.get('error') or 'Node returned failed')
                        self.store.append(run_id,'node',{**prior,'status':status,'output':output,
                            'thread_id':thread_id,'artifacts':artifacts,'finished_at':now()})
                    except Exception as exc:
                        node=nodes[node_id]
                        retry=node.get('idempotent',False) and attempt<=node.get('retries',1)
                        self.store.append(run_id,'node',{**prior,'status':'retry' if retry else 'failed',
                            'error':redact(exc),'finished_at':now()})
        result=self.store.get(run_id)
        write_json(base/'run-report.json',result)
        return result
