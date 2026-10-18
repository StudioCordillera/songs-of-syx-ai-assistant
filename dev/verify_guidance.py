"""Evaluate the reviewed starter corpus through actual MCP; no game or inference required."""
import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import sys
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from syx_knowledge import install_seed


def normalized(text):
    return " ".join(text.casefold().split())


def validate_result(case, found):
    """Check returned evidence against independently authored advice expectations.

    Passage matching is a regression guard, not automated semantic entailment.
    The advice and caveat relationship requires human review.
    """
    result={"case_id":case["case_id"], "query":case["query"],
            "game_version":case.get("game_version", "0.71.44"),
            "authority_filter":case.get("authority")}
    assert found["game_version"] == result["game_version"]
    assert found["warning"] and found["retrieval"]
    if case["expected_id"] is None:
        assert not found["results"], (case["case_id"], "unexpected evidence")
        return {**result, "expected":None, "passed":True}
    assert found["results"], (case["case_id"], "missing evidence")
    source=found["results"][0]
    assert source["id"]==case["expected_id"], (case["case_id"], source["id"])
    for actual, expected in (("url","expected_url"), ("authority","expected_authority"),
                             ("author","expected_author"),
                             ("version_compatibility","expected_compatibility")):
        assert source[actual]==case[expected], (case["case_id"], actual)
    assert source["matched_terms"] and source["retrieval_score"]>0
    assert source["retrieved_at"] and source["version_notes"]
    body=normalized(source["text"])
    context=normalized(source["text"]+" "+source["version_notes"])
    for passage in case["required_passages"]:
        assert normalized(passage) in body, (case["case_id"], "support missing", passage)
    for caveat in case["required_caveats"]:
        assert normalized(caveat) in context, (case["case_id"], "caveat missing", caveat)
    return {**result, "source_id":source["id"], "url":source["url"],
        "authority":source["authority"], "version_compatibility":source["version_compatibility"],
        "reviewed_advice":case["reviewed_advice"],
        "support_passages_checked":len(case["required_passages"]),
        "caveats_checked":len(case["required_caveats"]),
        "returned_text_sha256":hashlib.sha256(source["text"].encode()).hexdigest(), "passed":True}


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
                arguments={'query':case['query'],'game_version':case.get('game_version','0.71.44'),'limit':1}
                if 'authority' in case:arguments['authority']=case['authority']
                response=await session.call_tool('search_guidance',arguments)
                text=next(c.text for c in response.content if c.type=='text')
                assert not response.is_error,text
                assert len(text.encode())<=65536
                results.append(validate_result(case,json.loads(text)))
    report={'passed':True,'evaluated_at':datetime.now(timezone.utc).isoformat(),'cases':results,'case_count':len(cases),'inference_calls':0,
        'evaluated_game_versions':sorted({c.get('game_version','0.71.44') for c in cases}),
        'corpus_size':len(json.loads((directory/'corpus.json').read_text())),
        'corpus_sha256':hashlib.sha256((directory/'corpus.json').read_bytes()).hexdigest(),
        'support_checks':sum(r.get('support_passages_checked',0) for r in results),
        'caveat_checks':sum(r.get('caveats_checked',0) for r in results),
        'source_sha256':{n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in
            ('syx_mcp.py','syx_knowledge.py','guidance-questions.json','dev/verify_guidance.py')},
        'limits':[f'{len(cases)} authored retrieval cases with manually reviewed advice/passages; not comprehensive advice correctness or a semantic-search benchmark.',
            'Literal supporting-passage and caveat checks catch regressions; they do not establish semantic entailment or provider answer correctness.',
            'No new external-source review or live web refresh is performed by this local evaluator.',
            'Historical developer explanations do not establish current-patch mechanics.',
            'Starter corpus is locally reviewed and not automatically refreshed; no complete guide collection.']}
    (directory/'guidance-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True)
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state-dir',type=Path,required=True)
    asyncio.run(verify(parser.parse_args().state_dir))
