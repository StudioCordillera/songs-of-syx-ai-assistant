import java.nio.file.*;
import java.util.*;
import game.GAME;
import settlement.main.SETT;
import settlement.room.home.house.HomeInstance;
import snake2d.CORE;
import syx.assistant.JsonWriter;
import syx.assistant.candidate.HousingObservation;
import static syx.assistant.StateCollector.object;

/** TEST ONLY: remove/restore one ordinary home's furnishing through public APIs in one copied-city callback. */
public final class StockpileScenario {
    static void require(boolean ok,String why){if(!ok)throw new IllegalStateException(why);}
    @SuppressWarnings("unchecked")
    public static void install(Path directory){
        GAME.SPEED.speedSet(0);view.main.VIEW.s().activate();long began=System.nanoTime();boolean[] written={false},finished={false};
        GAME.addAfterUpdate(()->{
            if(finished[0])return;
            try{
                if(Files.exists(directory.resolve("verifier.done"))){
                    require(written[0],"Premature verification");
                    Files.writeString(directory.resolve("housing-fault-clean-exit.json"),JsonWriter.encode(object("passed",true,"fault_cases",1,"housing_output_restored",true)));
                    finished[0]=true;CORE.annihilate();return;
                }
                require(System.nanoTime()-began<100_000_000_000L,"Housing fault timeout");
                if(written[0] || System.nanoTime()-began<5_000_000_000L)return;
                int tick=GAME.updateI();var baseline=HousingObservation.collect(10000,1000);
                require(Boolean.TRUE.equals(baseline.get("available")),"Baseline unavailable");
                var data=(Map<String,Object>)baseline.get("data");var rows=(List<Map<String,Object>>)data.get("rooms");
                require(Boolean.TRUE.equals(data.get("room_scan_complete")) && data.get("failed_room_reads").equals(0) && data.get("failed_rosters").equals(0),"Baseline incomplete");
                HomeInstance home=null;
                for(var row:rows){var room=SETT.ROOMS().map.getByIndex((Integer)row.get("room_id"));
                    if(room instanceof HomeInstance){var h=(HomeInstance)room;var it=h.it();
                        if(it!=null && it.width()==h.body().width() && it.height()==h.body().height()){home=h;break;}
                    }
                }
                require(home!=null,"Need a full ordinary furnishing footprint");
                var item=home.it();int x=home.body().x1(),y=home.body().y1();
                for(int dy=0;dy<item.height();dy++)for(int dx=0;dx<item.width();dx++)
                    if(item.get(dx,dy)!=null)require(home.is(x+dx,y+dy),"Furnishing crosses home footprint");
                var expected=new ArrayList<Map<String,Object>>();for(var r:rows)if(!r.get("room_id").equals(home.index()))expected.add(r);
                boolean directFailed=false;String failureKind=null;
                try{
                    SETT.ROOMS().fData.itemClear(home.serviceX(),home.serviceY(),home);
                    require(home.it()==null,"Public furnishing clear left item");
                    try{home.occupantsMax();}catch(RuntimeException error){directFailed=true;failureKind=error.getClass().getSimpleName();}
                    require(directFailed,"Expected real capacity getter failure");
                    var fault=HousingObservation.collect(10000,1000);require(Boolean.TRUE.equals(fault.get("available")) && "partial".equals(fault.get("coverage")),"Fault lost partial observation");
                    var partial=(Map<String,Object>)fault.get("data");
                    require(Boolean.TRUE.equals(partial.get("room_scan_complete")) && partial.get("failed_room_reads").equals(1) && partial.get("failed_rosters").equals(0),"Failure diagnostics mismatch");
                    require(partial.get("rooms").equals(expected),"Failed row fabricated or unrelated rows changed");
                    require(partial.get("ordinary_home_cohort_ledger").equals(data.get("ordinary_home_cohort_ledger")),"Unrelated ledger changed");
                }finally{
                    if(home.it()==null)SETT.ROOMS().fData.itemSet(x,y,item,home);
                }
                require(home.it()==item && JsonWriter.encode(HousingObservation.collect(10000,1000)).equals(JsonWriter.encode(baseline)),"Housing DTO not restored");
                require(GAME.updateI()==tick,"Fault transaction crossed update callback");
                Files.writeString(directory.resolve("stockpile-fixture.json"),JsonWriter.encode(object("passed",true,"fault_cases",1,"direct_getter_failure",failureKind,
                    "baseline_home_rows",rows.size(),"fault_home_rows",expected.size(),"failed_room_reads",1,"unrelated_rows_ledger_unchanged",true,"housing_output_restored",true,"same_callback",true)));
                written[0]=true;
            }catch(Exception failure){finished[0]=true;System.err.println("SMOKE_FIXTURE_FAILURE: "+failure);CORE.annihilate(failure);}
        });
    }
}
