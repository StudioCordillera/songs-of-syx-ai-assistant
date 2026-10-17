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
                String terrain=SETT.TERRAIN().get(x,y).key();
                if(examples.size()<12)examples.putIfAbsent("terrain:"+terrain,new int[]{x,y});
            }
            for(String required:new String[]{"instance_room","floor","mineral","no_room","no_floor","no_mineral"})
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
                    "reachable",SETT.PATH().reachability.is(x,y)));
            }
            int[] anchor=examples.get("instance_room");int x1=Math.max(0,anchor[0]-8),y1=Math.max(0,anchor[1]-8);
            int x2=Math.min(SETT.TWIDTH,x1+24),y2=Math.min(SETT.THEIGHT,y1+24);
            String terrain=SETT.TERRAIN().get(anchor[0],anchor[1]).key();
            List<Object> matches=new ArrayList<>();
            for(int y=y1;y<y2;y++)for(int x=x1;x<x2;x++)
                if(terrain.equals(SETT.TERRAIN().get(x,y).key()) && SETT.ROOMS().map.get(x,y)!=null)
                    matches.add(Arrays.asList(x,y));
            Files.writeString(output.resolve("tile-fixture.json"),JsonWriter.encode(object("points",points,
                "rectangle",Arrays.asList(x1,y1,x2,y2),"terrain_filter",terrain,"matching_coordinates",matches,
                "width",SETT.TWIDTH,"height",SETT.THEIGHT)));
            long started=System.currentTimeMillis();boolean[] advanced={false};
            GAME.addAfterUpdate(()->{
                if(advanced[0])return;
                if(Files.exists(output.resolve("tile-verifier.done"))) {
                    advanced[0]=true;SceneScenario.install(output,save);return;
                }
                if(System.currentTimeMillis()-started>140000){advanced[0]=true;CORE.annihilate();}
            });
        }catch(Exception error){throw new IllegalStateException(error);}
    }
}
