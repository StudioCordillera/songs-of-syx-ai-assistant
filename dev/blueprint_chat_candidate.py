"""Developer-only admission seam for reference tools in the unchanged conversation lifecycle.

No production tool allowlist/global mutation, provider fallback, execution or client UI integration.
"""
import asyncio
from contextvars import ContextVar
from copy import deepcopy
from pydantic import BaseModel,ConfigDict
from syx_chat import Conversation,TOOLS,encoded
from dev.blueprint_mcp_candidate import SearchRequest,GetRequest

EXTRA=frozenset({'search_blueprint_examples','get_blueprint_example'})
class SearchArguments(BaseModel):
    model_config=ConfigDict(strict=True,extra='forbid')
    request:SearchRequest
class GetArguments(BaseModel):
    model_config=ConfigDict(strict=True,extra='forbid')
    request:GetRequest


class _ReferenceProvider:
    def __init__(self,provider,schemas):self.provider=provider;self.schemas=deepcopy(schemas)
    async def complete(self,messages,schemas,emit):
        if {s['function']['name'] for s in schemas}!=TOOLS:raise ValueError('Base conversation tool set changed')
        return await self.provider.complete(messages,deepcopy(schemas)+deepcopy(self.schemas),emit)
    async def close(self):await self.provider.close()


class BlueprintConversation(Conversation):
    def __init__(self,store,mcp,provider_factory):
        self._reference_schemas=ContextVar('blueprint_reference_schemas',default=None)
        def factory(chat):
            grant=self._reference_schemas.get()
            if grant is None or not grant['active']:raise ValueError('Reference tools not admitted for this turn')
            return _ReferenceProvider(provider_factory(chat),grant['schemas'])
        super().__init__(store,mcp,factory)
        self.instructions+='\nDeveloper reference tools return original teaching schematics, never executable construction plans or live selections. Cite the original source and retain catalog/version/rights/materials/placement uncertainty. Never infer optimality or numeric capacity from a grid.'

    async def _admit_references(self):
        async with asyncio.timeout(5):listing=await self.mcp.list_tools()
        selected=[t for t in listing.tools if t.name in EXTRA]
        if len(selected)!=2 or {t.name for t in selected}!=EXTRA:raise ValueError('Required reference tools missing or duplicated')
        for tool in selected:
            a=tool.annotations
            if a is None or a.read_only_hint is not True or a.idempotent_hint is not True or a.destructive_hint is not False or a.open_world_hint is not False:
                raise ValueError('Reference tool read-only contract unavailable')
        return sorted([{'type':'function','function':{'name':t.name,'description':t.description or '',
          'parameters':deepcopy(t.input_schema)}} for t in selected],key=lambda x:x['function']['name'])

    async def _tool(self,name,arguments):
        if name not in EXTRA:return await super()._tool(name,arguments)
        grant=self._reference_schemas.get()
        if grant is None or not grant['active']:return {'error':'Reference tools not admitted for this turn'}
        try:
            kind=SearchArguments if name=='search_blueprint_examples' else GetArguments
            args=kind.model_validate(arguments).model_dump()
            current=await self._admit_references()
            if not grant['active'] or current!=grant['schemas']:raise ValueError('Reference tool definitions changed')
            response=await self.mcp.call_tool(name,args,read_timeout_seconds=12)
            data=response.model_dump(mode='json',by_alias=True,exclude_none=True)
            if len(encoded(data).encode())>65536:return {'error':'Reference evidence exceeds the 64 KiB chat limit; use summary search'}
            return data
        except asyncio.CancelledError:raise
        except Exception:return {'error':'Reference tool unavailable, invalid or changed; no construction or live observation established'}

    async def run(self,chat_id,turn_id,session_id,text,on_text=lambda text:None):
        schemas=await self._admit_references()
        grant={'schemas':schemas,'active':True}
        token=self._reference_schemas.set(grant)
        try:return await super().run(chat_id,turn_id,session_id,text,on_text)
        finally:
            grant['active']=False
            self._reference_schemas.reset(token)
