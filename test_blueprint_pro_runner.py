"""Paid runner control/evidence tests with fake inference and real local MCP; never loads a key or calls an API."""
import asyncio,json,tempfile
from pathlib import Path
from uuid import uuid4
import pytest
from dev import run_blueprint_pro_check as runner

ROOT=Path(__file__).resolve().parent

def call(name,args):return {'role':'assistant','content':'','tool_calls':[{'id':str(uuid4()),'type':'function','function':{'name':name,'arguments':json.dumps(args)}}]}
def answer(text):return {'role':'assistant','content':text+' 0.71.44 '+runner.URL}

@pytest.mark.parametrize('case',['passing','production_passing','no_tools','changed_source'])
def test_runner_evidence_and_cleanup_without_paid_inference(monkeypatch,case):
    replies=[call('search_blueprint_examples',{'request':{'query':'warehouse aisle','game_version':'0.71.44'}}),
      call('get_blueprint_example',{'request':{'example_id':runner.ID,'game_version':'0.71.44'}}),answer('Original teaching sketch'),
      call('get_blueprint_example',{'request':{'example_id':runner.ID,'game_version':'0.72.0'}}),answer('Compatibility is unknown for 0.72.0')]
    if case=='no_tools':replies=[answer('No evidence'),answer('Unknown compatibility')]
    if case=='production_passing':
        for reply in replies:
            if reply['content']:reply['content']+=' '+runner.load_registry().citation()['artifacts'][0]['url']
    instances=[]
    class FakePro:
        def __init__(self,key,model):
            assert key=='test-only-secret' and model=='deepseek-v4-pro';self.closed=False;instances.append(self)
        async def complete(self,messages,tools,on_text):
            assert len(tools)==21
            value=replies.pop(0);on_text(value.get('content',''));return value
        async def close(self):self.closed=True
    monkeypatch.setattr(runner,'DeepSeek',FakePro)
    hashes={n:runner.sha(ROOT/n) for n in runner.SOURCES}
    if case=='changed_source':hashes['dev/run_blueprint_pro_check.py']='0'*64
    monkeypatch.setattr(runner,'SOURCE_HASHES',hashes,raising=False)
    with tempfile.TemporaryDirectory(dir=ROOT/'runtime',prefix='blueprint-pro-fake-') as name:
        if case not in {'passing','production_passing'}:
            with pytest.raises(AssertionError):asyncio.run(runner.run(Path(name),'test-only-secret'))
        else:
            report=asyncio.run(runner.run(Path(name),'test-only-secret',production=case=='production_passing'))
            assert report['passed'] and report['completed_turns']==2
            assert report['started_requests']==report['completed_round_trips']==5
            assert report['actual_reference_tool_calls']==3 and report['get_results_checked']==2
            assert report['fixture']['demo'] is True and report['fixture']['game_version']=='DEMO-unverified'
            assert 'test-only-secret' not in json.dumps(report)
            assert report['production_backend_only'] is (case=='production_passing')
        assert len(instances)==2 and all(p.closed for p in instances)
