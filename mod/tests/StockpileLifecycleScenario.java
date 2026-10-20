import java.nio.file.*;
import java.util.*;
import game.GAME;
import init.resources.RESOURCES;
import settlement.main.SETT;
import settlement.room.infra.stockpile.StockpileInstance;
import settlement.room.main.util.RoomInit;
import snake2d.CORE;
import syx.assistant.JsonWriter;
import static syx.assistant.StateCollector.object;

/** TEST ONLY: public removal/reconstruction in a disposable copied city; never saves. */
public final class StockpileLifecycleScenario {
    public static void install(Path directory) {
        view.main.VIEW.s().activate();GAME.SPEED.speedSet(0);
        long began=System.nanoTime();int[] phase={0},originalId={-1};
        StockpileInstance[] current={null};boolean[] finished={false};
        GAME.addAfterUpdate(()->{
            if(finished[0])return;
            try {
                if(System.nanoTime()-began>140_000_000_000L)throw new IllegalStateException("Lifecycle verifier timed out");
                if(phase[0]==0){
                    if(System.nanoTime()-began<5_000_000_000L)return;
                    if(!SETT.exists() || SETT.WORLD_AREA().isBattle || !world.WORLD.GEN().isDone || SETT.ROOMS().STOCKPILE.all().size()!=1)
                        throw new IllegalStateException("Requires one warehouse in a completed copied city");
                    // Normalize the allocator once: a loaded save can have earlier free room slots.
                    current[0]=rebuild(SETT.ROOMS().STOCKPILE.all().get(0));originalId[0]=current[0].index();
                }else if(!Files.exists(directory.resolve("stockpile-lifecycle-"+(phase[0]-1)+".done")))return;
                if(phase[0]==1){
                    var old=current[0];current[0]=rebuild(old);
                    current[0].deactivate();
                    if(old.exists() || old==current[0] || current[0].index()!=originalId[0] || SETT.ROOMS().map.getByIndex(originalId[0])!=current[0])
                        throw new IllegalStateException("Expected actual distinct-instance room ID reuse");
                }else if(phase[0]==2){
                    var old=current[0];old.remove(old.mX(),old.mY(),false,StockpileLifecycleScenario.class,true).clearAndUpdate();
                    if(old.exists() || SETT.ROOMS().map.getByIndex(originalId[0])!=null || SETT.ROOMS().STOCKPILE.all().size()!=0)
                        throw new IllegalStateException("Removed warehouse still registered");
                    current[0]=null;
                }else if(phase[0]==3){
                    Files.writeString(directory.resolve("stockpile-lifecycle-clean-exit.json"),JsonWriter.encode(object("passed",true,"verified_phases",3)));
                    finished[0]=true;CORE.annihilate();return;
                }
                List<Object> rows=new ArrayList<>();List<String> keys=new ArrayList<>();var tally=SETT.ROOMS().STOCKPILE.tally();
                for(var r:RESOURCES.ALL()){
                    keys.add(r.key);var room=current[0];if(room==null)continue;
                    rows.add(object("matrix_position",rows.size(),"room_id",room.index(),"resource_id",r.key,
                        "room_blueprint_id",room.blueprint().key,"anchor_tile_x",room.mX(),"anchor_tile_y",room.mY(),"room_active",room.active(),
                        "assigned_crates",tally.crates.get(r,room),"stored_raw",tally.amount.get(r,room),"capacity_raw",tally.space.get(r,room),
                        "reserved_stored_raw",tally.amountReserved.get(r,room),"reserved_incoming_raw",tally.spaceReserved.get(r,room),"reference_id","resource:"+r.key));
                }
                Files.writeString(directory.resolve("stockpile-lifecycle-"+phase[0]+".json"),JsonWriter.encode(object(
                    "phase",phase[0],"original_room_id",originalId[0],"resource_ids",keys,"rows",rows,"warehouse_count",SETT.ROOMS().STOCKPILE.all().size())));
                phase[0]++;
            }catch(Exception error){
                finished[0]=true;System.err.println("SMOKE_FIXTURE_FAILURE: "+error);
                try{Files.writeString(directory.resolve("stockpile-lifecycle-failure.json"),error.toString());}catch(Exception ignored){}
                CORE.annihilate(error);
            }
        });
    }
    private static StockpileInstance rebuild(StockpileInstance old) {
        var blueprint=SETT.ROOMS().STOCKPILE;RoomInit init=new RoomInit(blueprint,0);
        for(int i=0;i<init.stats.length;i++)init.stats[i]=old.stat(i);
        int x=old.mX(),y=old.mY();
        if(!old.is(x,y))throw new IllegalStateException("Anchor is not a room tile");
        var area=old.remove(x,y,false,StockpileLifecycleScenario.class,true);
        // Consume the singleton temporary area within this same callback. No scratch handle escapes.
        var replacement=(StockpileInstance)blueprint.constructor().create(area,init);
        SETT.ROOMS().stats.finished().add(replacement.mX(),replacement.mY());
        if(old.exists() || old==replacement)throw new IllegalStateException("Reconstruction did not replace the instance");
        return replacement;
    }

}
