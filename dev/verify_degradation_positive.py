"""Check a TEST-ONLY public maintenance action in an isolated copied game; publish metadata only."""
import argparse
import asyncio
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from verify_production import verify as verify_production


async def verify(directory):
    report=await verify_production(directory)
    control=json.loads((directory/'degradation-positive-fixture.json').read_text())
    fixture=json.loads((directory/'production-fixture.json').read_text())
    assert control['test_only'] and control['save_written'] is False
    assert control['public_action']=='MAINTENANCE.vandalise(int,int)'
    assert control['before']==0 and control['after']>0 and 1<=control['public_action_calls']<=512
    target=[row for row in fixture['flows'] if row['room_id']==control['room_id']]
    assert target and all(row['room_degradation_raw']==control['after'] for row in target)
    assert any(row['direction']=='output' for row in target)
    assert report['degradation']['passed'] and report['degradation']['positive_rooms']>=1
    # Keep the generic verifier's evidence, but correct its baseline-only limitation for this controlled case.
    report['degradation']['limits']=[
        'One test-only bounded public maintenance action sequence changes a copied room; no all-room, external-override, cap/fault or large-city acceptance.'
        if item.startswith('No forced room wear,') else item for item in report['degradation']['limits']]
    report['degradation']['controlled_test_only_public_action']=control['public_action']
    (directory/'production-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    root=Path(__file__).resolve().parent.parent
    result={'passed':True,'validated_at':datetime.now(timezone.utc).isoformat(),
        'game_version':report['game_version'],'controlled_room_before':control['before'],'controlled_room_after':control['after'],
        'bounded_public_action_calls':control['public_action_calls'],'controlled_room_flow_rows_checked':len(target),
        'producer_rooms_checked':report['degradation']['producer_rooms_checked'],
        'positive_rooms':report['degradation']['positive_rooms'],'zero_rooms':report['degradation']['zero_rooms'],
        'public_getter_and_actual_mcp_parity':True,'sorted_output_and_nullable_staffing_join':True,
        'test_only_public_action':control['public_action'],'save_written':False,'inference_calls':0,
        'production_verification_report_sha256':hashlib.sha256((directory/'production-validation.json').read_bytes()).hexdigest(),
        'source_sha256':{name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in [
            'mod/tests/DegradationPositiveScenario.java','mod/tests/LiveSmoke.java','mod/tests/ProductionScenario.java',
            'dev/verify_degradation_positive.py','dev/verify_production.py','mod/src/main/java/syx/assistant/StateCollector.java',
            'degradation-query-example.json']},
        'limits':['One deliberately worn producer in a paused disposable copied game, not natural deterioration or all room types.',
            'Only the test fixture invokes the public maintenance action; the production observer remains read-only and never obtains a degrader handle.',
            'Controlled maintenance mutates only copied in-process state; no save, normal profile, private field, reflection or native input is used.',
            'No actual output effect, full modifier/age/resource-cost model, large-city/cap/fault or exhaustive menu acceptance.']}
    (directory/'degradation-positive-validation.json').write_text(json.dumps(result,indent=2)+'\n')
    print('Controlled positive room value matches public getter and actual MCP output selection.')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state-dir',type=Path,required=True)
    asyncio.run(verify(p.parse_args().state_dir))
