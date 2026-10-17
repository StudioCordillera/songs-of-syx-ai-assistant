package syx.assistant;

import game.GAME;
import game.VERSION;
import settlement.main.SETT;
import java.time.Instant;
import java.nio.charset.StandardCharsets;
import java.util.*;
import static syx.assistant.StateCollector.object;

/** Fixed public tile observations, evaluated only by the game after-update observer. */
public final class TileReadRequest {
    public final String id,session;
    final long expires;
    final int x1,y1,x2,y2,cursor,scanLimit,limit;
    final Set<String> fields;
    final String terrain,floor,room,mineral;
    final Boolean hasRoom,reachable;
    private TileReadRequest(Map<String,String> v) {
        if(!"1".equals(v.get("protocol")))throw new IllegalArgumentException("Unsupported tile protocol");
        id=uuid(v.get("request_id"));session=uuid(v.get("session"));
        expires=Long.parseLong(v.get("expires"));
        String[] bounds=v.get("bounds").split(",",-1);
        if(bounds.length!=4)throw new IllegalArgumentException("Four bounds required");
        x1=number(bounds[0],0,100000);y1=number(bounds[1],0,100000);
        x2=number(bounds[2],0,100000);y2=number(bounds[3],0,100000);
        if(x2<=x1 || y2<=y1)throw new IllegalArgumentException("Exclusive upper tile bounds required");
        cursor=number(v.get("cursor"),0,Integer.MAX_VALUE);scanLimit=number(v.get("scan_limit"),1,4096);limit=number(v.get("limit"),1,100);
        fields=new LinkedHashSet<>();
        for(String field:v.get("fields").split(",",-1))
            if(!Set.of("terrain","floor","room","minerals","path").contains(field) || !fields.add(field))throw new IllegalArgumentException("Unknown/duplicate tile field");
        terrain=key(v.get("terrain"));floor=key(v.get("floor"));room=key(v.get("room"));mineral=key(v.get("mineral"));
        hasRoom=bool(v.get("has_room"));reachable=bool(v.get("reachable"));
    }
    private static int number(String s,int low,int high) {
        if(!s.matches("0|[1-9][0-9]*"))throw new IllegalArgumentException("Canonical nonnegative integer required");
        int n=Integer.parseInt(s);if(n<low || n>high)throw new IllegalArgumentException("Tile bound exceeded");return n;
    }
    private static String uuid(String s){if(!UUID.fromString(s).toString().equals(s))throw new IllegalArgumentException("Canonical UUID required");return s;}
    private static Boolean bool(String s){if(s.isEmpty())return null;if("true".equals(s))return true;if("false".equals(s))return false;throw new IllegalArgumentException("Boolean required");}
    private static String key(String s) {
        if(s.isEmpty())return null;
        byte[] raw=Base64.getUrlDecoder().decode(s);
        String text=new String(raw,StandardCharsets.UTF_8);
        if(text.isEmpty() || text.codePointCount(0,text.length())>100 || !Base64.getUrlEncoder().withoutPadding().encodeToString(text.getBytes(StandardCharsets.UTF_8)).equals(s))throw new IllegalArgumentException("Invalid key encoding");
        return text;
    }
    public static TileReadRequest parse(String text) {
        if(text.getBytes(StandardCharsets.UTF_8).length>8192)throw new IllegalArgumentException("Tile request exceeds 8 KiB");
        Set<String> keys=Set.of("protocol","request_id","session","expires","bounds","cursor","scan_limit","limit","fields","terrain","floor","room","mineral","has_room","reachable");
        Map<String,String> values=new LinkedHashMap<>();
        for(String line:text.split("\n",-1)) {
            if(line.isEmpty())continue;int eq=line.indexOf('=');
            if(eq<1 || !keys.contains(line.substring(0,eq)) || values.putIfAbsent(line.substring(0,eq),line.substring(eq+1))!=null)throw new IllegalArgumentException("Unknown/duplicate tile request key");
        }
        if(values.size()!=keys.size())throw new IllegalArgumentException("Incomplete tile request");
        return new TileReadRequest(values);
    }
    public Map<String,Object> collect(String currentSession) {
        Map<String,Object> result=object("request_id",id,"session_id",currentSession,"game_version",VERSION.VERSION_STRING,
            "captured_at",Instant.now().toString(),"tick",Math.max(0,GAME.updateI()),"read_mode","tile_page","observer_phase","GAME.addAfterUpdate",
            "coverage","partial","scope","instantiated_settlement_scene",
            "consistency","One game after-update observation. Cursor pages are separate mutable observations; no global worker transaction.");
        try {
            if(!session.equals(currentSession))throw new IllegalArgumentException("Session changed");
            if(System.currentTimeMillis()>expires)throw new IllegalArgumentException("Tile request expired");
            if(!SETT.exists())throw new IllegalStateException("No instantiated settlement scene");
            if(x2>SETT.TWIDTH || y2>SETT.THEIGHT)throw new IllegalArgumentException("Bounds exceed instantiated map");
            long area=(long)(x2-x1)*(y2-y1);
            if(cursor>area)throw new IllegalArgumentException("Cursor exceeds rectangular area");
            int next=cursor,scanned=0,errors=0;List<Object> rows=new ArrayList<>();
            while(next<area && scanned<scanLimit && rows.size()<limit) {
                int x=x1+next%(x2-x1),y=y1+next/(x2-x1);next++;scanned++;
                try {
                    if(terrain!=null && !terrain.equals(SETT.TERRAIN().get(x,y).key()))continue;
                    if(floor!=null) {settlement.tilemap.floor.Floors.Floor f=SETT.FLOOR().getter.get(x,y);if(f==null || !floor.equals(f.key))continue;}
                    if(room!=null || hasRoom!=null) {
                        settlement.room.main.Room r=SETT.ROOMS().map.get(x,y);
                        if(hasRoom!=null && (r!=null)!=hasRoom)continue;
                        if(room!=null && (r==null || !room.equals(r.blueprint().key)))continue;
                    }
                    if(mineral!=null) {init.resources.Minable m=SETT.MINERALS().getter.get(x,y);if(m==null || !mineral.equals(m.resource.key))continue;}
                    if(reachable!=null && SETT.PATH().reachability.is(x,y)!=reachable)continue;
                } catch(RuntimeException error) {errors++;continue;}
                Map<String,Object> row=object("tile_x",x,"tile_y",y);
                for(String field:fields)try {row.put(field,object("available",true,"data",read(field,x,y)));}
                catch(RuntimeException error){row.put(field,object("available",false,"data",null,"reason",error.getClass().getSimpleName()));}
                rows.add(row);
            }
            result.put("available",true);result.put("scene",UiContextCollector.scene());result.put("ui_context",UiContextCollector.collect());
            result.put("data",object("rows",rows,"scanned_tiles",scanned,"predicate_errors",errors,"next_cursor",next<area?next:null,
                "cursor_kind","row_major_rectangle_offset","bounds",Arrays.asList(x1,y1,x2,y2)));
        } catch(RuntimeException error){result.put("available",false);result.put("reason",error.getClass().getSimpleName()+": "+error.getMessage());result.put("data",null);}
        return result;
    }
    private static Object read(String field,int x,int y) {
        switch(field) {
            case "terrain": {
                settlement.tilemap.terrain.Terrain.TerrainTile t=SETT.TERRAIN().get(x,y);
                return object("key",t.key(),"name",t.name().toString(),"roof_flag",t.roofIs(),"massive_wall_flag",t.isMassiveWall());
            }
            case "floor": {
                settlement.tilemap.floor.Floors.Floor f=SETT.FLOOR().getter.get(x,y);
                return f==null?null:object("key",f.key,"name",f.name.toString(),"is_road",f.isRoad,"degradation_raw",SETT.FLOOR().degrade.get(x,y));
            }
            case "room": {
                settlement.room.main.Room r=SETT.ROOMS().map.get(x,y);
                return r==null?null:object("map_record_id",r.index(),"instance_room_id",r instanceof settlement.room.main.RoomInstance?r.index():null,"blueprint_id",r.blueprint().key,"name",r.name(x,y).toString(),
                    "anchor_tile_x",r.mX(x,y),"anchor_tile_y",r.mY(x,y),"area_tiles",r.area(x,y));
            }
            case "minerals": {
                init.resources.Minable m=SETT.MINERALS().getter.get(x,y);
                return m==null?null:object("resource_id",m.resource.key,"reference_id","resource:"+m.resource.key,
                    "amount_raw",SETT.MINERALS().amountInt.get(x,y),"amount_fraction",SETT.MINERALS().amountD.get(x,y),"richness_flag_raw",SETT.MINERALS().value.get(x,y));
            }
            case "path": {
                settlement.path.AVAILABILITY a=SETT.PATH().getAvailability(x,y);
                return object("availability",a.name(),"available_to_stand_on",a.availableToStandOn,"tile_collide",a.tileCollide,
                    "player_cost_raw",a.player,"enemy_cost_raw",a.enemy,"movement_speed_raw",a.movementSpeed,
                    "throne_component_reachable",SETT.PATH().reachability.is(x,y));
            }
            default:throw new IllegalArgumentException("Unknown tile field");
        }
    }
}
