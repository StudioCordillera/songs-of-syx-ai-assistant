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

/** TEST ONLY: real small warehouse instances in a disposable paused city, never saved. */
public final class StockpileMatrixScenario {
    public static void install(Path directory) {
        view.main.VIEW.s().activate();GAME.SPEED.speedSet(0);
        long began=System.nanoTime();int[] phase={0},removedId={-1};boolean[] finished={false};
        GAME.addAfterUpdate(()->{
            if(finished[0])return;
            try {
                if(System.nanoTime()-began>180_000_000_000L)throw new IllegalStateException("Warehouse matrix verifier timed out");
                if(phase[0]==0){
                    if(System.nanoTime()-began<5_000_000_000L)return;
                    if(!SETT.exists() || SETT.WORLD_AREA().isBattle || !world.WORLD.GEN().isDone || SETT.ROOMS().STOCKPILE.all().size()!=1 || RESOURCES.ALL().size()!=42)
                        throw new IllegalStateException("Requires the paired copied city with one warehouse and 42 resources");
                    var blueprint=SETT.ROOMS().STOCKPILE;var item=blueprint.constructor().item(1);
                    if(item==null || item.width()>3 || item.height()>3)throw new IllegalStateException("Unexpected small furnishing item");
                    int created=0,candidates=0;
                    search:for(int y=8;y<SETT.THEIGHT-8;y+=4)for(int x=8;x<SETT.TWIDTH-8;x+=4){
                        if(++candidates>40000)throw new IllegalStateException("Fixture placement search budget exhausted");
                        boolean free=true;
                        for(int dy=0;dy<3;dy++)for(int dx=0;dx<3;dx++){
                            if(SETT.ROOMS().map.get(x+dx,y+dy)!=null || SETT.PATH().availability.get(x+dx,y+dy).player<=0)free=false;
                        }
                        if(!free)continue;
                        var area=SETT.ROOMS().tmpArea(StockpileMatrixScenario.class);
                        for(int dy=0;dy<3;dy++)for(int dx=0;dx<3;dx++)area.set(x+dx,y+dy);
                        SETT.ROOMS().fData.itemSet(x,y,item,area.room());
                        var room=(StockpileInstance)blueprint.constructor().create(area,new RoomInit(blueprint,0));
                        SETT.ROOMS().stats.finished().add(room.mX(),room.mY());
                        if(room.totalCrates()<1)throw new IllegalStateException("No real furnishing crates created");
                        if(++created==100)break search;
                    }
                    if(created!=100 || blueprint.all().size()!=101)throw new IllegalStateException("Expected 101 actual warehouses");
                    removedId[0]=blueprint.all().get(1).index();
                }else if(!Files.exists(directory.resolve("stockpile-matrix-"+(phase[0]-1)+".done")))return;
                if(phase[0]==1){
                    var room=SETT.ROOMS().STOCKPILE.all().get(1);
                    if(room.index()!=removedId[0])throw new IllegalStateException("Unexpected warehouse order");
                    room.remove(room.mX(),room.mY(),false,StockpileMatrixScenario.class,true).clearAndUpdate();
                    if(room.exists() || SETT.ROOMS().map.getByIndex(removedId[0])!=null || SETT.ROOMS().STOCKPILE.all().size()!=100)
                        throw new IllegalStateException("Middle warehouse removal did not complete");
                }else if(phase[0]==2){
                    Files.writeString(directory.resolve("stockpile-matrix-clean-exit.json"),JsonWriter.encode(object("passed",true,"verified_phases",2)));
                    finished[0]=true;CORE.annihilate();return;
                }
                var blueprint=SETT.ROOMS().STOCKPILE;var tally=blueprint.tally();List<Object> rows=new ArrayList<>();List<Integer> ids=new ArrayList<>();List<String> keys=new ArrayList<>();
                for(var r:RESOURCES.ALL())keys.add(r.key);
                for(var room:blueprint.all()){
                    ids.add(room.index());for(var r:RESOURCES.ALL())rows.add(object("matrix_position",rows.size(),"room_id",room.index(),"resource_id",r.key,
                        "room_blueprint_id",room.blueprint().key,"anchor_tile_x",room.mX(),"anchor_tile_y",room.mY(),"room_active",room.active(),
                        "assigned_crates",tally.crates.get(r,room),"stored_raw",tally.amount.get(r,room),"capacity_raw",tally.space.get(r,room),
                        "reserved_stored_raw",tally.amountReserved.get(r,room),"reserved_incoming_raw",tally.spaceReserved.get(r,room),"reference_id","resource:"+r.key));
                }
                Files.writeString(directory.resolve("stockpile-matrix-"+phase[0]+".json"),JsonWriter.encode(object("phase",phase[0],"removed_room_id",removedId[0],"room_ids",ids,"resource_ids",keys,"rows",rows)));
                phase[0]++;
            }catch(Exception error){
                finished[0]=true;System.err.println("SMOKE_FIXTURE_FAILURE: "+error);
                try{Files.writeString(directory.resolve("stockpile-matrix-failure.json"),error.toString());}catch(Exception ignored){}
                CORE.annihilate(error);
            }
        });
    }
}
