"""Explicit paid DeepSeek Pro check for developer reference tools; synthetic demo context, no game process.

Never run from pytest/CI. Requires --env-file; writes only a fresh private runtime directory.
"""
import argparse,asyncio,hashlib,json,os,sys,tempfile
from datetime import datetime,timezone
from pathlib import Path
from uuid import uuid4
ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'dev')]
from syx_chat_service import read_key_file
from syx_chat_store import ChatStore
from syx_deepseek import DeepSeek
from dev.blueprint_chat_candidate import BlueprintConversation,EXTRA
from dev.blueprint_examples import load_registry
SOURCES=['dev/run_blueprint_pro_check.py','dev/blueprint_chat_candidate.py','dev/blueprint_mcp_candidate.py',
 'dev/blueprint_examples.py','syx_chat.py','syx_chat_store.py','syx_deepseek.py','syx_mcp.py',
 'blueprint-examples-candidate.json','BLUEPRINT_CATALOG_VALIDATION.json','snapshot.example.json']
URL='https://github.com/StudioCordillera/songs-of-syx-ai-assistant/blob/main/BLUEPRINT_EXAMPLES_CANDIDATE.md'
ID='warehouse-two-items-teaching-grid'
PROMPTS=[
 'This is a reference-tool integration check, not a question about the synthetic demo world. Use search_blueprint_examples with query "warehouse aisle" and explicit game_version "0.71.44", then get_blueprint_example for the discovered original example. Explain its teaching geometry in under 200 words, cite its source URL and reviewed version, and clearly state that actual construction, capacity, materials, efficiency and the demo world are not validated. Use only those two reference tools; no need to query live game data.',
 'Now use get_blueprint_example again for warehouse-two-items-teaching-grid with explicit game_version "0.72.0". In under 120 words, explain why the old catalog evidence does not establish compatibility or construction on 0.72.0. Cite the original source URL and retain the original reviewed version. Do not treat the synthetic demo state as a real world.'
]

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

