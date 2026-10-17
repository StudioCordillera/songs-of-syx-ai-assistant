"""Bounded structured queries over one validated, immutable game snapshot.

No SQL, eval, Python expressions, file paths or Java method calls are accepted.
"""
from __future__ import annotations
import json
import re
from collections import defaultdict
from functools import cmp_to_key
from typing import Any

MAX_ROWS = 10000
MAX_WORK = 200000
MAX_RESULT = 65536


def pointer(value, path: str):
    if path == '':
        return value
    if not isinstance(path, str) or not path.startswith('/') or len(path)>1000 or re.search(r'~(?![01])', path):
        raise ValueError('Expected an RFC 6901 pointer')
    for token in path[1:].split('/'):
        token = token.replace('~1', '/').replace('~0', '~')
        if isinstance(value, dict) and token in value:
            value = value[token]
        elif isinstance(value, list) and token.isdigit() and int(token)<len(value):
            value = value[int(token)]
        else:
            raise ValueError(f'Field does not exist: {path}')
    return value


def keys(value, allowed, label):
    if not isinstance(value, dict) or set(value)-set(allowed):
        raise ValueError(f'Invalid {label} fields')


class QueryEngine:
    def __init__(self, snapshot):
        self.snapshot = snapshot
        self.work = MAX_WORK

    def spend(self, amount=1):
        self.work -= amount
        if self.work < 0:
            raise ValueError('Query work budget exceeded; narrow the selection')

    def expression(self, spec, row, depth=0):
        self.spend()
        if depth>16:
            raise ValueError('Expression too deeply nested')
        if not isinstance(spec, dict):
            return spec
        if len(spec)!=1:
            raise ValueError('An expression must have exactly one operator')
        op, args = next(iter(spec.items()))
        if op=='field':
            return pointer(row, args)
        if op=='literal':
            return args
        if op=='context':
            return pointer(self.snapshot.ui_context,args)
        if op in {'and','or'}:
            if not isinstance(args,list) or not 1<=len(args)<=20:
                raise ValueError('and/or require 1..20 conditions')
            if op=='and': return all(self.expression(a,row,depth+1) for a in args)
            return any(self.expression(a,row,depth+1) for a in args)
        if op=='not': return not self.expression(args,row,depth+1)
        if op=='is_null': return self.expression(args,row,depth+1) is None
        if op not in {'eq','ne','lt','lte','gt','gte','in','contains','add','subtract','multiply','divide'}:
            raise ValueError('Unknown expression operator: '+op)
        if not isinstance(args,list) or len(args)!=2:
            raise ValueError(op+' requires two operands')
        a,b=(self.expression(x,row,depth+1) for x in args)
        if op=='eq': return a==b
        if op=='ne': return a!=b
        if op=='in': return a in b if isinstance(b,(list,str)) else False
        if op=='contains': return b in a if isinstance(a,(list,str)) else False
        if a is None or b is None:
            return None
        if op in {'add','subtract','multiply','divide'}:
            if type(a) not in (int,float) or type(b) not in (int,float):
                raise ValueError('Arithmetic requires numbers')
            if op=='add': return a+b
            if op=='subtract': return a-b
            if op=='multiply': return a*b
            return a/b if b!=0 else None
        try:
            if op=='lt': return a<b
            if op=='lte': return a<=b
            if op=='gt': return a>b
            if op=='gte': return a>=b
        except TypeError as exc:
            raise ValueError('Comparison operands have incompatible types') from exc

    def source(self, spec):
        keys(spec, {'domain','path'}, 'source')
        domain = self.snapshot.domains.get(spec.get('domain'))
        if domain is None or domain.coverage=='unavailable':
            raise ValueError('Requested domain is unavailable')
        value = pointer(domain.data, spec.get('path',''))
        rows = value if isinstance(value,list) else [value]
        if len(rows)>MAX_ROWS:
            raise ValueError('Source exceeds row budget; use a more specific source')
        self.spend(len(rows))
        return rows

    def source_metadata(self, spec):
        domain=self.snapshot.domains[spec['domain']]
        return {'domain':spec['domain'],'path':spec.get('path',''),
                'coverage':domain.coverage,'scope':domain.scope}

    def query(self, spec):
        keys(spec, {'name','source','where','joins','select','group_by','aggregates','sort','offset','limit'}, 'query')
        rows = self.source(spec['source'])
        source_metadata=[self.source_metadata(spec['source'])]
        joins = spec.get('joins',[])
        if not isinstance(joins,list) or len(joins)>3:
            raise ValueError('At most three joins are supported')
        for join in joins:
            keys(join, {'source','left_key','right_key','as','kind'}, 'join')
            alias=join.get('as')
            if not isinstance(alias,str) or not alias or len(alias)>80:
                raise ValueError('A join requires an alias')
            kind=join.get('kind','inner')
            if kind not in {'inner','left'}: raise ValueError('Join kind must be inner or left')
            index=defaultdict(list)
            right_rows=self.source(join['source'])
            source_metadata.append(self.source_metadata(join['source']))
            for right in right_rows:
                key=pointer(right,join['right_key'])
                if isinstance(key,(list,dict)): raise ValueError('Join keys must be scalar')
                if key is not None: index[(type(key).__name__,key)].append(right)
            expanded=[]
            for left in rows:
                if not isinstance(left,dict) or alias in left:
                    raise ValueError('Join requires objects and a non-conflicting alias')
                key=pointer(left,join['left_key'])
                if isinstance(key,(list,dict)): raise ValueError('Join keys must be scalar')
                matches=index.get((type(key).__name__,key),[]) if key is not None else []
                for right in matches or ([None] if kind=='left' else []):
                    expanded.append({**left,alias:right}); self.spend()
                    if len(expanded)>MAX_ROWS: raise ValueError('Join result exceeds row budget')
            rows=expanded
        if 'where' in spec:
            rows=[r for r in rows if self.expression(spec['where'],r)]
        if 'group_by' in spec or 'aggregates' in spec:
            if 'select' in spec: raise ValueError('Group queries use group_by/aggregates instead of select')
            group_by=spec.get('group_by',{})
            aggregates=spec.get('aggregates',{})
            if not isinstance(group_by,dict) or not isinstance(aggregates,dict) or not aggregates:
                raise ValueError('Grouped queries require named aggregates')
            if set(group_by)&set(aggregates): raise ValueError('Group and aggregate aliases must be distinct')
            groups={}
            for row in rows:
                fields={k:self.expression(v,row) for k,v in group_by.items()}
                key=json.dumps(fields,sort_keys=True)
                groups.setdefault(key,(fields,[]))[1].append(row)
            if not group_by and not groups: groups['{}']=({},[])
            result=[]
            for fields, members in groups.values():
                result_row=dict(fields)
                for name,agg in aggregates.items():
                    keys(agg, {'op','value'}, 'aggregate')
                    op=agg.get('op')
                    if op=='count': value=len(members)
                    else:
                        if op not in {'sum','avg','min','max'}: raise ValueError('Unknown aggregate')
                        values=[self.expression(agg['value'],r) for r in members]
                        values=[v for v in values if v is not None]
                        if any(type(v) not in (int,float) for v in values): raise ValueError('Numeric aggregate requires numbers')
                        if not values: value=None
                        elif op=='sum': value=sum(values)
                        elif op=='avg': value=sum(values)/len(values)
                        elif op=='min': value=min(values)
                        else: value=max(values)
                    result_row[name]=value
                result.append(result_row)
            rows=result
        elif 'select' in spec:
            selection=spec['select']
            if not isinstance(selection,dict) or not 1<=len(selection)<=50:
                raise ValueError('select requires 1..50 named expressions')
            rows=[{k:self.expression(v,row) for k,v in selection.items()} for row in rows]
        ordering=spec.get('sort',[])
        if not isinstance(ordering,list) or len(ordering)>5: raise ValueError('At most five sort keys')
        for order in ordering:
            keys(order, {'field','direction'}, 'sort')
            if order.get('direction','asc') not in {'asc','desc'}: raise ValueError('Invalid sort direction')
        def compare(a,b):
            self.spend()
            for order in ordering:
                av,bv=pointer(a,order['field']),pointer(b,order['field'])
                if av is None and bv is None: continue
                if av is None: return 1
                if bv is None: return -1
                try: result=(av>bv)-(av<bv)
                except TypeError as exc: raise ValueError('Sort fields require comparable values') from exc
                if result: return -result if order.get('direction')=='desc' else result
            return 0
        if ordering: rows=sorted(rows,key=cmp_to_key(compare))
        offset,limit=spec.get('offset',0),spec.get('limit',50)
        if type(offset) is not int or offset<0 or type(limit) is not int or not 1<=limit<=100:
            raise ValueError('Offset must be nonnegative; limit must be 1..100')
        total=len(rows)
        return {'name':spec.get('name'), 'rows':rows[offset:offset+limit], 'matched_total':total,
                'next_offset':offset+limit if offset+limit<total else None,
                'source_coverage':self.snapshot.domains[spec['source']['domain']].coverage,
                'source_scope':self.snapshot.domains[spec['source']['domain']].scope,
                'sources':source_metadata,'mixed_scopes':len({s['scope'] for s in source_metadata if s['scope'] is not None})>1}

    def execute(self, spec):
        if len(json.dumps(spec).encode())>32768: raise ValueError('Query specification exceeds 32 KiB')
        keys(spec, {'queries','expected_snapshot_id','include_ui_context'}, 'query batch')
        if type(spec.get('include_ui_context',False)) is not bool: raise ValueError('include_ui_context must be a boolean')
        queries=spec.get('queries')
        if not isinstance(queries,list) or not 1<=len(queries)<=10: raise ValueError('Provide 1..10 queries')
        expected=spec.get('expected_snapshot_id')
        if expected is not None and expected!=self.snapshot.snapshot_id: raise ValueError('Snapshot changed; retry with current state')
        try:
            results=[self.query(q) for q in queries]
            encoded=json.dumps(results, allow_nan=False).encode()
        except (KeyError, TypeError, OverflowError) as exc:
            raise ValueError('Missing or invalid query operand: '+str(exc)) from exc
        if len(encoded)>MAX_RESULT: raise ValueError('Result exceeds 64 KiB; project fewer fields or lower the limit')
        return results


