import java.nio.file.*;
import java.util.*;
import game.GAME;
import init.resources.*;
import settlement.main.SETT;
import snake2d.CORE;
import syx.assistant.JsonWriter;
import static syx.assistant.StateCollector.object;

/** TEST ONLY: independent stored getter rows held in a paused copied city for real MCP queries. */
public final class StockpileLiveScenario {
    public static void install(Path directory,Path save){
        GAME.SPEED.speedSet(0);view.main.VIEW.s().activate();long began=System.nanoTime();boolean[] written={false},finished={false};
        GAME.addAfterUpdate(()->{
            if(finished[0])return;
            try{
                if(Files.exists(directory.resolve("stockpile-live.done"))){finished[0]=true;SceneScenario.install(directory,save);return;}
                if(System.nanoTime()-began>140_000_000_000L)throw new IllegalStateException("Stockpile MCP verifier timed out");
                if(written[0] || System.nanoTime()-began<5_000_000_000L)return;
                if(!SETT.exists() || SETT.WORLD_AREA().isBattle || !world.WORLD.GEN().isDone)throw new IllegalStateException("Completed copied city required");
                var blueprint=SETT.ROOMS().STOCKPILE;var tally=blueprint.tally();
                if(blueprint.all().size()<1 || blueprint.all().size()>100 || RESOURCES.ALL().size()>100)throw new IllegalStateException("Finite warehouse/resource matrix required");
                List<Integer> ids=new ArrayList<>();List<String> keys=new ArrayList<>();List<Object> rows=new ArrayList<>();
                for(var r:RESOURCES.ALL())keys.add(r.key);int position=0;
                for(var room:blueprint.all()){
                    ids.add(room.index());for(var r:RESOURCES.ALL())rows.add(object("matrix_position",position++,"room_id",room.index(),"resource_id",r.key,
                        "room_blueprint_id",room.blueprint().key,"anchor_tile_x",room.mX(),"anchor_tile_y",room.mY(),"room_active",room.active(),
                        "assigned_crates",tally.crates.get(r,room),"stored_raw",tally.amount.get(r,room),"capacity_raw",tally.space.get(r,room),
                        "reserved_stored_raw",tally.amountReserved.get(r,room),"reserved_incoming_raw",tally.spaceReserved.get(r,room),"reference_id","resource:"+r.key));
                }
                int nonWarehouse=-1;if(SETT.ROOMS().map.max()>100000)throw new IllegalStateException("Fixture room scan bound exceeded");
                for(int i=0;i<SETT.ROOMS().map.max();i++){var room=SETT.ROOMS().map.getByIndex(i);if(room!=null && room.blueprint()!=blueprint){nonWarehouse=i;break;}}
                if(nonWarehouse<0)throw new IllegalStateException("Fixture needs a non-warehouse room");
                Files.writeString(directory.resolve("stockpile-live-fixture.json"),JsonWriter.encode(object("room_ids",ids,"resource_ids",keys,"rows",rows,
                    "out_of_bounds_room",SETT.ROOMS().map.max(),"non_warehouse_room",nonWarehouse,"blueprint_id",blueprint.key)));
                written[0]=true;System.err.println("STOCKPILE LIVE: independent getter rows ready");
            }catch(Exception failure){CORE.annihilate(failure);}
        });
    }
}
