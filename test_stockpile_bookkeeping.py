"""Query the authored reservation example with distinct counters and incomplete coverage."""
import json
from pathlib import Path
import pytest
from syx_mcp import Snapshot
from syx_query import QueryEngine


def fixture():
    raw=json.loads(Path('snapshot.example.json').read_text())
    raw['domains']['resources']={'coverage':'partial','data':{
        'stockpiles':[{'id':'grain','owned':800},{'id':'wood','owned':90}],
        'stockpile_bookkeeping':{'coverage':'partial','rows':[
            {'resource_id':'grain','stored_raw':100,'reserved_stored_raw':7,'reserved_incoming_raw':21,'capacity_raw':200,'assigned_crates':4},
            {'resource_id':'wood','stored_raw':0,'reserved_stored_raw':0,'reserved_incoming_raw':0,'capacity_raw':0,'assigned_crates':0}],
            'truncated':False,'failed_resources':0,'resource_limit':1000,'row_limit':1000}}}
    return raw


def test_authored_stockpile_query_preserves_distinct_reservations_and_owned_scope():
    raw=fixture();spec=json.loads(Path('stockpile-query-example.json').read_text())
    # UI wrapper is an Advisor concern; engine gets the query list only.
    result=QueryEngine(Snapshot.model_validate(raw)).execute({'queries':spec['queries']})
    assert result[0]['rows']==[{'resource':'grain','stored':100,'reserved_stored':7,'reserved_incoming':21,
        'capacity':200,'assigned_crates':4,'broader_owned':800}]
    assert result[0]['matched_total']==1


def test_stockpile_ancestor_failures_and_caps_survive_authored_join():
    raw=fixture();book=raw['domains']['resources']['data']['stockpile_bookkeeping']
    book.update(truncated=True,failed_resources=2)
    spec=json.loads(Path('stockpile-query-example.json').read_text())
    result=QueryEngine(Snapshot.model_validate(raw)).execute({'queries':spec['queries']})
    diag=result[0]['sources'][0]['collection_diagnostics']
    assert any(d['path']=='/stockpile_bookkeeping' and d['truncated'] and d['failed_resources']==2 for d in diag)
    assert result[0]['matched_total']==1  # Exported rows only; flags qualify the apparent total.


def test_unavailable_stockpile_count_is_refused_instead_of_zero():
    raw=fixture();raw['domains']['resources']['data']['stockpile_bookkeeping']={'coverage':'unavailable','rows':None}
    spec={'queries':[{'source':{'domain':'resources','path':'/stockpile_bookkeeping/rows'},'aggregates':{'n':{'op':'count'}}}]}
    with pytest.raises(ValueError,match='observation is unavailable'):
        QueryEngine(Snapshot.model_validate(raw)).execute(spec)
