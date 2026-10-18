"""Verify installed room/currency descriptions by hashes and public UI reference links."""
import argparse
import asyncio
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from syx_mcp import Advisor
from verify_context import verify as verify_context


async def verify(directory):
    directory=directory.resolve();root=Path(__file__).resolve().parent.parent
    context_task=asyncio.create_task(asyncio.to_thread(verify_context,directory,240))
    advisor=Advisor(directory/'snapshot.json',directory/'corpus.json')
    deadline=time.monotonic()+100
    while time.monotonic()<deadline:
        try:
            fixture=json.loads((directory/'help-fixture.json').read_text());snapshot=advisor.snapshot()
            if advisor.status(snapshot)['live'] and any(r.category=='room' for r in snapshot.references):break
        except (FileNotFoundError,ValueError):pass
        await asyncio.sleep(.2)
    else:raise AssertionError('No installed help fixture')
    assert len({r.id for r in snapshot.references})==len(snapshot.references)
    expected=fixture['references'];counts=Counter(row['category'] for row in expected)
    assert counts['room']>0 and counts['research_currency']>0
    params=StdioServerParameters(command=sys.executable,args=['-m','syx_mcp'],cwd=str(root),
        env={**os.environ,'SYX_STATE_DIR':str(directory)})
    async with stdio_client(params) as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()
            for row in expected:
                response=await session.call_tool('search_game_references',{'query':row['id'],'category':row['category'],'limit':1})
                text=next(c.text for c in response.content if c.type=='text')
                assert not response.is_error,text
                assert len(text.encode())<=65536
                result=json.loads(text);reference=result['results'][0]
                assert reference['id']==row['id'] and reference['category']==row['category']
                for field in ('title','text'):
                    assert hashlib.sha256(reference[field].encode()).hexdigest()==row[field+'_sha256']
                assert result['state']['game_version']==snapshot.game_version
                assert result['state']['mods']==snapshot.mods
                assert reference['origin'] and reference['id'].split(':',1)[1] in reference['origin']
            # Check links from live data without returning whole domain objects.
            s=advisor.snapshot()
            employment=s.domains['employment'].data['rooms'];research=s.domains['research'].data['currencies']
            ids={row['id'] for row in expected}
            assert employment and research
            assert all(r['reference_id']=='room:'+r['blueprint_id'] and r['reference_id'] in ids for r in employment)
            assert all(r['reference_id']=='research_currency:'+r['id'] and r['reference_id'] in ids for r in research)
            assert all(r['room_reference_id'] in ids for r in s.domains['production'].data['room_data']['flows'])
    context=await context_task
    report={'passed':True,'game_version':snapshot.game_version,'catalog_size':len(snapshot.references),
        'new_categories_checked':dict(counts),'public_title_description_hash_parity':True,
        'actual_mcp_exact_id_and_category_lookup':True,'version_mod_provenance':True,
        'employment_production_currency_reference_links':True,'ui_context_regression':context,
        'limits':['Descriptions are installed data; active mods can override them, and empty descriptions do not establish mechanics.',
            'Room context links blueprint help, not a UI-selected instance, tooltip or complete topmost panel.',
            'Eleven sampled UI/lifecycle phases, with main menu unknown only after expiry; not all menus or all game states.']}
    (directory/'installed-help-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True);return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state-dir',type=Path,required=True)
    asyncio.run(verify(p.parse_args().state_dir))
