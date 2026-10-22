"""Paid evidence verifier refuses missing/wrong-session/wrong-source/wrong-value rows; no inference."""
import pytest
from dev.verify_settings_pro import check_events


def fixture():
    snapshot={'session_id':'synthetic-native-session','domains':{'settings':{'data':{'configured_options':{'data':{'rows':[{'setting_id':'audio_master','configured_steps':14}]}}}}}}
    result={'structuredContent':{'state':{'session_id':snapshot['session_id']},'results':[{'rows':[{'steps':14}]}]}}
    events=[('tool',{'name':'select_game_state','arguments':{'spec':{'queries':[{'source':{'domain':'settings','path':'/configured_options/data/rows'},'where':{'eq':[{'field':'/setting_id'},'audio_master']},'select':{'steps':{'field':'/configured_steps'}}}]}},'result':result}),('assistant',{'completed':True,'text':'Quantized steps cannot prove actual mute.'})]
    return events,snapshot


def test_settings_paid_evidence_validates_without_provider():
    events,snapshot=fixture()
    assert check_events(events,snapshot)['native_session_settings_selection']


@pytest.mark.parametrize('fault',['missing','session','source','value','boolean','wrong_setting','unfiltered','caveat'])
def test_settings_paid_evidence_refuses_unestablished_claims(fault):
    events,snapshot=fixture()
    payload=events[0][1]
    if fault=='missing':events.pop(0)
    elif fault=='session':payload['result']['structuredContent']['state']['session_id']='other'
    elif fault=='source':payload['arguments']['spec']['queries'][0]['source']['path']='/elsewhere'
    elif fault=='value':payload['result']['structuredContent']['results'][0]['rows'][0]['steps']=0
    elif fault=='boolean':payload['result']['structuredContent']['results'][0]['rows'][0]['steps']=True
    elif fault=='wrong_setting':payload['arguments']['spec']['queries'][0]['where']['eq'][1]='audio_music'
    elif fault=='unfiltered':payload['arguments']['spec']['queries'][0].pop('where')
    else:events[1][1]['text']='Everything is silent.'
    with pytest.raises(AssertionError):check_events(events,snapshot)
