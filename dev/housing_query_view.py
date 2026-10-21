"""Unshipped bounded view over detached HousingObservation JSON; no game/API or file access."""
from copy import deepcopy
import json

SCOPE='instantiated_city_home_records'
RELATION_SCOPE='instantiated_city_recorded_home_assignments'
MAX_RELATIONS=10000
MAX_VIEW_BYTES=2*1024*1024
DIAGNOSTICS=('room_slots_scanned','room_map_size','scan_limit','room_scan_complete',
             'failed_room_reads','failed_rosters','truncated_rosters')

DEFINITIONS={
 'home_records':{
   'contract':'Songs of Syx 0.71.44 public shipped-source/binary verification, not separately documented stable housing contracts.',
   'source':'HomeInstance/ChamberInstance fixed HOME getters; HOUSING_BOUNDARY_REVIEW.json',
   'room_id':'Current reusable room slot, unique only among these observed rows; not permanent identity or UI selection.',
   'capacity_configured':'Reported per-home configured capacity. No capacity-minus-assignment eligibility/vacancy claim.',
   'occupants_reported':'Ordinary home: stored assignment count. Chamber: zero/one after resolving its recorded entity ID. A resolved zero does not establish the private raw ID is zero.',
   'odd_occupants_stored':'Ordinary stored no-employment accounting bucket, not a current unemployment census; null for chambers.',
   'service_tile_x/service_tile_y':'Home service/door point in city tile coordinates, not resident physical position or current selection.',
   'isolation_reported':'Ordinary unsigned eight-bit fraction; chamber conditional parent-room value. Not full housing quality or a fresh environment computation.',
   'occupant_roster':'Recorded/resolved IDs, maximum 64 per observed home. Unavailable IDs are null, not an empty roster. Truncation/failures stay explicit.',
 },
 'home_assignments':{
   'source':'Pure bounded extraction of the same detached home roster IDs, never another game read.',
   'room_id':'Join home_records/data/rooms.room_id only within this snapshot/session; ID reuse invalidates cross-observation identity assumptions.',
   'resident_id':'Copied public Humanoid.id from the recorded/resolved roster. Entity IDs can be reused; not permanent person identity.',
   'roster_index':'Zero-based position in this observed roster; not a stable assignment identity.',
   'meaning':'Recorded home relationship only; not physical presence, sleeping, reachability, effective eligibility or proof a cached entity prefix contains every resident.',
   'limits':'At most 10000 relationship rows. Each home roster is added as an entire batch or omitted when the relation bound is exceeded. Failed/truncated source rosters and incomplete room scans qualify absence.',
 },
 'ordinary_home_cohort_ledger':{
   'source':'ROOM_HOME.total/used(HGROUP), HGROUP fixed public identity keys.',
   'group_id/class_id/race_id':'Ordinary citizen/slave race cohort keys; nobles are separate. Join by keys, never translated labels.',
   'capacity_reported_raw/used_reported_raw':'Stored eligibility-weighted accounting ledgers. An empty home may contribute to multiple cohorts.',
   'null_group_totals':'The source null-group sums are not unique physical bed counts, effective vacancy or per-person eligibility. Exact counter age is unknown.',
 },
}


