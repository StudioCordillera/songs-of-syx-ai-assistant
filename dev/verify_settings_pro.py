"""Narrow extra evidence for the explicitly paid native configured-settings question."""
import json,re,sqlite3
from syx_chat import Conversation


def check_events(events,snapshot):
    rows=snapshot['domains']['settings']['data']['configured_options']['data']['rows']
    expected=next(r['configured_steps'] for r in rows if r['setting_id']=='audio_master')
    selections=[]
    for kind,payload in events:
        if kind!='tool' or payload.get('name')!='select_game_state':continue
        result=Conversation._status(payload['result'])
        if result.get('state',{}).get('session_id')!=snapshot['session_id']:continue
        queries=payload.get('arguments',{}).get('spec',{}).get('queries',[])
        for query,group in zip(queries,result.get('results',[])):
            if query.get('source')!={'domain':'settings','path':'/configured_options/data/rows'}:continue
            if query.get('where')!={'eq':[{'field':'/setting_id'},'audio_master']}:continue
            if query.get('select',{}).get('steps')!={'field':'/configured_steps'}:continue
            selected=group.get('rows',[])
            if len(selected)==1 and type(selected[0].get('steps')) is int and selected[0]['steps']==expected:
                selections.append(True)
    assert selections,'No exact-source native-session audio-step selection established'
    final='\n'.join(p['text'] for kind,p in events if kind=='assistant' and p.get('completed')).lower()
    assert re.search(r'quantiz|truncat|round|step',final)
    assert re.search(r'cannot|can.t|not necessarily|does not|doesn.t|not prove',final)
    assert re.search(r'mut|silen|audib|gain',final)
    return {'native_session_settings_selection':True,'steps_match_retained_fixture':True,
        'zero_step_caveat_text_present':True,'actual_provider_settings_question':True,
        'limits':['Settings source/session and configured UI value compared with the retained first-answer observation; not a cross-tick transaction or actual audio test.',
                  'Text checks establish caveat terms, not comprehensive semantic correctness or all advice quality.']}


def verify_settings(state,history):
    db=sqlite3.connect((history/'history.sqlite3').resolve().as_uri()+'?mode=ro',uri=True)
    try:events=[(k,json.loads(p)) for k,p in db.execute('SELECT kind,payload FROM events ORDER BY sequence')]
    finally:db.close()
    return check_events(events,json.loads((state/'first-answer-observation.json').read_text()))
