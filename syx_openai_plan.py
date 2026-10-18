"""Stateless Responses transport for explicitly authorized ChatGPT plan usage.

Not yet wired into the game coordinator: account-bound model selection and an
approved independent sign-in are required. No API-key/Codex-token fallback exists.
"""
import json
import re
import httpx
from syx_deepseek import ProviderError

ROOT='https://api.openai.com/v1'


async def list_models(access_token,client):
    response=await client.get(ROOT+'/models',headers={'Authorization':'Bearer '+access_token},follow_redirects=False)
    if response.status_code!=200:raise ProviderError('ChatGPT account model catalog unavailable; no alternate authentication attempted')
    if len(response.content)>2*1024*1024:raise ProviderError('Model catalog exceeds bounds')
    try:
        records=response.json()['models']
        if not isinstance(records,list) or len(records)>1000:raise ValueError()
        models=[]
        for record in records:
            if record.get('visibility')!='list':continue
            slug=record['slug'];name=record['display_name']
            if not isinstance(slug,str) or not re.fullmatch(r'[A-Za-z0-9._:-]{1,128}',slug) or not isinstance(name,str):raise ValueError()
            models.append(dict(slug=slug,display_name=name[:100]))
        if not models or len({r['slug'] for r in models})!=len(models):raise ValueError()
        return models
    except (ValueError,KeyError,TypeError,AttributeError):raise ProviderError('Invalid account model catalog') from None


class OpenAIPlan:
    def __init__(self,access_token,model,available_models,client=None):
        if not access_token or model not in available_models:raise ProviderError('Choose a model from this authorized account catalog')
        self._token=access_token;self.model=model
        self.client=client or httpx.AsyncClient(timeout=httpx.Timeout(45,connect=10),follow_redirects=False)
        self.owns=client is None

    async def close(self):
        if self.owns:await self.client.aclose()

    async def complete(self,messages,tools,on_text=lambda text:None):
        instructions=[];items=[]
        for message in messages:
            role=message['role']
            if role=='system':instructions.append(message['content'])
            elif role=='user':items.append(dict(role='user',content=message['content']))
            elif role=='assistant':
                if '_responses_output' not in message:raise ProviderError('Missing private Responses continuation; reset this context explicitly')
                items.extend(message['_responses_output'])
            elif role=='tool':items.append(dict(type='function_call_output',call_id=message['tool_call_id'],output=message['content']))
            else:raise ProviderError('Unsupported conversation role')
        functions=[dict(type='function',name=tool['function']['name'],description=tool['function'].get('description',''),parameters=tool['function']['parameters'],strict=False) for tool in tools]
        body=dict(model=self.model,input=items,instructions='\n'.join(instructions),store=False,stream=True,include=['reasoning.encrypted_content'])
        if functions:body['tools']=[dict(type='namespace',name='syx',description='Read-only selective Songs of Syx observations and reference evidence',tools=functions)]
        if len(json.dumps(body,ensure_ascii=False,allow_nan=False).encode())>2*1024*1024:raise ProviderError('Conversation exceeds 2 MiB; reset or start a new chat')
        data=[];completed=None;size=0;visible=''
        def consume(raw):
            nonlocal completed,visible
            if raw=='[DONE]':return
            try:event=json.loads(raw)
            except ValueError:raise ProviderError('Invalid Responses stream') from None
            if not isinstance(event,dict):raise ProviderError('Invalid Responses event')
            kind=event.get('type')
            if kind in {'error','response.failed','response.incomplete'}:raise ProviderError('ChatGPT plan reply failed or was incomplete; no API billing fallback attempted')
            if kind=='response.output_text.delta':
                fragment=event.get('delta')
                if not isinstance(fragment,str):raise ProviderError('Invalid visible text fragment')
                visible+=fragment
                if len(visible.encode())>196608:raise ProviderError('Visible answer exceeds 192 KiB')
                on_text(fragment)
            elif kind=='response.completed':
                completed=event.get('response')
                if not isinstance(completed,dict) or completed.get('status')!='completed':raise ProviderError('Response did not complete successfully')
        try:
            async with self.client.stream('POST',ROOT+'/responses',json=body,headers={'Authorization':'Bearer '+self._token,'Accept':'text/event-stream'},follow_redirects=False) as response:
                if response.status_code!=200:raise ProviderError('ChatGPT plan request returned HTTP '+str(response.status_code)+'; no API billing fallback attempted')
                async for line in response.aiter_lines():
                    size+=len(line.encode())+1
                    if size>2*1024*1024:raise ProviderError('Responses stream exceeds 2 MiB')
                    if line.startswith('data:'):data.append(line[5:].lstrip())
                    elif not line and data:
                        consume('\n'.join(data));data=[]
                        if completed is not None:break
                if data and completed is None:consume('\n'.join(data))
        except httpx.HTTPError:raise ProviderError('ChatGPT plan connection failed; no alternate endpoint attempted') from None
        if completed is None:raise ProviderError('Stream ended before response.completed')
        output=completed.get('output');text='';calls=[]
        if not isinstance(output,list):raise ProviderError('Invalid response output')
        for item in output:
            if not isinstance(item,dict):raise ProviderError('Invalid response item')
            if item.get('type')=='message':
                blocks=item.get('content')
                if not isinstance(blocks,list):raise ProviderError('Invalid message content')
                for block in blocks:
                    if not isinstance(block,dict):raise ProviderError('Invalid message block')
                    value=block.get('text') if block.get('type')=='output_text' else block.get('refusal') if block.get('type')=='refusal' else None
                    if not isinstance(value,str):raise ProviderError('Unsupported message content')
                    text+=value
            elif item.get('type')=='function_call':
                caller=item.get('caller') or {}
                if not isinstance(caller,dict):raise ProviderError('Invalid function caller')
                if item.get('namespace')!='syx' or caller.get('type','direct')!='direct':raise ProviderError('Unexpected function namespace or caller')
                if not isinstance(item.get('call_id'),str) or not isinstance(item.get('name'),str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',item['call_id']) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}',item['name']):raise ProviderError('Invalid function call identity')
                args=item.get('arguments')
                if not isinstance(args,str) or len(args.encode())>32768:raise ProviderError('Function arguments exceed bounds')
                calls.append(dict(id=item['call_id'],type='function',function=dict(name=item['name'],arguments=args)))
            elif item.get('type')!='reasoning':raise ProviderError('Unsupported response item; no additional tools are enabled')
        if len(text.encode())>196608 or len(calls)>16 or len({c['id'] for c in calls})!=len(calls):raise ProviderError('Answer/tool output exceeds bounds')
        if not text and not calls:raise ProviderError('Empty completed response')
        if visible and visible!=text:raise ProviderError('Streamed text did not match completed output')
        if not visible and text:on_text(text)
        result=dict(role='assistant',content=text or None,_responses_output=output)
        if calls:result['tool_calls']=calls
        return result