def describe(value, path='', result=None, budget=300):
    """Discover observed shapes without returning every row of game data."""
    result=[] if result is None else result
    if len(result)>=budget: return result
    kind='null' if value is None else 'boolean' if isinstance(value,bool) else 'number' if isinstance(value,(int,float)) else 'string' if isinstance(value,str) else 'array' if isinstance(value,list) else 'object'
    result.append({'path':path,'type':kind,**({'length':len(value)} if isinstance(value,list) else {})})
    if isinstance(value,dict):
        for k,v in value.items(): describe(v,path+'/'+k.replace('~','~0').replace('/','~1'),result,budget)
    elif isinstance(value,list) and value:
        describe(value[0],path+'/*',result,budget)
    return result

QUERY_HELP = {
    "access_boundary": "Read-only typed public game API exports via SCRIPT. No private fields, screenshots, input or OS automation. Public mappings are source-verified, not all individually documented. Partial UI context is available through get_game_ui_context; get_game_api_support explains evidence and gaps.",
    "workflow": ["game_status", "describe_game_fields(domain)", "select_game_state(spec)"],
    "batch": {"queries": "1..10 query objects", "expected_snapshot_id": "optional snapshot pin", "include_ui_context": "optional boolean; return UI context from the same snapshot"},
    "query": {"source": {"domain": "domain name", "path": "JSON pointer to rows"},
        "where": "expression", "select": "alias -> expression", "joins": "up to 3 source/left_key/right_key/as/kind joins",
        "group_by": "alias -> expression (instead of select)", "aggregates": "alias -> {op: count|sum|avg|min|max, value: expression}",
        "sort": [{"field":"pointer in projected result", "direction":"asc|desc"}], "offset":0,"limit":"1..100"},
    "expressions": {"field":"JSON pointer into row", "context":"JSON pointer into this snapshot UI context", "literal":"any JSON value", "binary_operators":
        "eq ne lt lte gt gte in contains add subtract multiply divide: [left,right]",
        "logical":"and/or: [expressions]; not/is_null: expression", "constants":"scalars can be used directly"},
    "example": {"queries":[{"source":{"domain":"resources","path":"/stockpiles"},
        "select":{"stored":{"field":"/stockpile_stored"}},"sort":[{"field":"/stored","direction":"asc"}],"limit":5}]},
    "limits":"10k intermediate rows, 200k expression work, 32 KiB specification, 64 KiB response",
    "evidence":"search_game_references: installed help text, version/mods and origin. search_guidance: reviewed external excerpts, authority filter and citation URLs. Unknown/mismatched versions require verification.",
    "semantics":"Missing fields error; null stays null; division by zero returns null; aggregates ignore null; empty sum/avg/min/max null; count zero. All collectors currently partial. No raw field exploration or UI control is exposed. Inspect scene metadata and each source scope; battlefield observations differ from campaign ledgers."
}
