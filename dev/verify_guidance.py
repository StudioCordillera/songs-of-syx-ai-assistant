"""Evaluate the reviewed starter corpus through actual MCP; no game or inference required."""
import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from syx_knowledge import install_seed


async def verify(directory):
    directory=directory.resolve()
    root=Path(__file__).resolve().parent.parent
    install_seed(directory)
    cases=json.loads((root/'guidance-questions.json').read_text())
    # Provider secrets have no role in local evidence retrieval.
    env={k:v for k,v in os.environ.items() if not any(s in k for s in ('API_KEY','ACCESS_TOKEN','REFRESH_TOKEN'))}
    env['SYX_STATE_DIR']=str(directory)
    params=StdioServerParameters(command=sys.executable,args=['-m','syx_mcp'],cwd=str(root),env=env)
    results=[]
    async with stdio_client(params) as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()
            for case in cases:
                response=await session.call_tool('search_guidance',{'query':case['query'],'game_version':'0.71.44','limit':1})
                text=next(c.text for c in response.content if c.type=='text')
                assert not response.is_error,text
                assert len(text.encode())<=65536
                found=json.loads(text)
                if case['expected_id'] is None:
                    assert not found['results']
                    results.append({'expected':None,'passed':True});continue
                source=found['results'][0]
                assert source['id']==case['expected_id'],(case['query'],source['id'])
                assert source['matched_terms'] and source['retrieval_score']>0
                assert source['url'].startswith('https://') and source['author'] and source['retrieved_at']
                assert source['version_compatibility'] in {'family_match','unknown'}
                assert source['version_notes']
                results.append({'source_id':source['id'],'url':source['url'],'authority':source['authority'],
                    'version_compatibility':source['version_compatibility'],'passed':True})
    report={'passed':True,'cases':results,'case_count':len(cases),'inference_calls':0,
        'evaluated_game_version':'0.71.44',
        'source_sha256':{n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in
            ('syx_mcp.py','syx_knowledge.py','guidance-questions.json','dev/verify_guidance.py')},
        'limits':[f'{len(cases)} authored retrieval cases, not comprehensive advice correctness or a semantic-search benchmark.',
            'Historical developer explanations do not establish current-patch mechanics.',
            'Starter corpus is locally reviewed and not automatically refreshed; no complete guide collection.']}
    (directory/'guidance-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True)
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state-dir',type=Path,required=True)
    asyncio.run(verify(parser.parse_args().state_dir))
