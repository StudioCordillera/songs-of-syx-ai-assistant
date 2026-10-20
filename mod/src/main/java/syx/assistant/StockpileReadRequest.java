package syx.assistant;

import java.nio.ByteBuffer;
import java.nio.charset.*;
import java.time.Instant;
import java.util.*;
import game.GAME;
import game.VERSION;
import init.resources.RESOURCE;
import init.resources.RESOURCES;
import settlement.main.SETT;
import settlement.room.infra.stockpile.StockpileInstance;
import static syx.assistant.StateCollector.object;

/** Fixed stored-counter reads. Parsing on the I/O thread binds no live game objects. */
public final class StockpileReadRequest {
    static final Set<String> COUNTERS=Set.of("assigned_crates","stored_raw","capacity_raw","reserved_stored_raw","reserved_incoming_raw");
    static final Set<String> FIELDS=Set.of("assigned_crates","stored_raw","capacity_raw","reserved_stored_raw","reserved_incoming_raw","reference_id");
    static final Set<String> OPS=Set.of("eq","ne","lt","lte","gt","gte");
    static final Set<String> KEYS=Set.of("protocol","request_id","session","expires","rooms","resources","fields","filters","active","cursor","scan_limit","limit");
    final String id,session;final long expires;final List<Integer> roomIds=new ArrayList<>();
    final List<String> resources=new ArrayList<>(),fields=new ArrayList<>();final List<Filter> filters=new ArrayList<>();
    final Boolean active;final int cursor,scanLimit,limit;
    static final class Filter {
        final String field,op;final int value;
        Filter(String field,String op,int value){this.field=field;this.op=op;this.value=value;}
        boolean matches(int n){switch(op){case "eq":return n==value;case "ne":return n!=value;case "lt":return n<value;
            case "lte":return n<=value;case "gt":return n>value;case "gte":return n>=value;default:throw new IllegalArgumentException("Unknown comparison");}}
    }
    static int integer(String s,int min,int max){
        if(!s.matches("0|-?[1-9][0-9]*"))throw new IllegalArgumentException("Canonical integer required");
        int n=Integer.parseInt(s);if(n<min || n>max)throw new IllegalArgumentException("Integer out of range");return n;
    }
    static String uuid(String value){if(!UUID.fromString(value).toString().equals(value))throw new IllegalArgumentException("Canonical UUID required");return value;}
    static String key(String encoded){
        try {
            byte[] bytes=Base64.getUrlDecoder().decode(encoded);
            if(!Base64.getUrlEncoder().withoutPadding().encodeToString(bytes).equals(encoded))throw new IllegalArgumentException();
            String value=StandardCharsets.UTF_8.newDecoder().onMalformedInput(CodingErrorAction.REPORT).onUnmappableCharacter(CodingErrorAction.REPORT).decode(ByteBuffer.wrap(bytes)).toString();
            if(value.isEmpty() || value.length()>100)throw new IllegalArgumentException();return value;
        }catch(Exception error){throw new IllegalArgumentException("Invalid resource key encoding");}
    }
    public static StockpileReadRequest parse(String text){
        if(text.length()>8192)throw new IllegalArgumentException("Stockpile request exceeds 8 KiB");
        for(int i=0;i<text.length();i++)if(text.charAt(i)>127 || text.charAt(i)=='\r')throw new IllegalArgumentException("ASCII LF framing required");
        Map<String,String> p=new HashMap<>();
        String framed=text.endsWith("\n")?text.substring(0,text.length()-1):text;
        for(String line:framed.split("\n",-1)){
            int at=line.indexOf('=');if(at<1)throw new IllegalArgumentException("Invalid request line");
            String k=line.substring(0,at);if(!KEYS.contains(k) || p.put(k,line.substring(at+1))!=null)throw new IllegalArgumentException("Unknown or duplicate request field");
        }
        if(!p.keySet().equals(KEYS) || !"1".equals(p.get("protocol")))throw new IllegalArgumentException("Unsupported stockpile protocol");
        return new StockpileReadRequest(p);
    }
    private StockpileReadRequest(Map<String,String> p){
        id=uuid(p.get("request_id"));session=uuid(p.get("session"));
        if(!p.get("expires").matches("[0-9]{13}"))throw new IllegalArgumentException("Invalid deadline");
        expires=Long.parseLong(p.get("expires"));if(expires-System.currentTimeMillis()>15000)throw new IllegalArgumentException("Deadline too far ahead");
        if(!p.get("rooms").isEmpty())for(String s:p.get("rooms").split(",",-1)){
            int value=integer(s,0,Integer.MAX_VALUE);if(roomIds.contains(value))throw new IllegalArgumentException("Duplicate room ID");roomIds.add(value);
        }
        for(String s:p.get("resources").split(",",-1)){
            String value=key(s);if(resources.contains(value))throw new IllegalArgumentException("Duplicate resource key");resources.add(value);
        }
        if(roomIds.size()>100 || resources.size()>100)throw new IllegalArgumentException("At most 100 room/resource IDs");
        for(String value:p.get("fields").split(",",-1)){
            if(!FIELDS.contains(value) || fields.contains(value))throw new IllegalArgumentException("Invalid projection");fields.add(value);
        }
        if(!p.get("filters").isEmpty())for(String s:p.get("filters").split(",",-1)){
            String[] parts=s.split(":",-1);if(parts.length!=3 || !COUNTERS.contains(parts[0]) || !OPS.contains(parts[1]))throw new IllegalArgumentException("Invalid counter predicate");
            filters.add(new Filter(parts[0],parts[1],integer(parts[2],Integer.MIN_VALUE,Integer.MAX_VALUE)));
        }
        if(filters.size()>4)throw new IllegalArgumentException("At most four counter predicates");
        String a=p.get("active");if(!Set.of("","true","false").contains(a))throw new IllegalArgumentException("Invalid active predicate");active=a.isEmpty()?null:Boolean.valueOf(a);
        cursor=integer(p.get("cursor"),0,Integer.MAX_VALUE);scanLimit=integer(p.get("scan_limit"),1,4096);limit=integer(p.get("limit"),1,100);
    }
    private Map<String,Object> error(String actual,String reason){return object("request_id",id,"session_id",actual,"game_version",VERSION.VERSION_STRING,
        "captured_at",Instant.now().toString(),"available",false,"reason",reason,"data",null);}
    public Map<String,Object> collect(String actual){
        if(!actual.equals(session))return error(actual,"Session changed; rediscover game state");
        if(System.currentTimeMillis()>expires)return error(actual,"Stockpile request expired");
        if(!SETT.exists() || SETT.WORLD_AREA().isBattle || !world.WORLD.GEN().isDone)return error(actual,"No completed instantiated campaign city");
        try {
            if(RESOURCES.ALL().size()>1000)throw new IllegalArgumentException("Resource registry scan bound exceeded");
            Map<String,RESOURCE> bindings=new HashMap<>();
            for(RESOURCE r:RESOURCES.ALL())if(resources.contains(r.key)){
                if(r.index()<0 || r.index()>=RESOURCES.ALL().size() || bindings.put(r.key,r)!=null)throw new IllegalArgumentException("Invalid or ambiguous resource binding");
            }
            if(bindings.size()!=resources.size())throw new IllegalArgumentException("Unknown requested resource key");
            var blueprint=SETT.ROOMS().STOCKPILE;var all=blueprint.all();List<StockpileInstance> explicit=new ArrayList<>();
            for(int ri:roomIds){
                if(ri>=SETT.ROOMS().map.max())throw new IllegalArgumentException("Unknown requested warehouse room");
                var r=SETT.ROOMS().map.getByIndex(ri);
                if(!(r instanceof StockpileInstance) || r.blueprint()!=blueprint)throw new IllegalArgumentException("Requested room is not a current warehouse");
                explicit.add((StockpileInstance)r);
            }
            int count=roomIds.isEmpty()?all.size():explicit.size();long product=(long)count*resources.size();
            if(product>Integer.MAX_VALUE || cursor>product)throw new IllegalArgumentException("Cursor exceeds current requested matrix");
            int area=(int)product,next=cursor,scanned=0,errors=0;List<Object> rows=new ArrayList<>();var tally=blueprint.tally();
            while(next<area && scanned<scanLimit && rows.size()<limit){
                int position=next++;scanned++;
                try {
                    StockpileInstance room=roomIds.isEmpty()?all.get(position/resources.size()):explicit.get(position/resources.size());
                    boolean isActive=room.active();if(active!=null && active.booleanValue()!=isActive)continue;
                    String resource=resources.get(position%resources.size());int ri=bindings.get(resource).index();
                    Map<String,Integer> values=new HashMap<>();
                    values.put("assigned_crates",tally.crates.get(ri,room));values.put("stored_raw",tally.amount.get(ri,room));
                    values.put("capacity_raw",tally.space.get(ri,room));values.put("reserved_stored_raw",tally.amountReserved.get(ri,room));
                    values.put("reserved_incoming_raw",tally.spaceReserved.get(ri,room));
                    boolean match=true;for(Filter f:filters)if(!f.matches(values.get(f.field))){match=false;break;}if(!match)continue;
                    Map<String,Object> row=object("matrix_position",position,"room_id",room.index(),"resource_id",resource,"room_blueprint_id",blueprint.key,
                        "anchor_tile_x",room.mX(),"anchor_tile_y",room.mY(),"room_active",isActive);
                    for(String field:fields)row.put(field,field.equals("reference_id")?"resource:"+resource:values.get(field));rows.add(row);
                }catch(RuntimeException failure){errors++;}
            }
            return object("request_id",id,"session_id",actual,"game_version",VERSION.VERSION_STRING,"captured_at",Instant.now().toString(),"tick",Math.max(0,GAME.updateI()),
                "observer_phase","GAME.addAfterUpdate","read_mode","stockpile_page","available",true,"coverage","partial","scope","instantiated_city_stockpile_bookkeeping",
                "scene",UiContextCollector.scene(),"ui_context",UiContextCollector.collect(),
                "data",object("rows",rows,"scanned_cells",scanned,"cell_errors",errors,"next_cursor",next<area?next:null,
                    "cursor_kind","stockpile_room_resource_matrix","room_source_kind",roomIds.isEmpty()?"current_warehouse_instance_slots":"explicit_room_ids",
                    "room_ids",roomIds,"resource_ids",resources,"room_count_total",count,"resource_registry_count",RESOURCES.ALL().size(),"resource_scan_limit",1000,"stockpile_blueprint_id",blueprint.key),
                "consistency","One callback per live page; cursors index current warehouse slots or the explicit room/resource matrix, never matching-row counts. Separate pages can change; no retained/global transaction.",
                "reason","Stored resource-specific counters, not free-to-use goods, future deliveries, physical fullness or selected rooms. Room IDs can be reused within a session; check scene, blueprint, anchors and observation time. Exact tally age is unknown; cell errors qualify missing matches.");
        }catch(RuntimeException failure){return error(actual,"Stockpile read unavailable: "+failure.getMessage());}
    }
}
