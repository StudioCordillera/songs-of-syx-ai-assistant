import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import game.GAME;
import init.resources.*;
import settlement.main.SETT;
import settlement.room.infra.stockpile.*;
import snake2d.CORE;
import syx.assistant.StockpileReadRequest;
import syx.assistant.JsonWriter;
import static syx.assistant.StateCollector.object;

/** TEST ONLY: detached candidate vs public resource-overload getters on a copied paused city. */
public final class StockpileScenario {
    static String session=UUID.randomUUID().toString();
    static int requests=0,comparisons=0,maxBytes=0;static List<Object> cases=new ArrayList<>();
    static final List<String> fields=List.of("assigned_crates","stored_raw","capacity_raw","reserved_stored_raw","reserved_incoming_raw","reference_id");
    static String frame(String rooms,List<String> keys,int cursor,int scan,int limit,String filters,String active,long expires,String requestedSession){
        List<String> encoded=new ArrayList<>();for(String key:keys)encoded.add(Base64.getUrlEncoder().withoutPadding().encodeToString(key.getBytes(StandardCharsets.UTF_8)));
        return "protocol=1\nrequest_id="+UUID.randomUUID()+"\nsession="+requestedSession+"\nexpires="+expires+"\nrooms="+rooms+"\nresources="+String.join(",",encoded)+"\nfields="+String.join(",",fields)+"\nfilters="+filters+"\nactive="+active+"\ncursor="+cursor+"\nscan_limit="+scan+"\nlimit="+limit+"\n";
    }
    static Map<String,Object> read(String rooms,List<String> keys,int cursor,int scan,int limit,String filters,String active){
        return readFrame(frame(rooms,keys,cursor,scan,limit,filters,active,System.currentTimeMillis()+8000,session));
    }
    static Map<String,Object> readFrame(String frame){
        var result=StockpileReadRequest.parse(frame).collect(session);requests++;
        int size=JsonWriter.encode(result).getBytes(StandardCharsets.UTF_8).length;maxBytes=Math.max(maxBytes,size);
        require(size<=65536,"Finite fixture response exceeds candidate page budget");return result;
    }
    static void require(boolean condition,String message){if(!condition)throw new IllegalStateException(message);}
    @SuppressWarnings("unchecked") static Map<String,Object> data(Map<String,Object> result){
        require(Boolean.TRUE.equals(result.get("available")),"Candidate refused an expected available request");
        require(result.get("session_id").equals(session),"Response session mismatch");
        require(((Number)result.get("tick")).longValue()==Math.max(0,GAME.updateI()),"Response tick mismatch");
        require(result.get("scope").equals("instantiated_city_stockpile_bookkeeping"),"Scope mismatch");
        return (Map<String,Object>)result.get("data");
    }
    @SuppressWarnings("unchecked") static List<Map<String,Object>> rows(Map<String,Object> d){return (List<Map<String,Object>>)d.get("rows");}
    static List<Map<String,Object>> expected(List<StockpileInstance> rooms,List<RESOURCE> resources){
        List<Map<String,Object>> result=new ArrayList<>();var tally=SETT.ROOMS().STOCKPILE.tally();int position=0;
        for(var room:rooms)for(var r:resources){
            result.add(object("matrix_position",position++,"room_id",room.index(),"resource_id",r.key,"room_blueprint_id",room.blueprint().key,
                "anchor_tile_x",room.mX(),"anchor_tile_y",room.mY(),"room_active",room.active(),
                "assigned_crates",tally.crates.get(r,room),"stored_raw",tally.amount.get(r,room),"capacity_raw",tally.space.get(r,room),
                "reserved_stored_raw",tally.amountReserved.get(r,room),"reserved_incoming_raw",tally.spaceReserved.get(r,room),"reference_id","resource:"+r.key));
        }
        return result;
    }
    static void same(List<Map<String,Object>> actual,List<Map<String,Object>> expected){require(actual.equals(expected),"Candidate differs from direct resource-overload getter rows");comparisons+=actual.size()*5;}
    static void record(String name){cases.add(object("name",name,"passed",true));}
    static void refused(Map<String,Object> response){require(Boolean.FALSE.equals(response.get("available")) && response.get("data")==null,"Expected explicit unavailable/null");}
    public static void install(Path directory){
        GAME.SPEED.speedSet(0);view.main.VIEW.s().activate();long began=System.currentTimeMillis();boolean[] written={false};
        GAME.addAfterUpdate(()->{
            try{
                if(!written[0] && System.currentTimeMillis()-began>10000){
                    written[0]=true;
                    require(SETT.exists() && !SETT.WORLD_AREA().isBattle && world.WORLD.GEN().isDone,"Completed city required");
                    List<StockpileInstance> rooms=new ArrayList<>();for(var r:SETT.ROOMS().STOCKPILE.all())rooms.add(r);
                    List<RESOURCE> resources=new ArrayList<>();List<String> keys=new ArrayList<>();for(var r:RESOURCES.ALL()){resources.add(r);keys.add(r.key);}
                    require(!rooms.isEmpty() && rooms.size()<=100 && !resources.isEmpty() && resources.size()<=100,"Finite copied warehouse/resource fixture required");
                    var baseline=expected(rooms,resources);require(baseline.size()<=10000,"Fixture matrix exceeds 10000 cells");
                    var full=data(read("",keys,0,4096,100,"",""));
                    same(rows(full),baseline.subList(0,Math.min(100,baseline.size())));record("typed_instance_discovery_and_counter_identity_parity");
                    List<Map<String,Object>> paged=new ArrayList<>();int cursor=0,pages=0;
                    while(cursor<baseline.size()){
                        var d=data(read("",keys,cursor,5,3,"",""));int n=((Number)d.get("scanned_cells")).intValue();
                        require(n==Math.min(3,baseline.size()-cursor) && ((Number)d.get("cell_errors")).intValue()==0,"Page row/scan bound mismatch");
                        same(rows(d),baseline.subList(cursor,cursor+n));paged.addAll(rows(d));cursor+=n;pages++;
                        require(Objects.equals(d.get("next_cursor"),cursor<baseline.size()?cursor:null),"Next cursor mismatch");
                    }
                    same(paged,baseline);record("full_matrix_paging_with_small_scan_and_row_caps");
                    cursor=0;int emptyPages=0;
                    while(cursor<baseline.size()){
                        var d=data(read("",keys,cursor,5,3,"stored_raw:gt:2147483647",""));int n=((Number)d.get("scanned_cells")).intValue();
                        require(rows(d).isEmpty() && n==Math.min(5,baseline.size()-cursor),"Empty filtered scan mismatch");cursor+=n;emptyPages++;
                        require(Objects.equals(d.get("next_cursor"),cursor<baseline.size()?cursor:null),"Filtered next cursor mismatch");
                    }
                    record("empty_filtered_pages_still_advance_matrix_cursor");
                    var positives=new ArrayList<Map<String,Object>>();for(var row:baseline)if((int)row.get("stored_raw")>0 && (int)row.get("capacity_raw")>0)positives.add(row);
                    require(!positives.isEmpty() && positives.size()<=100,"Finite fixture needs naturally stored goods");
                    same(rows(data(read("",keys,0,4096,100,"stored_raw:gt:0,capacity_raw:gt:0",""))),positives);record("and_predicates_preserve_original_matrix_positions");
                    String id=Integer.toString(rooms.get(0).index());var one=expected(List.of(rooms.get(0)),resources);
                    same(rows(data(read(id,keys,0,4096,100,"",""))),one);record("explicit_room_lookup_and_resource_binding");
                    String projected=frame(id,keys,0,4096,100,"","",System.currentTimeMillis()+8000,session)
                        .replace("fields="+String.join(",",fields),"fields=stored_raw,reference_id");
                    List<Map<String,Object>> projectedExpected=new ArrayList<>();for(var row:one){
                        var copy=new LinkedHashMap<String,Object>(row);for(String field:fields)if(!field.equals("stored_raw") && !field.equals("reference_id"))copy.remove(field);projectedExpected.add(copy);
                    }
                    require(rows(data(readFrame(projected))).equals(projectedExpected),"Projection differs from exact requested fields");record("projection_preserves_required_identity_without_extra_fields");
                    List<Map<String,Object>> zeroCapacity=new ArrayList<>();for(var row:baseline)if((int)row.get("capacity_raw")==0)zeroCapacity.add(row);
                    require(!zeroCapacity.isEmpty() && zeroCapacity.size()<=100,"Fixture needs zero assigned capacity");
                    same(rows(data(read("",keys,0,4096,100,"capacity_raw:eq:0",""))),zeroCapacity);record("zero_capacity_is_observed_zero_not_missing");
                    require(rows(data(read("",keys,baseline.size(),5,3,"",""))).isEmpty(),"Terminal cursor should be empty");
                    refused(read("",keys,baseline.size()+1,5,3,"",""));record("terminal_and_past_end_cursor");
                    refused(read(Integer.toString(SETT.ROOMS().map.max()),keys,0,5,3,"",""));
                    int nonWarehouse=-1;require(SETT.ROOMS().map.max()<=100000,"Fixture room search budget exceeded");
                    for(int i=0;i<SETT.ROOMS().map.max();i++){var room=SETT.ROOMS().map.getByIndex(i);if(room!=null && !(room instanceof StockpileInstance)){nonWarehouse=i;break;}}
                    require(nonWarehouse>=0,"Fixture needs a non-warehouse room");refused(read(Integer.toString(nonWarehouse),keys,0,5,3,"",""));
                    refused(read("",List.of("__fixture_unknown_stockpile_resource__"),0,5,3,"",""));record("unknown_and_nonwarehouse_identity_refusal");
                    refused(readFrame(frame("",keys,0,5,3,"","",System.currentTimeMillis()-1000,session)));
                    refused(readFrame(frame("",keys,0,5,3,"","",System.currentTimeMillis()+8000,UUID.randomUUID().toString())));record("expired_and_cross_session_refusal");
                    var controlled=rooms.get(0);require(controlled.active(),"Controlled warehouse must begin active");controlled.deactivate();
                    try{
                        var inactive=expected(List.of(controlled),resources);same(rows(data(read(id,keys,0,4096,100,"","false"))),inactive);
                        require(rows(data(read(id,keys,0,4096,100,"","true"))).isEmpty(),"Inactive room incorrectly matches active filter");
                        for(int i=0;i<one.size();i++)for(String f:fields)require(Objects.equals(one.get(i).get(f),inactive.get(i).get(f)),"Immediate deactivation unexpectedly changed stored bookkeeping");
                    }finally{controlled.activate(true);}
                    require(controlled.active(),"Controlled warehouse restoration failed");record("immediate_inactive_stored_bookkeeping_and_restoration");
                    boolean battle=SETT.WORLD_AREA().isBattle,done=world.WORLD.GEN().isDone;
                    try{SETT.WORLD_AREA().isBattle=true;refused(read("",keys,0,5,3,"",""));}finally{SETT.WORLD_AREA().isBattle=battle;}
                    try{world.WORLD.GEN().isDone=false;refused(read("",keys,0,5,3,"",""));}finally{world.WORLD.GEN().isDone=done;}
                    record("controlled_public_scope_flags_refuse_not_actual_battle_transition");
                    view.main.VIEW.world().activate();same(rows(data(read(id,keys,0,4096,100,"",""))),one);view.main.VIEW.s().activate();record("underlying_city_counters_from_world_view");
                    List<Long> times=new ArrayList<>();for(int i=0;i<32;i++){long start=System.nanoTime();var r=read(id,keys,0,4096,100,"","");long elapsed=System.nanoTime()-start;same(rows(data(r)),one);times.add(elapsed);}
                    Files.writeString(directory.resolve("stockpile-fixture.json"),JsonWriter.encode(object("passed",true,"cases",cases,"requests",requests,
                        "counter_comparisons",comparisons,"room_count",rooms.size(),"resource_count",resources.size(),"matrix_cells",baseline.size(),"pages",pages,
                        "empty_filtered_pages",emptyPages,"maximum_observed_response_bytes",maxBytes,"request_parse_collect_encode_ns",times,
                        "controlled_room_restored",controlled.active(),"controlled_scope_flags_restored",SETT.WORLD_AREA().isBattle==battle && world.WORLD.GEN().isDone==done)));
                    System.err.println("STOCKPILE CANDIDATE: detached native checks ready");
                }
                if(Files.exists(directory.resolve("verifier.done")) || System.currentTimeMillis()-began>110000)CORE.annihilate();
            }catch(Exception error){CORE.annihilate(error);}
        });
    }
}
