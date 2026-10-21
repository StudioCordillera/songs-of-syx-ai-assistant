"""Finite copied-city subject-panel clear/select/clear observations through production MCP; no new mapping."""
import argparse
import hashlib
import json
import os
import sys
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'dev')]
import run_selected_resident_query as positive
from game_fixture_lock import exclusive_fixture
from run_stockpile_probe import run,sha
from run_player_chat_check import native_environment

SOURCES=['dev/run_selected_resident_absence.py',
 'dev/candidates/housing/selected-resident-absence/StockpileScenario.java',
 'mod/src/main/java/syx/assistant/UiContextCollector.java']
GAME_SOURCES=positive.GAME_SOURCES+['view/sett/ui/subject/UISubjects.java',
 'view/sett/ui/subject/UISubject.java','view/sett/SettView.java','view/interrupter/ISidePanels.java']

async def verify(state,manifest):
    from mcp import ClientSession,StdioServerParameters
    from mcp.client.stdio import stdio_client
    from syx_mcp import Snapshot
    report=await positive.verify(state,manifest)
    fixture=json.loads((state/'stockpile-fixture.json').read_text())
    names=['selected-absent-before.json',*[e['file'] for e in fixture['samples']],'selected-absent-after.json']
    snapshots=[Snapshot.model_validate_json((state/n).read_bytes()) for n in names]
    assert len({s.snapshot_id for s in snapshots})==4
    assert len({s.session_id for s in snapshots})==len({s.tick for s in snapshots})==1
    for s in (snapshots[0],snapshots[-1]):
        assert s.game_loaded and s.scene['settlement_scene_kind']=='city'
        assert s.domains['entities'].data['selected_subject'] is None
        assert s.ui_context['selected_subject'] is None
        assert s.domains['entities'].data['items'], 'Ordinary cached entities remain available'
    retained=state/'retained-subject-absence';retained.mkdir(mode=0o700)
    env={**native_environment(os.environ),'SYX_STATE_DIR':str(retained)}
    params=StdioServerParameters(command=sys.executable,args=['-m','syx_mcp'],cwd=str(ROOT),env=env)
    spec=json.loads((ROOT/'selected-resident-query-example.json').read_text());calls=0
    async with stdio_client(params) as streams:
      async with ClientSession(*streams) as session:
        await session.initialize()
        async def call(name,args,error=False):
            nonlocal calls
            r=await session.call_tool(name,args);calls+=1
            text=next(c.text for c in r.content if c.type=='text')
            assert len(text.encode())<=65536 and r.is_error==error,text
            return text if error else json.loads(text)
        for i,(name,s) in enumerate(zip(names,snapshots)):
            pending=retained/'snapshot.pending';pending.write_bytes((state/name).read_bytes());pending.replace(retained/'snapshot.json')
            if i:
                old=await call('select_game_state',{'spec':{**spec,'expected_snapshot_id':snapshots[i-1].snapshot_id}},True)
                assert 'Snapshot changed' in old
            raw=await call('query_game_state',{'domain':'entities','pointer':'/selected_subject','expected_snapshot_id':s.snapshot_id})
            assert raw['data']==s.domains['entities'].data['selected_subject']
            if i in (0,3):
                error=await call('select_game_state',{'spec':{**spec,'expected_snapshot_id':s.snapshot_id}},True)
                assert 'Join requires objects and a non-conflicting alias' in error,error
            else:
                result=await call('select_game_state',{'spec':{**spec,'expected_snapshot_id':s.snapshot_id}})
                assert result['results'][0]['matched_total']==1
                assert result['results'][0]['rows'][0]['entity_id']==fixture['samples'][i-1]['entity_id']
                assert result['state']['snapshot_id']==s.snapshot_id and result['ui_context']==s.ui_context
    report.update(scope='Finite cleared subject-panel / selected worker / selected worker / cleared panel production observations in one paused copied-city callback, served unmodified through MCP.',
      actual_mcp_calls=report['actual_mcp_calls']+calls,absence_transition_mcp_calls=calls,
      native_absent_subject_observations=2,original_observations=4,
      absence_preserves_cached_entity_items=True,absent_subject_query_refused=True,
      published_transition_rejects_previous_snapshot_pin=True)
    # The earlier positive verifier supplies shared assertions, not evidence that its historical scenario ran.
    report['source_sha256']={n:sha(ROOT/n) for n in [*positive.SOURCES,*SOURCES] if n!='dev/candidates/housing/selected-resident/StockpileScenario.java'}
    report['selected_game_source_sha256']=positive.GAME_SOURCE_HASHES
    report['private_observation_sha256']=[sha(state/n) for n in names]
    report['public_test_only_actions'].append('VIEW.s.panels.clear before and after subject selection')
    report['limits'].append('Subject-panel removal is tested through public ISidePanels.clear in one callback. This is not physical close-button input, rendered visibility, unpaused selection transitions, missing workplace/housing native faults, cap/scale or unload/menu acceptance.')
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['game-dir','jdk-home','java','save']:p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--candidate-dir',type=Path);p.add_argument('--validation',type=Path)
    a=p.parse_args();review=json.loads((ROOT/'HOUSING_CONTRACT_REVIEW.json').read_text());assert review['passed']
    for n,h in review['source_sha256'].items():assert sha(ROOT/n)==h,n
    assert sha(a.game_dir/'SongsOfSyx.jar')==review['game_jar_sha256'] and sha(a.game_dir/'info/SongsOfSyx-sources.jar')==review['source_archive_sha256']
    with zipfile.ZipFile(a.game_dir/'info/SongsOfSyx-sources.jar') as z:
        positive.GAME_SOURCE_HASHES={n:hashlib.sha256(z.read(n)).hexdigest() for n in GAME_SOURCES}
    with exclusive_fixture():
        run(a,scenario_override=ROOT/'dev/candidates/housing/selected-resident-absence/StockpileScenario.java',extra_sources=[],verifier=verify,
          report_name='selected-resident-absence-validation.json',boundary_review_path=ROOT/'HOUSING_CONTRACT_REVIEW.json',
          completion_marker=('selected-resident-clean-exit.json',{'passed':True,'samples':2}))
