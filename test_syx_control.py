import json
from pathlib import Path
import threading
import time
import uuid
from urllib.parse import unquote

import pytest
from syx_control import GameControl

class TestAdvisor:
    __test__ = False
    def __init__(self, root, live=True):
        self.snapshot_path = root / 'snapshot.json'
        self.live = live
    def status(self):
        return {'live': self.live, 'session_id': 'session-test'}


def test_control_requires_live_game(tmp_path):
    c = GameControl(TestAdvisor(tmp_path, False), timeout=.1)
    with pytest.raises(ValueError, match='live game'):
        c.request('observe')
    assert not c.directory.exists()


def test_timeout_does_not_claim_success(tmp_path):
    c = GameControl(TestAdvisor(tmp_path), timeout=.05)
    with pytest.raises(TimeoutError, match='uncertain'):
        c.request('key', value='SPACE')


def test_action_receipt_retries_and_conflicting_parameters(tmp_path):
    c = GameControl(TestAdvisor(tmp_path), timeout=1)
    id = str(uuid.uuid4())
    calls = []
    def game():
        p=c.directory / (id + '.req')
        for _ in range(200):
            if p.exists(): break
            time.sleep(.005)
        request={k: unquote(v) for k,v in (l.split('=',1) for l in p.read_text().splitlines())}
        calls.append(request)
        p.rename(c.directory / (id + '.claimed'))
        (c.directory / (id + '.json')).write_text(json.dumps({'ok':True,'action_id':id}))
    responder=threading.Thread(target=game)
    responder.start()
    assert c.request('key', action_id=id, value='SPACE')['ok']
    responder.join()
    assert c.request('key', action_id=id, value='SPACE')['ok']
    assert len(calls)==1
    with pytest.raises(ValueError, match='different parameters'):
        c.request('key', action_id=id, value='ENTER')


def test_refuses_arbitrary_image_paths(tmp_path):
    c=GameControl(TestAdvisor(tmp_path))
    id=str(uuid.uuid4())
    with pytest.raises(ValueError, match='image name'):
        c.content({'action_id':id,'image':'../../private.png'})


def test_stop_can_be_requested_without_fresh_snapshot(tmp_path):
    c=GameControl(TestAdvisor(tmp_path,False), timeout=.02)
    with pytest.raises(TimeoutError): c.request('stop')
    assert 'operation=stop' in next(c.directory.glob('*.req')).read_text()


def test_input_bounds_before_mailbox(tmp_path):
    c=GameControl(TestAdvisor(tmp_path))
    params=('session','grant','frame',str(uuid.uuid4()))
    for op,value in [('scroll','100'),('click','middle'),('text','x'*65)]:
        with pytest.raises(ValueError): c.action(op,*params,value=value)
    assert not c.directory.exists()


def test_seed_sources_preserve_version_and_authority(tmp_path):
    from syx_knowledge import install_seed
    from syx_mcp import Advisor
    assert install_seed(tmp_path)==2
    assert install_seed(tmp_path)==2
    a=Advisor(tmp_path/'snapshot.json',tmp_path/'corpus.json')
    guide=a.search('farms food', '0.71.44', authority='community')['results'][0]
    assert guide['authority']=='community'
    assert guide['version_compatibility']=='family_match'
    assert guide['version_notes']
    forum=a.search('eatery overlay','0.71.44')['results'][0]
    assert forum['authority']=='developer'
    assert forum['version_compatibility']=='unknown'
