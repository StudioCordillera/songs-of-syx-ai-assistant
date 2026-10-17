package syx.assistant;

import java.time.Instant;
import java.nio.charset.StandardCharsets;
import java.util.*;
import game.GAME;
import game.VERSION;
import settlement.entity.ENTITY;
import settlement.entity.humanoid.Humanoid;
import settlement.main.SETT;
import settlement.stats.STATS;
import settlement.stats.stat.STAT;
import static syx.assistant.StateCollector.object;

/** Fixed read-only protocol. No arbitrary field names, expressions, methods or paths. */
public final class EntityReadRequest {
    public final String id, session;
    final long expires;
    final int cursor, scanLimit, limit;
    final boolean capture;
    final Set<Integer> ids, statIds;
    final Set<String> fields;
    final String race, clas, type;
    final int[] bounds;
    final List<Filter> filters;
    private static final Set<String> KEYS=Set.of("protocol","request_id","session","expires","cursor","scan_limit","limit","ids","race","class","type","bounds","fields","stats","filters");
    private static final Set<String> FIELDS=Set.of("id","entity_type","tile_x","tile_y","race_id","class_id","humanoid_type_id","stats","relationships");
    private static final Set<String> OPS=Set.of("eq","ne","lt","lte","gt","gte");

    private static int integer(String text,int low,int high) {
        if(!text.matches("-?(0|[1-9][0-9]*)"))throw new IllegalArgumentException("Invalid integer");
        int n=Integer.parseInt(text);if(n<low || n>high)throw new IllegalArgumentException("Integer out of range");return n;
    }
    private static String uuid(String text) {
        if(!UUID.fromString(text).toString().equals(text))throw new IllegalArgumentException("Noncanonical UUID");return text;
    }
    private static Set<Integer> integers(String text,int maximum,int low,int high) {
        Set<Integer> result=new LinkedHashSet<>();
        if(!text.isEmpty()) for(String part:text.split(",",-1)) {
            if(!result.add(integer(part,low,high)))throw new IllegalArgumentException("Duplicate integer");
        }
        if(result.size()>maximum)throw new IllegalArgumentException("Too many integers");return Collections.unmodifiableSet(result);
    }
    private static String decoded(String text) {
        if(text.isEmpty())return null;
        byte[] bytes=Base64.getUrlDecoder().decode(text);
        String result=new String(bytes,StandardCharsets.UTF_8);
        if(result.codePointCount(0,result.length())>100 || result.isEmpty() || !Base64.getUrlEncoder().withoutPadding().encodeToString(result.getBytes(StandardCharsets.UTF_8)).equals(text))
            throw new IllegalArgumentException("Invalid filter string");
        return result;
    }
    public static EntityReadRequest parse(String text) {
        if(text.length()>8192 || !text.endsWith("\n"))throw new IllegalArgumentException("Invalid request size/framing");
        Map<String,String> parts=new HashMap<>();
        for(String line:text.split("\n")) {
            int equals=line.indexOf('=');if(equals<1)throw new IllegalArgumentException("Invalid request line");
            String key=line.substring(0,equals);
            if(!KEYS.contains(key) || parts.put(key,line.substring(equals+1))!=null)throw new IllegalArgumentException("Unknown or duplicate request field");
        }
        if(!parts.keySet().equals(KEYS) || !Set.of("1","2").contains(parts.get("protocol")))throw new IllegalArgumentException("Unsupported request protocol");
        return new EntityReadRequest(parts);
    }
    private EntityReadRequest(Map<String,String> p) {
        id=uuid(p.get("request_id"));session=uuid(p.get("session"));
        capture="2".equals(p.get("protocol"));
        if(!p.get("expires").matches("[0-9]{13}"))throw new IllegalArgumentException("Invalid deadline");
        expires=Long.parseLong(p.get("expires"));
        if(expires-System.currentTimeMillis()>15000)throw new IllegalArgumentException("Deadline too far ahead");
        cursor=integer(p.get("cursor"),0,Integer.MAX_VALUE);scanLimit=integer(p.get("scan_limit"),1,capture?100000:10000);limit=integer(p.get("limit"),1,capture?2000:100);
        if(capture && cursor!=0)throw new IllegalArgumentException("Capture starts at scene origin; cursor must be zero");
        ids=integers(p.get("ids"),100,Integer.MIN_VALUE,Integer.MAX_VALUE);statIds=integers(p.get("stats"),20,0,100000);
        fields=new LinkedHashSet<>(Arrays.asList(p.get("fields").split(",",-1)));
        if(fields.isEmpty() || !FIELDS.containsAll(fields) || fields.size()!=p.get("fields").split(",",-1).length)throw new IllegalArgumentException("Invalid projection");
        if(fields.contains("stats") && (statIds.isEmpty() || statIds.size()*limit>(capture?4000:100)))throw new IllegalArgumentException("Stat projection exceeds the read mode cell budget");
        if(!fields.contains("stats") && !statIds.isEmpty())throw new IllegalArgumentException("Unused stat projection");
        if(capture && !fields.contains("id"))throw new IllegalArgumentException("Capture requires the id projection");
        race=decoded(p.get("race"));clas=decoded(p.get("class"));type=decoded(p.get("type"));
        if(p.get("bounds").isEmpty())bounds=null;
        else {
            String[] coordinates=p.get("bounds").split(",",-1);if(coordinates.length!=4)throw new IllegalArgumentException("Invalid tile bounds");
            bounds=new int[4];for(int i=0;i<4;i++)bounds[i]=integer(coordinates[i],0,100000);
            if(bounds[0]>=bounds[2] || bounds[1]>=bounds[3])throw new IllegalArgumentException("Empty tile bounds");
        }
        filters=new ArrayList<>();
        if(!p.get("filters").isEmpty())for(String item:p.get("filters").split(",",-1)) {
            String[] f=item.split(":",-1);if(f.length!=3 || !OPS.contains(f[1]))throw new IllegalArgumentException("Invalid stat predicate");
            filters.add(new Filter(integer(f[0],0,100000),f[1],integer(f[2],Integer.MIN_VALUE,Integer.MAX_VALUE)));
        }
        if(filters.size()>4)throw new IllegalArgumentException("At most four stat predicates");
    }
    static final class Filter {
        final int id,value;final String op;
        Filter(int id,String op,int value){this.id=id;this.op=op;this.value=value;}
        boolean matches(int actual) {
            switch(op) {
                case "eq":return actual==value;case "ne":return actual!=value;
                case "lt":return actual<value;case "lte":return actual<=value;
                case "gt":return actual>value;case "gte":return actual>=value;
                default:throw new IllegalArgumentException("Unknown operator");
            }
        }
    }
    public Map<String,Object> error(String actualSession,String reason) {
        return object("request_id",id,"session_id",actualSession,"game_version",VERSION.VERSION_STRING,
            "captured_at",Instant.now().toString(),"available",false,"reason",reason,"data",null);
    }
    /** Called exclusively from the registered GAME.addAfterUpdate observer, never from the file daemon. */
    public Map<String,Object> collect(String actualSession) {
        if(!session.equals(actualSession))return error(actualSession,"Session changed; rediscover game state");
        if(System.currentTimeMillis()>expires)return error(actualSession,"Read request expired");
        if(!SETT.exists())return error(actualSession,"No instantiated settlement scene");
        try {
            Set<Integer> needed=new HashSet<>(statIds);for(Filter f:filters)needed.add(f.id);
            Map<Integer,STAT> stats=new HashMap<>();
            for(STAT stat:STATS.all())if(needed.contains(stat.index())) {
                if(!stat.hasIndu() || stat.indu()==null)throw new IllegalArgumentException("Stat lacks named individual getter: "+stat.index());
                stats.put(stat.index(),stat);
            }
            if(stats.size()!=needed.size())throw new IllegalArgumentException("Unknown stat ID; discover the installed stat catalog first");
            ENTITY[] entities;
            String cursorKind;
            if(ids.isEmpty()){entities=SETT.ENTITIES().getAllEnts();cursorKind="scene_slots";}
            else {
                entities=new ENTITY[ids.size()];int at=0;
                for(Integer entityId:ids)entities[at++]=SETT.ENTITIES().getByID(entityId);
                cursorKind="requested_ids";
            }
            if(cursor>entities.length)throw new IllegalArgumentException("Cursor outside scene array; restart query");
            List<Object> rows=new ArrayList<>();int next=cursor,scanned=0,skipped=0;
            for(;next<entities.length && scanned<scanLimit && (capture || rows.size()<limit);next++,scanned++) {
                ENTITY e=entities[next];if(e==null || e.isRemoved() || (!ids.isEmpty() && !ids.contains(e.id())))continue;
                if(bounds!=null && (e.tc().x()<bounds[0] || e.tc().y()<bounds[1] || e.tc().x()>=bounds[2] || e.tc().y()>=bounds[3]))continue;
                Humanoid h=e instanceof Humanoid?(Humanoid)e:null;
                if((race!=null || clas!=null || type!=null || !filters.isEmpty()) && h==null)continue;
                if(race!=null && !race.equals(h.race().key))continue;
                if(clas!=null && !clas.equals(h.indu().clas().key))continue;
                if(type!=null && !type.equals(h.indu().hType().key))continue;
                boolean matches=true;
                try {for(Filter f:filters)if(!f.matches(stats.get(f.id).indu().get(h.indu()))){matches=false;break;}}
                catch(RuntimeException failure){skipped++;continue;}
                if(!matches)continue;
                if(capture && rows.size()>=limit)throw new IllegalArgumentException("Capture exceeds row bound; narrow selection or raise max_rows up to 2000");
                Map<String,Object> row=new LinkedHashMap<>();
                for(String field:fields)switch(field) {
                    case "id":row.put(field,e.id());break;
                    case "entity_type":row.put(field,e.getClass().getSimpleName());break;
                    case "tile_x":row.put(field,e.tc().x());break;
                    case "tile_y":row.put(field,e.tc().y());break;
                    case "race_id":row.put(field,h==null?null:h.race().key);break;
                    case "class_id":row.put(field,h==null?null:h.indu().clas().key);break;
                    case "humanoid_type_id":row.put(field,h==null?null:h.indu().hType().key);break;
                    case "relationships":row.put(field,h==null?null:StateCollector.personRelationships(h));break;
                    case "stats":
                        List<Object> values=new ArrayList<>();
                        if(h!=null)for(Integer statId:statIds)values.add(StateCollector.individualStat(h,stats.get(statId)));
                        row.put(field,h==null?null:values);break;
                    default:throw new IllegalArgumentException("Unknown field");
                }
                rows.add(row);
            }
            if(capture && next<entities.length)throw new IllegalArgumentException("Capture exceeds scan bound; increase scan_limit up to 100000 or use explicit IDs");
            if(capture && skipped>0)throw new IllegalArgumentException("Capture predicate errors; no complete selection retained");
            return object("observer_phase","GAME.addAfterUpdate","read_mode",capture?"capture":"live_page","request_id",id,"session_id",actualSession,"game_version",VERSION.VERSION_STRING,
                "captured_at",Instant.now().toString(),"tick",Math.max(0,GAME.updateI()),"available",true,
                "scope","instantiated_settlement_scene","coverage","partial","scene",UiContextCollector.scene(),"ui_context",UiContextCollector.collect(),
                "data",object("rows",rows,"scanned_slots",scanned,"array_capacity",entities.length,"cursor_kind",cursorKind,
                    "next_cursor",next<entities.length?next:null,"predicate_errors",skipped),
                "consistency",capture?"Retained DTO from one bounded game update-thread observation. No global transaction or battle-worker synchronization is established.":"One update-thread observation per response. Cursor pages are separate observations over mutable scene slots; IDs/positions may change. Not a pinned multi-page snapshot.",
                "reason","Only fixed public getters and named individual stats; raw stat units are not established. Not every game variable or private AI attribute.");
        } catch(RuntimeException failure) { return error(actualSession,failure.getClass().getSimpleName()+": "+failure.getMessage()); }
    }
}
