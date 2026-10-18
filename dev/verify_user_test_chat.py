"""Verify the isolated Pro player test; publish metadata only."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import re
import sqlite3
from syx_chat import Conversation
from make_user_test import MODULES


def verify(root,state,history,jar):
    db=sqlite3.connect((history/'history.sqlite3').resolve().as_uri()+'?mode=ro',uri=True)
    try:
        assert db.execute('SELECT provider,model,route FROM chats').fetchall()==[('deepseek','deepseek-v4-pro','api')]
        assert db.execute('SELECT status FROM turns ORDER BY rowid').fetchall()==[('completed',),('completed',)]
        events=[(k,json.loads(p)) for k,p in db.execute('SELECT kind,payload FROM events ORDER BY sequence')]
        rows=[];urls=set();tools=set()
        for kind,payload in events:
            if kind!='tool' or payload['result'].get('isError') or payload['result'].get('error'):continue
            tools.add(payload['name']);result=Conversation._status(payload['result'])
            if payload['name']=='select_game_state':rows.extend(len(group.get('rows',[])) for group in result.get('results',[]))
            if payload['name']=='search_guidance':urls.update(s['url'] for s in result.get('results',[]))
        final='\n'.join(p['text'] for kind,p in events if kind=='assistant' and p.get('completed'))
        cited={u.rstrip('.,;:!?') for u in re.findall(r'https://[^\s<>`\)\]]+',final)}
        assert 3 in rows and cited and cited<=urls
        ui=(state/'chat-ui.txt').read_text()
        visible=[base64.b64decode(line[5:]).decode() for line in ui.splitlines() if line.startswith('line=')]
        assert visible and not any(s in '\n'.join(visible) for s in ('Tool:','Tool evidence:','snapshot_id','session_id','"arguments":'))
        gui=json.loads((state/'chat-live-gui-validation.json').read_text());assert gui['passed']
        audit=json.loads((root/'api-audit.json').read_text())
        return {'passed':True,'requested_model':'deepseek-v4-pro','real_provider_round_trip':True,
            'completed_turns':2,'select_result_row_counts':rows,'successful_tools':sorted(tools),
            'cited_urls_match_retrieval':True,'simple_transcript_without_debug_events':True,
            'mod_jar_sha256':hashlib.sha256(jar.read_bytes()).hexdigest(),
            'production_source_sha256':audit['mod_source_sha256'],
            'python_source_sha256':{n+'.py':hashlib.sha256((root/(n+'.py')).read_bytes()).hexdigest() for n in MODULES},
            'limits':['Copied city; native own-widget text/click fixture, not physical keyboard or every screen size.',
                'No complete game-state/all-menu claim. Raw read-only tool evidence remains in the private local history.',
                'Linux user-test bundle; game and Python dependencies must be installed separately.']}
    finally:db.close()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--state-dir',type=Path,required=True);p.add_argument('--history-dir',type=Path,required=True)
    p.add_argument('--mod-jar',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();root=Path(__file__).resolve().parent.parent
    report=verify(root,args.state_dir,args.history_dir,args.mod_jar)
    args.output.write_text(json.dumps(report,indent=2)+'\n');print('Pro player verification passed.')