def build_view(candidate, row_limit=MAX_RELATIONS):
    """Fail closed on malformed detached structure; preserve explicit source failures and caps."""
    if type(row_limit) is not int or not 1<=row_limit<=MAX_RELATIONS:
        raise ValueError('Relationship row limit must be 1..10000')
    if not isinstance(candidate,dict) or candidate.get('scope')!=SCOPE or type(candidate.get('available')) is not bool:
        raise ValueError('Expected fixed detached housing observation')
    if not candidate['available']:
        if candidate.get('coverage')!='unavailable' or candidate.get('data') is not None:
            raise ValueError('Unavailable housing must have null data')
        relation={'available':False,'coverage':'unavailable','scope':RELATION_SCOPE,'data':None,
                  'reason':candidate.get('reason','Housing observation unavailable')}
    else:
        if candidate.get('coverage')!='partial' or not isinstance(candidate.get('data'),dict):
            raise ValueError('Expected partial housing data')
        data=candidate['data'];rooms=data.get('rooms')
        if not isinstance(rooms,list) or len(rooms)>1000:raise ValueError('Room row budget exceeded')
        for key in DIAGNOSTICS:
            v=data.get(key)
            if key=='room_scan_complete':
                if type(v) is not bool:raise ValueError('Invalid scan completeness')
            elif type(v) is not int or v<0:raise ValueError('Invalid housing diagnostic')
        if not 1<=data['scan_limit']<=10000 or not 0<=data['room_slots_scanned']<=min(data['room_map_size'],data['scan_limit']):
            raise ValueError('Invalid scan extent')
        if data['room_scan_complete']!=(data['room_slots_scanned']==data['room_map_size']):
            raise ValueError('Scan completeness disagrees with extent')
        if type(data.get('row_limit')) is not int or not 1<=data['row_limit']<=1000 or len(rooms)>data['row_limit']:
            raise ValueError('Invalid home row bound')
        seen=set();batches=[]
        for room in rooms:
            if not isinstance(room,dict) or type(room.get('room_id')) is not int or room['room_id'] in seen:
                raise ValueError('Invalid or duplicate home ID')
            seen.add(room['room_id'])
            if room.get('kind') not in ('ordinary_home','noble_chamber') or type(room.get('occupants_reported')) is not int:
                raise ValueError('Unsupported detached home kind/count')
            roster=room.get('occupant_roster')
            if not isinstance(roster,dict) or type(roster.get('available')) is not bool:raise ValueError('Missing roster coverage')
            if not roster['available']:
                if roster.get('coverage')!='unavailable' or roster.get('ids') is not None:raise ValueError('Unavailable roster must have null IDs')
                batches.append(None);continue
            ids=roster.get('ids');count=room['occupants_reported']
            if not isinstance(ids,list) or len(ids)>64 or any(type(i) is not int for i in ids) or count<0 or len(ids)!=min(count,64):
                raise ValueError('Invalid detached roster IDs/count')
            if roster.get('coverage')!='partial' or type(roster.get('truncated')) is not bool or roster['truncated']!=(count>64):
                raise ValueError('Invalid roster truncation')
            batches.append([{'room_id':room['room_id'],'resident_id':rid,'roster_index':i} for i,rid in enumerate(ids)])
        if data['failed_rosters']<sum(batch is None for batch in batches):
            raise ValueError('Roster failure diagnostics undercount observed failures')
        if data['truncated_rosters']<sum(bool(r['occupant_roster'].get('truncated')) for r in rooms if r['occupant_roster']['available']):
            raise ValueError('Roster truncation diagnostics undercount observed caps')
        links=[];visited=0;bounded=False
        for batch in batches:
            visited+=1
            if batch is None:continue
            if len(links)+len(batch)>row_limit:bounded=True;break
            links.extend(batch)
        relation={'available':True,'coverage':'partial','scope':RELATION_SCOPE,
                  'data':{**{k:data[k] for k in DIAGNOSTICS},'rows':links,'row_limit':row_limit,
                          'scanned_rooms':visited,'truncated':bounded or not data['room_scan_complete'] or data['truncated_rosters']>0},
                  'reason':'Same-observation recorded/resolved home links; atomic per-home batches. Incomplete room scans, failed rooms/rosters and caps qualify missing relationships; no physical presence or permanent identity.'}
    result={'home_records':deepcopy(candidate),'home_assignments':relation,'field_definitions':deepcopy(DEFINITIONS)}
    if len(json.dumps(result,allow_nan=False).encode())>MAX_VIEW_BYTES:raise ValueError('Housing view exceeds byte budget')
    return result
