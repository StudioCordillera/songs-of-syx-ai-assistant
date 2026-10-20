"""Paid-check plumbing on real stdio MCP, fake provider and throwaway key only."""
import asyncio
import json
from pathlib import Path
import pytest
from mcp import ClientSession
from mcp.client.stdio import stdio_client
from syx_deepseek import ProviderError
from dev.chat_target_transport import McpTargetDrafts
import dev.verify_target_dispatch_pro as check
from test_chat_target_transport import transport_state, parameters, create


@pytest.mark.parametrize('fail',[False,True])
def test_paid_check_is_explicit_and_records_exact_handoff_without_offline_network(transport_state,tmp_path,monkeypatch,fail):
    path,_=transport_state
    keyfile=tmp_path/'test.env';keyfile.write_text('DEEPSEEK_API_KEY=offline-plumbing-key\n');keyfile.chmod(0o600)
    class FakePro:
        attempts=0
        closed=0
        def __init__(self,key,model):
            assert key=='offline-plumbing-key';assert model=='deepseek-v4-pro';self.model=model
        async def complete(self,messages,tools,on_text):
            FakePro.attempts+=1
            if fail:raise ProviderError('Explicit test failure; no retry')
            on_text('Offline test answer')
            return {'role':'assistant','content':'Offline test answer'}
        async def close(self):FakePro.closed+=1
    monkeypatch.setattr(check,'DeepSeek',FakePro)
    async def run():
        async with stdio_client(parameters(path)) as streams:
            async with ClientSession(*streams) as session:
                await session.initialize();capture=await create(session,'tile')
                page=await session.call_tool('read_tile_capture',{'capture_id':capture,'limit':1})
                row=(page.structured_content or json.loads(page.content[0].text))['rows'][0]
                adapter=McpTargetDrafts(session)
                if fail:
                    with pytest.raises(ProviderError,match='Explicit test failure'):
                        await check.verify(adapter,tmp_path,capture,row,keyfile)
                    assert FakePro.attempts==FakePro.closed==1
                else:
                    report=await check.verify(adapter,tmp_path,capture,row,keyfile)
                    assert report['completed_turns']==report['provider_round_attempts']==report['outgoing_original_evidence_checks']==2
                    assert report['provider_workflows']==2 and report['duplicate_dispatch_refused']
                    assert report['model_semantic_correctness_or_citation_quality_proven'] is False
                    assert FakePro.attempts==FakePro.closed==2
                assert b'offline-plumbing-key' not in (tmp_path/'target-pro-history/history.sqlite3').read_bytes()
    asyncio.run(run())
