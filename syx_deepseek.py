"""Native DeepSeek API streaming/tool protocol. No provider or billing-route fallback."""
import json
import re
import httpx

ENDPOINT='https://api.deepseek.com/chat/completions'


class ProviderError(ValueError):pass


class DeepSeek:
    def __init__(self,api_key,model='deepseek-flash',client=None):
        if not isinstance(api_key,str) or not api_key.strip():raise ValueError('DeepSeek API key is required')
        if model not in {'deepseek-flash','deepseek-v4-pro'}:raise ValueError('Unsupported explicit DeepSeek model')
        self._key=api_key;self.model=model
        self.client=client or httpx.AsyncClient(timeout=httpx.Timeout(45,connect=10),follow_redirects=False)
        self.owns_client=client is None

    async def close(self):
        if self.owns_client:await self.client.aclose()

    async def complete(self,messages,tools,on_text=lambda text:None):
        body={'model':self.model,'messages':messages,'tools':tools,'stream':True,
              'thinking':{'type':'enabled'},'reasoning_effort':'high','max_tokens':8192}
        if len(json.dumps(body,ensure_ascii=False).encode())>2*1024*1024:raise ProviderError('Conversation context exceeds 2 MiB; start a new chat')
        visible='';reasoning='';calls={};finish=None;done=False;size=0;data=[]
        def consume(raw):
            nonlocal visible,reasoning,finish,done
            if raw=='[DONE]':done=True;return
            try:chunk=json.loads(raw)
            except (ValueError,TypeError) as error:raise ProviderError('Invalid DeepSeek stream data') from error
            if not isinstance(chunk,dict) or 'error' in chunk:raise ProviderError('DeepSeek stream reported an error')
            choices=chunk.get('choices',[])
            if not choices:return
            if not isinstance(choices,list) or len(choices)!=1 or not isinstance(choices[0],dict) or choices[0].get('index')!=0:raise ProviderError('Unexpected DeepSeek choice')
            choice=choices[0];delta=choice.get('delta',{})
            if not isinstance(delta,dict):raise ProviderError('Invalid DeepSeek delta')
            if finish is not None and any(delta.get(k) for k in ('content','reasoning_content','tool_calls')):raise ProviderError('Data received after stream completion')
            for field in ['content','reasoning_content']:
                value=delta.get(field)
                if value is not None and not isinstance(value,str):raise ProviderError('Invalid DeepSeek text fragment')
                if field=='content' and value:
                    visible+=value
                    if len(visible.encode())>196608:raise ProviderError('Visible reply exceeds 192 KiB')
                    on_text(value)
                elif field=='reasoning_content' and value:reasoning+=value
            updates=delta.get('tool_calls',[])
            if updates is None:updates=[]
            if not isinstance(updates,list):raise ProviderError('Invalid tool fragments')
            for update in updates:
                if not isinstance(update,dict):raise ProviderError('Invalid tool fragment')
                index=update.get('index')
                if type(index) is not int or not 0<=index<16:raise ProviderError('Too many or invalid tool fragments')
                target=calls.setdefault(index,{'id':'','type':'function','function':{'name':'','arguments':''}})
                if update.get('type','function')!='function':raise ProviderError('Unsupported tool type')
                if 'id' in update:
                    if not isinstance(update['id'],str) or (target['id'] and target['id']!=update['id']):raise ProviderError('Tool call ID changed during stream')
                    target['id']=update['id']
                function=update.get('function',{})
                if not isinstance(function,dict):raise ProviderError('Invalid tool function')
                for field in ['name','arguments']:
                    value=function.get(field,'')
                    if not isinstance(value,str):raise ProviderError('Invalid tool text fragment')
                    target['function'][field]+=value
                if len(target['function']['arguments'].encode())>32768 or len(target['function']['name'])>100:raise ProviderError('Tool request exceeds bounds')
            end=choice.get('finish_reason')
            if end is not None:
                if not isinstance(end,str):raise ProviderError('Invalid stream completion reason')
                if finish is not None:raise ProviderError('Duplicate stream completion')
                finish=end
        try:
            async with self.client.stream('POST',ENDPOINT,json=body,headers={'Authorization':'Bearer '+self._key,'Accept':'text/event-stream'}) as response:
                if response.status_code!=200:raise ProviderError(f'DeepSeek API returned HTTP {response.status_code}; check connection, quota and model. No fallback was attempted.')
                async for line in response.aiter_lines():
                    size+=len(line.encode())+1
                    if size>2*1024*1024:raise ProviderError('DeepSeek response exceeds 2 MiB')
                    if line.startswith('data:'):data.append(line[5:].lstrip(' '))
                    elif not line and data:
                        consume('\n'.join(data));data=[]
                        if done:break
                if data and not done:consume('\n'.join(data))
        except httpx.HTTPError as error:raise ProviderError('DeepSeek connection failed or timed out; no fallback was attempted') from error
        if not done or finish not in {'stop','tool_calls'}:raise ProviderError('DeepSeek reply was interrupted, filtered or truncated; it is not a completed answer')
        if finish=='tool_calls' and not calls or finish=='stop' and calls:raise ProviderError('Inconsistent DeepSeek tool completion')
        ordered=[calls[i] for i in sorted(calls)]
        if len({c['id'] for c in ordered})!=len(ordered):raise ProviderError('Duplicate tool call IDs')
        for call in ordered:
            if not re.fullmatch(r'[A-Za-z0-9_-]{1,200}',call['id']) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}',call['function']['name']):raise ProviderError('Invalid tool call identity')
        message={'role':'assistant','content':visible or None,'reasoning_content':reasoning}
        if ordered:message['tool_calls']=ordered
        if not ordered and not visible:raise ProviderError('DeepSeek returned an empty answer')
        return message