async def run(state,key):
    from mcp import ClientSession,StdioServerParameters
    from mcp.client.stdio import stdio_client
    registry=load_registry();snapshot=json.loads((ROOT/'snapshot.example.json').read_text());assert snapshot['demo'] is True
    session_id=str(uuid4());snapshot['session_id']=session_id
    async def heartbeat():
        # Freshness here is explicitly synthetic fixture-clock data, never a refreshed native observation.
        while True:
            snapshot['captured_at']=datetime.now(timezone.utc).isoformat()
            pending=state/'snapshot.pending';pending.write_text(json.dumps(snapshot));pending.replace(state/'snapshot.json')
            await asyncio.sleep(1)
    task=asyncio.create_task(heartbeat());await asyncio.sleep(0)
    counts={'started_requests':0,'completed_round_trips':0,'schema_counts':[]}
    class CountedPro(DeepSeek):
        async def complete(self,messages,tools,on_text=lambda text:None):
            assert len(tools)==21 and EXTRA<={t['function']['name'] for t in tools}
            counts['started_requests']+=1;counts['schema_counts'].append(len(tools))
            value=await super().complete(messages,tools,on_text);counts['completed_round_trips']+=1;return value
    store=ChatStore(state/'history',secrets=[key]);chat=store.new(session_id,'Developer blueprint Pro check',model='deepseek-v4-pro')
    params=StdioServerParameters(command=sys.executable,args=['-m','dev.blueprint_mcp_candidate'],cwd=str(ROOT),env={'SYX_STATE_DIR':str(state)})
    answers=[]
    try:
      async with stdio_client(params) as streams:
        async with ClientSession(*streams) as mcp:
            await mcp.initialize();conversation=BlueprintConversation(store,mcp,lambda _:CountedPro(key,model='deepseek-v4-pro'))
            for prompt in PROMPTS:
                answers.append(await conversation.run(chat['chat_id'],str(uuid4()),session_id,prompt))
      turns=store.turns(chat['chat_id']);assert len(turns)==2 and all(t['status']=='completed' for t in turns)
      events=store.events(chat['chat_id'],limit=100);calls=[e['payload'] for e in events if e['kind']=='tool' and e['payload']['name'] in EXTRA]
      by_turn={t['turn_id']:[c for e in events if e['turn_id']==t['turn_id'] and e['kind']=='tool' and (c:=e['payload'])['name'] in EXTRA] for t in turns}
      # Check durable tool evidence, not an assertion that prose proves engine placement/semantic correctness.
      for t in turns:
          group=by_turn[t['turn_id']];assert group and all(not c['result'].get('error') and not c['result'].get('isError') for c in group)
      assert {'search_blueprint_examples','get_blueprint_example'}<={c['name'] for c in by_turn[turns[0]['turn_id']]}
      retrieved=[]
      for c in calls:
          if c['name']=='get_blueprint_example':
              value=json.loads(c['result']['content'][0]['text']);assert value['geometry']['grid']==['.....','.RF..','E....','.RF..','.....']
              assert value['execution_supported'] is False and value['construction_validated'] is False
              assert value['evidence']['catalog_report_sha256']==registry.report_hash;retrieved.append(value)
      assert any(v['requested_game_version']=='0.71.44' and v['compatibility']=='exact_catalog_version_only' for v in retrieved)
      assert any(v['requested_game_version']=='0.72.0' and v['compatibility']=='unknown' for v in retrieved)
      assert all(URL in a and '0.71.44' in a for a in answers)
      assert any(word in answers[1].lower() for word in ['unknown','unverified','not establish','not verified','cannot establish'])
      for n,h in SOURCE_HASHES.items():assert sha(ROOT/n)==h,'Source changed during paid check: '+n
      return {'passed':True,'evaluated_at':datetime.now(timezone.utc).isoformat(),
       'scope':'Two explicit paid Pro turns over developer blueprint conversation/MCP with an explicitly synthetic demo heartbeat; no game/native UI or production coordinator integration.',
       'requested_model':'deepseek-v4-pro','adapter_model':'deepseek-v4-pro','remote_model_identity_independently_attested':False,
       'completed_turns':2,**counts,'actual_reference_tool_calls':len(calls),'get_results_checked':len(retrieved),
       'first_turn_search_and_get':True,'other_version_unknown_evidence':True,'source_url_and_original_version_in_both_final_replies':True,
       'catalog_report_sha256':registry.report_hash,'source_sha256':SOURCE_HASHES,
       'prompt_sha256':[hashlib.sha256(p.encode()).hexdigest() for p in PROMPTS],
       'visible_reply_sha256':[hashlib.sha256(a.encode()).hexdigest() for a in answers],
       'fixture':{'demo':True,'game_version':snapshot['game_version'],'clock':'Synthetic fixture timestamp republished once per second to exercise existing freshness admission; no real game observations refreshed.'},
       'native_game_calls':0,'production_integration':False,
       'limits':['Controlled prompts explicitly request tools/version/citation/caveats. Successful model/schema transport, durable evidence and literal reply fragments do not establish general semantic entailment, unscripted retrieval quality or advice correctness.',
        'Original geometry/catalog evidence retains its earlier native scope. No actual room construction, map/path/door/roof/capacity/cost/efficiency/optimality or third-party layout/rights validation.',
        'This uses the developer subclass/server and private disposable history, not the production coordinator/native chat/player. Synthetic demo clock/session freshness is not live-world acceptance.',
        'No provider/account expansion, fallback model, runner retry or credit purchase. The explicit requested API model is recorded; remote model identity is not independently attested.']}
    finally:
      task.cancel()
      try:await task
      except asyncio.CancelledError:pass
      store.close()

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--env-file',type=Path,required=True)
    args=parser.parse_args();key=read_key_file(args.env_file)
    state=Path(tempfile.mkdtemp(prefix='blueprint-pro-',dir=ROOT/'runtime'));os.chmod(state,0o700)
    SOURCE_HASHES={n:sha(ROOT/n) for n in SOURCES}
    try:report=asyncio.run(run(state,key))
    except BaseException as error:
        report={'passed':False,'evaluated_at':datetime.now(timezone.utc).isoformat(),'error_type':type(error).__name__,
         'scope':'Developer explicit paid Pro check failed; inspect private history/log. No passing provider evidence or player promotion.',
         'source_sha256':SOURCE_HASHES,'runner_retry_attempted':False}
        (state/'blueprint-pro-validation.json').write_text(json.dumps(report,indent=2)+'\n')
        print('Developer Pro check failed; private report:',state/'blueprint-pro-validation.json');raise SystemExit(1)
    (state/'blueprint-pro-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Two developer DeepSeek Pro turns passed; private report:',state/'blueprint-pro-validation.json')
