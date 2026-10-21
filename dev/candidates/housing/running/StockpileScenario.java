import java.nio.file.*;
import java.util.*;
import game.GAME;
import game.time.TIME;
import settlement.main.SETT;
import settlement.room.home.HOME;
import settlement.room.home.house.HomeInstance;
import settlement.room.home.chamber.ChamberInstance;
import init.type.HGROUP;
import snake2d.CORE;
import syx.assistant.JsonWriter;
import syx.assistant.StateCollector;
import static syx.assistant.StateCollector.object;

/** TEST ONLY: passive production observations while an isolated copied city's simulation advances. */
public final class StockpileScenario {
    @SuppressWarnings("unchecked")
    public static void install(Path directory){
        view.main.VIEW.s().activate();GAME.SPEED.speedSet(1);
        long began=System.nanoTime();long[] last={0};int[] priorTick={-1};boolean[] written={false},finished={false};
        double[] priorSeconds={-1};
        String session=UUID.randomUUID().toString();List<Object> samples=new ArrayList<>();
        GAME.addAfterUpdate(()->{
            if(finished[0])return;
            try{
                if(Files.exists(directory.resolve("verifier.done"))){
                    if(!written[0])throw new IllegalStateException("Premature completion");
                    Files.writeString(directory.resolve("housing-running-clean-exit.json"),JsonWriter.encode(object("passed",true,"samples",6)));
                    finished[0]=true;CORE.annihilate();return;
                }
                long now=System.nanoTime();if(now-began>100_000_000_000L)throw new IllegalStateException("Running housing timeout");
                int tick=GAME.updateI();double seconds=TIME.currentSecond();
                if(written[0] || now-began<5_000_000_000L || now-last[0]<500_000_000L || tick<=priorTick[0] || seconds<=priorSeconds[0])return;
                int sequence=samples.size()+1;var observation=StateCollector.collect(session,sequence);
                var housing=(Map<String,Object>)((Map<String,Object>)observation.get("domains")).get("housing");
                var homeRecords=(Map<String,Object>)((Map<String,Object>)housing.get("data")).get("home_records");
                if(!Boolean.TRUE.equals(homeRecords.get("available")))throw new IllegalStateException("Running city homes unavailable");
                var data=(Map<String,Object>)homeRecords.get("data");var rooms=(List<Map<String,Object>>)data.get("rooms");
                if(rooms.isEmpty() || !Boolean.TRUE.equals(data.get("room_scan_complete")) || !Integer.valueOf(0).equals(data.get("failed_room_reads")) || !Integer.valueOf(0).equals(data.get("failed_rosters")))throw new IllegalStateException("Need complete successful fixture enumeration");
                int directRooms=0;for(int i=0;i<SETT.ROOMS().map.max();i++){var r=SETT.ROOMS().map.getByIndex(i);if(r instanceof HomeInstance || r instanceof ChamberInstance)directRooms++;}
                if(rooms.size()!=directRooms)throw new IllegalStateException("Registry enumeration differs");
                int rosterCount=0;
                for(var row:rooms){
                    var room=SETT.ROOMS().map.getByIndex((Integer)row.get("room_id"));
                    if(!(room instanceof HomeInstance) && !(room instanceof ChamberInstance))throw new IllegalStateException("Unsupported home type");
                    HOME home=(HOME)room;
                    if(!row.get("occupants_reported").equals(home.occupants()) || !row.get("capacity_configured").equals(home.occupantsMax()) || ((Number)row.get("isolation_reported")).doubleValue()!=home.isolation() || !row.get("service_tile_x").equals(home.serviceX()) || !row.get("service_tile_y").equals(home.serviceY()))throw new IllegalStateException("Running scalar mismatch");
                    var roster=(Map<String,Object>)row.get("occupant_roster");
                    if(!Boolean.TRUE.equals(roster.get("available")) || Boolean.TRUE.equals(roster.get("truncated")))throw new IllegalStateException("Need complete fixture roster");
                    var ids=(List<Integer>)roster.get("ids");if(ids.size()!=home.occupants())throw new IllegalStateException("Roster/count mismatch");
                    for(int i=0;i<ids.size();i++)if(home.occupant(i)==null || home.occupant(i).id()!=ids.get(i))throw new IllegalStateException("Running roster mismatch");
                    rosterCount+=ids.size();
                }
                var ledger=(List<Map<String,Object>>)data.get("ordinary_home_cohort_ledger");
                if(ledger.size()!=HGROUP.all().size())throw new IllegalStateException("Cohort enumeration mismatch");
                for(int i=0;i<ledger.size();i++){
                    var group=HGROUP.all().get(i);var row=ledger.get(i);
                    if(!row.get("group_id").equals(group.key) || !row.get("capacity_reported_raw").equals(SETT.ROOMS().HOME.total(group)) || !row.get("used_reported_raw").equals(SETT.ROOMS().HOME.used(group)))throw new IllegalStateException("Running cohort mismatch");
                }
                if(!data.get("capacity_group_sum_reported_raw").equals(SETT.ROOMS().HOME.total(null)) || !data.get("used_group_sum_reported_raw").equals(SETT.ROOMS().HOME.used(null)) || GAME.updateI()!=tick)throw new IllegalStateException("Sum/callback mismatch");
                String name="housing-running-"+sequence+".json";
                Files.writeString(directory.resolve(name),JsonWriter.encode(observation));
                samples.add(object("file",name,"tick",tick,"game_seconds",seconds,"home_rows",rooms.size(),"roster_links",rosterCount,"same_callback_direct_parity",true));
                last[0]=now;priorTick[0]=tick;priorSeconds[0]=seconds;
                if(sequence==6){
                    GAME.SPEED.speedSet(0);
                    Files.writeString(directory.resolve("stockpile-fixture.json"),JsonWriter.encode(object("passed",true,"samples",samples,"sample_count",6,"simulation_speed_during_sampling",1,"sample_interval_min_ns",500000000)));
                    written[0]=true;
                }
            }catch(Exception failure){finished[0]=true;System.err.println("SMOKE_FIXTURE_FAILURE: "+failure);CORE.annihilate(failure);}
        });
    }
}
