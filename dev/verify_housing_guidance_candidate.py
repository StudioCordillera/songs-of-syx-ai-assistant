"""Evaluate reviewed housing candidates alongside unchanged starter guidance via real MCP, only in a new private runtime directory."""
import argparse,asyncio,hashlib,json,os,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'dev')]
from syx_knowledge import install_seed,SEEDS
from syx_mcp import Source
from verify_guidance import validate_result

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

async def verify(directory):
    from mcp import ClientSession,StdioServerParameters
    from mcp.client.stdio import stdio_client
    directory=directory.resolve()
    if not directory.is_relative_to(ROOT/'runtime') or directory==ROOT/'runtime':raise ValueError('Use a new isolated directory beneath this checkout runtime/')
    if directory.exists():raise ValueError('Refuse an existing corpus/state directory; use a new runtime directory')
    records=json.loads((ROOT/'housing-guidance-candidate.json').read_text())
    review=json.loads((ROOT/'HOUSING_REFERENCE_REVIEW.json').read_text())
    assert review['candidate_file_sha256']==sha(ROOT/'housing-guidance-candidate.json')
    sources=[Source.model_validate(r) for r in records]
    assert len(sources)==len({s.id for s in sources})==2
    for source,proof in zip(sources,review['sources']):
        assert source.id==proof['id'] and source.url==proof['canonical_url']
        assert source.author==proof['author']=='Gamatron' and source.authority==proof['authority']=='developer'
        assert source.game_versions==proof['game_versions']==[] and proof['original_author_badge_and_profile_verified']
        assert hashlib.sha256(source.text.encode()).hexdigest()==proof['summary_body_sha256']
        assert hashlib.sha256(source.version_notes.encode()).hexdigest()==proof['version_notes_sha256']
    directory.mkdir(mode=0o700,parents=True);install_seed(directory)
    corpus_path=directory/'corpus.json';original=json.loads(corpus_path.read_text());by_id={r['id']:r for r in original}
    assert not any(s.id in by_id for s in sources)
    corpus=original+[s.model_dump(mode='json') for s in sources]
    corpus_path.write_text(json.dumps(corpus,indent=2)+'\n');corpus_path.chmod(0o600)
    assert len(corpus)==len(SEEDS)+2==15 and corpus[:len(original)]==original
    baseline=json.loads((ROOT/'guidance-questions.json').read_text())
    new=json.loads((ROOT/'housing-guidance-candidate-questions.json').read_text());assert len(baseline)==37 and len(new)==8
    env={k:v for k,v in os.environ.items() if not any(s in k for s in ('API_KEY','ACCESS_TOKEN','REFRESH_TOKEN'))};env['SYX_STATE_DIR']=str(directory)
    params=StdioServerParameters(command=sys.executable,args=['-m','syx_mcp'],cwd=str(ROOT),env=env)
    results=[]
    async with stdio_client(params) as streams:
      async with ClientSession(*streams) as session:
        await session.initialize()
        for case in baseline+new:
            args={'query':case['query'],'game_version':case.get('game_version','0.71.44'),'limit':1}
            if 'authority' in case:args['authority']=case['authority']
            response=await session.call_tool('search_guidance',args)
            text=next(c.text for c in response.content if c.type=='text');assert not response.is_error and len(text.encode())<=65536
            results.append(validate_result(case,json.loads(text)))
    report={'passed':True,'evaluated_at':datetime.now(timezone.utc).isoformat(),
      'scope':'Developer-only two historical housing summaries in a separate fifteen-record corpus through unchanged production MCP; not a production seed/client release.',
      'case_count':len(results),'baseline_cases_unchanged':len(baseline),'new_cases':len(new),'corpus_size':len(corpus),
      'existing_seed_records_and_review_dates_preserved':True,'production_seed_corpus_unchanged':True,
      'candidate_exact_family_future_versions_all_unknown':True,'unrelated_official_substitution_refused':True,
      'actual_mcp_calls':len(results),'inference_calls':0,'game_calls':0,
      'corpus_sha256':sha(corpus_path),'source_review_sha256':sha(ROOT/'HOUSING_REFERENCE_REVIEW.json'),
      'source_sha256':{n:sha(ROOT/n) for n in ['dev/verify_housing_guidance_candidate.py','dev/verify_guidance.py','syx_mcp.py','syx_knowledge.py','housing-guidance-candidate.json','housing-guidance-candidate-questions.json','guidance-questions.json']},
      'cases':results,
      'limits':['Original canonical developer comment review is recorded separately. This evaluator reads pinned summaries, not live webpages; rerunning never refreshes retrieval dates.',
        'Eight authored candidate cases plus unchanged baseline; literal fragments/caveats are regression guards, not independent semantic entailment or provider answer accuracy.',
        'Historical proximity and EA64 density/privacy statements remain unknown for current/family/future game versions. No current numeric distance, eligibility, geometry, complete housing mechanic or optimal blueprint inferred.',
        'Candidates are not appended to production SEEDS or installed in player worlds. Promotion requires separate source/migration/provider/core/distribution/release gates; unchanged player evidence is not relabeled.']}
    output=directory/'housing-guidance-candidate-validation.json';output.write_text(json.dumps(report,indent=2)+'\n')
    print('Housing guidance candidate passed:',output)
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state-dir',type=Path,required=True)
    asyncio.run(verify(p.parse_args().state_dir))
