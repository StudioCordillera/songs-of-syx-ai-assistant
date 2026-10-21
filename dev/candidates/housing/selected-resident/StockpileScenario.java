import java.nio.file.*;
import java.util.*;
import game.GAME;
import settlement.main.SETT;
import settlement.room.home.HOME;
import settlement.room.home.house.HomeInstance;
import settlement.room.home.chamber.ChamberInstance;
import settlement.stats.STATS;
import snake2d.CORE;
import syx.assistant.JsonWriter;
import syx.assistant.StateCollector;
import static syx.assistant.StateCollector.object;

/** TEST ONLY: select two naturally housed workers through the existing public subject UI in an isolated paused city. */
public final class StockpileScenario {
    public static void install(Path directory){
        view.main.VIEW.s().activate();GAME.SPEED.speedSet(0);long began=System.nanoTime();boolean[] written={false},finished={false};
        GAME.addAfterUpdate(()->{
            if(finished[0])return;
            try{
                if(Files.exists(directory.resolve("verifier.done"))){
                    if(!written[0])throw new IllegalStateException("Premature completion");
                    Files.writeString(directory.resolve("selected-resident-clean-exit.json"),JsonWriter.encode(object("passed",true,"samples",2)));
                    finished[0]=true;CORE.annihilate();return;
                }
                if(System.nanoTime()-began>100_000_000_000L)throw new IllegalStateException("Selected-resident timeout");
                if(written[0] || System.nanoTime()-began<5_000_000_000L)return;
                int tick=GAME.updateI();String session=UUID.randomUUID().toString();Set<Integer> ids=new HashSet<>();List<Object> samples=new ArrayList<>();
                search:for(int slot=0;slot<SETT.ROOMS().map.max();slot++){
                    var room=SETT.ROOMS().map.getByIndex(slot);
                    if(!(room instanceof HomeInstance) && !(room instanceof ChamberInstance))continue;
                    HOME home=(HOME)room;
                    for(int i=0;i<Math.min(home.occupants(),64);i++){
                        var h=home.occupant(i);if(h==null || h.isRemoved() || ids.contains(h.id()))continue;
                        var workplace=STATS.WORK().EMPLOYED.get(h);
                        if(workplace==null || workplace.employees()==null || workplace.blueprint().employment()==null)continue;
                        // hCoo is a public scratch coordinate; copy primitives immediately and never retain the handle.
                        var hc=STATS.HOME().GETTER.hCoo(h);if(hc==null)continue;int hx=hc.x(),hy=hc.y();
                        if(hx!=home.serviceX() || hy!=home.serviceY())throw new IllegalStateException("Independent recorded-home coordinate mismatch");
                        view.main.VIEW.s().ui.subjects.showSingle(h);
                        if(view.main.VIEW.s().ui.subjects.current()!=h)throw new IllegalStateException("Underlying subject selection mismatch");
                        int sequence=samples.size()+1;var observation=StateCollector.collect(session,sequence);
                        if(GAME.updateI()!=tick)throw new IllegalStateException("Crossed callback");
                        String name="selected-resident-"+sequence+".json";
                        Files.writeString(directory.resolve(name),JsonWriter.encode(observation));
                        samples.add(object("file",name,"entity_id",h.id(),"home_room_id",room.index(),"home_kind",room instanceof HomeInstance?"ordinary_home":"noble_chamber",
                            "home_x",hx,"home_y",hy,"home_capacity",home.occupantsMax(),"workplace_room_id",workplace.index(),
                            "workplace_blueprint_id",workplace.blueprint().key,"workplace_employed",workplace.employees().employed(),"workplace_needed",workplace.employees().needed(),
                            "workplace_target",workplace.employees().target(),"workplace_capacity",workplace.employees().max()));
                        ids.add(h.id());if(samples.size()==2)break search;
                    }
                }
                if(samples.size()!=2)throw new IllegalStateException("Need two naturally housed employed subjects");
                Files.writeString(directory.resolve("stockpile-fixture.json"),JsonWriter.encode(object("passed",true,"same_callback",true,"samples",samples)));
                written[0]=true;
            }catch(Exception failure){finished[0]=true;System.err.println("SMOKE_FIXTURE_FAILURE: "+failure);CORE.annihilate(failure);}
        });
    }
}
