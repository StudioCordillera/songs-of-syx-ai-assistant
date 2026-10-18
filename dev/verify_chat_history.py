"""Verify a completed isolated shared-provider test without making inference requests.

Reports metadata only, never raw answers, game values, credentials or private reasoning.
"""
import argparse
import json
from pathlib import Path
import re
import sqlite3

from syx_chat import Conversation


def verify(directory):
    path=Path(directory).resolve()/'history.sqlite3'
    db=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)
    results={}
    try:
        for provider,route in [('deepseek','api'),('claude','subscription')]:
            chats=db.execute('SELECT chat_id FROM chats WHERE provider=? AND route=?',(provider,route)).fetchall()
            assert len(chats)==1,'Expected one isolated chat for each route'
            cid=chats[0][0]
            statuses=db.execute('SELECT status FROM turns WHERE chat_id=? ORDER BY rowid',(cid,)).fetchall()
            assert statuses==[('completed',),('completed',)],'Both provider turns must complete'
            events=[(kind,json.loads(raw)) for kind,raw in db.execute('SELECT kind,payload FROM events WHERE chat_id=? ORDER BY sequence',(cid,))]
            rows=[];urls=set();sources=set();tools=set();ids=False
            for kind,payload in events:
                assert payload['provider']==provider and payload['route']==route
                if kind=='assistant' and payload.get('tool_calls'):ids|=all(bool(c.get('id')) for c in payload['tool_calls'])
                if kind!='tool':continue
                result=payload['result']
                if result.get('isError') or result.get('error'):continue
                tools.add(payload['name']);data=Conversation._status(result)
                if payload['name']=='select_game_state':rows.extend(len(group.get('rows',[])) for group in data.get('results',[]))
                if payload['name']=='search_guidance':
                    for source in data.get('results',[]):urls.add(source['url']);sources.add(source['id'])
            final='\n'.join(p['text'] for kind,p in events if kind=='assistant' and p.get('completed'))
            cited={u.rstrip('.,;:!?') for u in re.findall(r'https://[^\s<>`\)\]]+',final)}
            assert 3 in rows and sources and ids,'Successful selective data, guidance and tool IDs are required'
            assert cited and cited<=urls,'Every external URL in the answer must match retrieved guidance'
            results[provider]=dict(route=route,completed_turns=2,successful_tools=sorted(tools),select_result_row_counts=rows,
                guidance_source_ids=sorted(sources),external_urls_match_retrieved_sources=True)
        assert db.execute('SELECT count(*) FROM chats').fetchone()[0]==2,'Provider histories must be separate'
        return {'passed':True,'providers':results}
    finally:db.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--history-dir',type=Path,required=True)
    print(json.dumps(verify(parser.parse_args().history_dir),indent=2))
