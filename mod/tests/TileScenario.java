import java.nio.file.*;
import java.util.*;
import game.GAME;
import settlement.main.SETT;
import settlement.room.main.Room;
import settlement.room.main.RoomInstance;
import view.main.VIEW;
import snake2d.CORE;
import syx.assistant.JsonWriter;
import static syx.assistant.StateCollector.object;

/** Test only: direct public getter expectations in a copied paused city, then existing scene transitions. */
public final class TileScenario {
    public static void install(Path output,Path save) {
        try {
            Files.createDirectories(output);VIEW.s().activate();GAME.SPEED.speedSet(0);
            Map<String,int[]> examples=new LinkedHashMap<>();
            for(int y=0;y<SETT.THEIGHT;y++)for(int x=0;x<SETT.TWIDTH;x++) {
                Room r=SETT.ROOMS().map.get(x,y);
                if(r instanceof RoomInstance)examples.putIfAbsent("instance_room",new int[]{x,y});
                else if(r!=null)examples.putIfAbsent("shared_room_record",new int[]{x,y});
                else examples.putIfAbsent("no_room",new int[]{x,y});
                if(SETT.FLOOR().getter.get(x,y)!=null)examples.putIfAbsent("floor",new int[]{x,y});
                else examples.putIfAbsent("no_floor",new int[]{x,y});
                if(SETT.MINERALS().getter.get(x,y)!=null)examples.putIfAbsent("mineral",new int[]{x,y});
                else examples.putIfAbsent("no_mineral",new int[]{x,y});
                double base=SETT.GROUND().MOISTURE_BASE.get(x,y),current=SETT.GROUND().MOISTURE_CURRENT.get(x,y);
                if(base==0)examples.putIfAbsent("moisture_base_zero",new int[]{x,y});
                if(base==1)examples.putIfAbsent("moisture_base_full",new int[]{x,y});
                if(base!=current)examples.putIfAbsent("moisture_base_current_different",new int[]{x,y});
                String terrain=SETT.TERRAIN().get(x,y).key();
                if(examples.size()<12)examples.putIfAbsent("terrain:"+terrain,new int[]{x,y});
            }
            for(String required:new String[]{"instance_room","floor","mineral","no_room","no_floor","no_mineral","moisture_base_zero","moisture_base_full","moisture_base_current_different"})
                if(!examples.containsKey(required))throw new IllegalStateException("Copied fixture lacks "+required);
            List<Object> points=new ArrayList<>();
            for(Map.Entry<String,int[]> e:examples.entrySet()) {
                int x=e.getValue()[0],y=e.getValue()[1];Room room=SETT.ROOMS().map.get(x,y);
                settlement.tilemap.floor.Floors.Floor floor=SETT.FLOOR().getter.get(x,y);
                init.resources.Minable mineral=SETT.MINERALS().getter.get(x,y);
                settlement.path.AVAILABILITY path=SETT.PATH().getAvailability(x,y);
                points.add(object("case",e.getKey(),"tile_x",x,"tile_y",y,"terrain",SETT.TERRAIN().get(x,y).key(),
                    "floor",floor==null?null:floor.key,"degrade",floor==null?null:SETT.FLOOR().degrade.get(x,y),
                    "room_record",room==null?null:room.index(),"instance_room",room instanceof RoomInstance?room.index():null,
                    "room_blueprint",room==null?null:room.blueprint().key,"mineral",mineral==null?null:mineral.resource.key,
                    "amount_raw",mineral==null?null:SETT.MINERALS().amountInt.get(x,y),"availability",path.name(),
                    "reachable",SETT.PATH().reachability.is(x,y),
                    "base_fraction",SETT.GROUND().MOISTURE_BASE.get(x+y*SETT.TWIDTH),
                    "stored_current_fraction",SETT.GROUND().MOISTURE_CURRENT.get(x+y*SETT.TWIDTH)));
            }
            int[] anchor=examples.get("instance_room");int x1=Math.max(0,anchor[0]-8),y1=Math.max(0,anchor[1]-8);
            int x2=Math.min(SETT.TWIDTH,x1+24),y2=Math.min(SETT.THEIGHT,y1+24);
            String terrain=SETT.TERRAIN().get(anchor[0],anchor[1]).key();
            List<Object> matches=new ArrayList<>();
            for(int y=y1;y<y2;y++)for(int x=x1;x<x2;x++)
                if(terrain.equals(SETT.TERRAIN().get(x,y).key()) && SETT.ROOMS().map.get(x,y)!=null)
                    matches.add(Arrays.asList(x,y));
            int cx=Math.max(0,Math.min(anchor[0]-5,SETT.TWIDTH-10));
            int cy=Math.max(0,Math.min(anchor[1]-5,SETT.THEIGHT-10));
            List<Object> captureRows=new ArrayList<>();
            for(int y=cy;y<cy+10;y++)for(int x=cx;x<cx+10;x++) {
                var t=SETT.TERRAIN().get(x,y);Room r=SETT.ROOMS().map.get(x,y);
                captureRows.add(object("tile_x",x,"tile_y",y,
                    "ground_moisture",object("available",true,"data",object("base_fraction",SETT.GROUND().MOISTURE_BASE.get(x+y*SETT.TWIDTH),"stored_current_fraction",SETT.GROUND().MOISTURE_CURRENT.get(x+y*SETT.TWIDTH))),
                    "terrain",object("available",true,"data",object("key",t.key(),"name",t.name().toString(),
                        "roof_flag",t.roofIs(),"massive_wall_flag",t.isMassiveWall())),
                    "room",object("available",true,"data",r==null?null:object("map_record_id",r.index(),
                        "instance_room_id",r instanceof RoomInstance?r.index():null,"blueprint_id",r.blueprint().key,
                        "name",r.name(x,y).toString(),"anchor_tile_x",r.mX(x,y),"anchor_tile_y",r.mY(x,y),"area_tiles",r.area(x,y)))));
            }
            Files.writeString(output.resolve("tile-fixture.json"),JsonWriter.encode(object("points",points,
                "capture_rectangle",Arrays.asList(cx,cy,cx+10,cy+10),"capture_rows",captureRows,
                "rectangle",Arrays.asList(x1,y1,x2,y2),"terrain_filter",terrain,"matching_coordinates",matches,
                "width",SETT.TWIDTH,"height",SETT.THEIGHT)));
            long started=System.currentTimeMillis();boolean[] advanced={false},worldAdvance={false},cityRestore={false};
            GAME.addAfterUpdate(()->{
                if(advanced[0])return;
                try {
                    if(!worldAdvance[0] && Files.exists(output.resolve("tile-capture-advance.request"))) {
                        worldAdvance[0]=true;VIEW.world().activate();GAME.SPEED.speedSet(1);
                    }
                    if(!cityRestore[0] && Files.exists(output.resolve("tile-capture-city.request"))) {
                        cityRestore[0]=true;GAME.SPEED.speedSet(0);VIEW.s().activate();
                    }
                }catch(Exception error){throw new IllegalStateException(error);}
                if(Files.exists(output.resolve("tile-verifier.done"))) {
                    advanced[0]=true;SceneScenario.install(output,save);return;
                }
                if(System.currentTimeMillis()-started>140000){advanced[0]=true;CORE.annihilate();}
            });
        }catch(Exception error){throw new IllegalStateException(error);}
    }
}
