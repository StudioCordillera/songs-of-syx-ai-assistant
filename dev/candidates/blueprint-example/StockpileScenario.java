import java.nio.file.*;
import java.util.*;
import game.GAME;
import settlement.main.SETT;
import snake2d.CORE;
import syx.assistant.JsonWriter;
import static syx.assistant.StateCollector.object;

/** TEST ONLY: fixed public catalog reads; no room planning, placement or gameplay mutation. */
public final class StockpileScenario {
    public static void install(Path directory){
        GAME.SPEED.speedSet(0);long began=System.nanoTime();boolean[] written={false},finished={false};
        GAME.addAfterUpdate(()->{
            if(finished[0])return;
            try{
                if(Files.exists(directory.resolve("verifier.done"))){
                    Files.writeString(directory.resolve("blueprint-catalog-clean-exit.json"),JsonWriter.encode(object("passed",true)));
                    finished[0]=true;CORE.annihilate();return;
                }
                if(System.nanoTime()-began>100_000_000_000L)throw new IllegalStateException("Blueprint catalog timeout");
                if(written[0] || System.nanoTime()-began<3_000_000_000L)return;
                var blueprint=SETT.ROOMS().STOCKPILE;var furnisher=blueprint.constructor();
                if(furnisher.pgroups().size()<1)throw new IllegalStateException("Missing furnishing group");
                var group=furnisher.pgroups().get(0);
                if(group.size()<1 || group.rotations()<1)throw new IllegalStateException("Missing selected item");
                var item=group.item(0,0);int width=item.width(),height=item.height();
                if(width<1 || height<1 || width>64 || height>64)throw new IllegalStateException("Catalog item bounds");
                List<Object> cells=new ArrayList<>();
                for(int y=0;y<height;y++)for(int x=0;x<width;x++){
                    var tile=item.get(x,y);
                    if(tile!=null)cells.add(object("x",x,"y",y,"tile_index",tile.index(),"blocker",tile.isBlocker(),"must_be_reachable",tile.mustBeReachable));
                }
                Files.writeString(directory.resolve("stockpile-fixture.json"),JsonWriter.encode(object("passed",true,
                    "blueprint_id",blueprint.key,"group_index",group.index(),"size",0,"rotation",item.rotation,"item_index",item.index(),
                    "width",width,"height",height,"cells",cells,"must_be_indoors",furnisher.mustBeIndoors())));
                written[0]=true;
            }catch(Exception failure){finished[0]=true;System.err.println("SMOKE_FIXTURE_FAILURE: "+failure);CORE.annihilate(failure);}
        });
    }
}
