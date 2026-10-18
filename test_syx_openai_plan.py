import asyncio
import json
import httpx
import pytest
from syx_openai_plan import OpenAIPlan,list_models
from syx_deepseek import ProviderError


def sse(events):return ''.join('data: '+json.dumps(event)+'\n\n' for event in events)


def message(text):return {'type':'message','role':'assistant','content':[{'type':'output_text','text':text}]}


def test_plan_stream_and_stateless_tool_continuation():
    async def run():
        sent=[];counter=0
        def handle(request):
            nonlocal counter
            body=json.loads(request.content);sent.append(body);counter+=1
            if counter==1:
                output=[{'type':'reasoning','id':'rs_1','summary':[],'encrypted_content':'private-encrypted-state'},
                    {'type':'function_call','id':'fc_1','call_id':'call_1','namespace':'syx','name':'game_status','arguments':'{}'}]
                events=[{'type':'response.completed','response':{'status':'completed','output':output}}]
            else:events=[{'type':'response.output_text.delta','delta':'Answer'}, {'type':'response.completed','response':{'status':'completed','output':[message('Answer')]}}]
            return httpx.Response(200,text=sse(events))
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            adapter=OpenAIPlan('test-token','account-model',['account-model'],client)
            messages=[{'role':'system','content':'Read-only instructions'},{'role':'user','content':'Question'}]
            tools=[{'function':{'name':'game_status','parameters':{'type':'object'},'description':'Status'}}]
            first=await adapter.complete(messages,tools)
            assert first['tool_calls'][0]['id']=='call_1'
            messages += [first,{'role':'tool','tool_call_id':'call_1','content':'Tool evidence'}]
            visible=[];answer=await adapter.complete(messages,tools,visible.append)
            assert answer['content']=='Answer' and visible==['Answer']
        assert all(body['store'] is False and body['stream'] is True for body in sent)
        assert sent[0]['tools'][0]['type']=='namespace'
        assert sent[1]['input'][-1]['call_id']=='call_1'
        assert any(item.get('encrypted_content')=='private-encrypted-state' for item in sent[1]['input'])
        assert not {'previous_response_id','max_output_tokens','temperature','metadata'}&sent[0].keys()
        assert all(item.get('role')!='system' for item in sent[0]['input'])
    asyncio.run(run())


@pytest.mark.parametrize('events',[
    [{'type':'response.output_text.delta','delta':'partial'}],
    [{'type':'response.failed','response':{'error':{'message':'private-server-body'}}}],
    [{'type':'response.incomplete'}],
    [{'type':'response.completed','response':{'status':'incomplete','output':[]}}],
    [{'type':'response.completed','response':{'status':'completed','output':[{'type':'computer_call'}]}}],
    [{'type':'response.completed','response':{'status':'completed','output':[{'type':'function_call','namespace':'other','call_id':'call','name':'x','arguments':'{}'}]}}],
])
def test_plan_failures_never_count_as_completion(events):
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _:httpx.Response(200,text=sse(events)))) as client:
            with pytest.raises(ProviderError) as caught:await OpenAIPlan('test-token','model',['model'],client).complete([{'role':'user','content':'Question'}],[])
            assert 'private-server-body' not in str(caught.value)
    asyncio.run(run())


def test_catalog_is_account_specific_and_ordered():
    async def run():
        records=[dict(slug='model-a',display_name='A',visibility='list'),dict(slug='hidden',display_name='Hidden',visibility='hidden'),dict(slug='model-b',display_name='B',visibility='list')]
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _:httpx.Response(200,json={'models':records}))) as client:
            assert [item['slug'] for item in await list_models('test-token',client)]==['model-a','model-b']
        with pytest.raises(ProviderError):OpenAIPlan('test-token','unlisted',['model-a'])
    asyncio.run(run())
