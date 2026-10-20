import java.nio.file.*;
import java.util.*;
import game.GAME;
import settlement.main.SETT;
import settlement.room.home.HOME;
import settlement.room.home.house.HomeInstance;
import settlement.room.home.chamber.ChamberInstance;
import init.type.HGROUP;
import syx.assistant.JsonWriter;
import syx.assistant.UiContextCollector;
import syx.assistant.candidate.HousingObservation;
import static syx.assistant.StateCollector.object;

/** TEST ONLY: unchanged housing candidate observed inside real public scene/reload transitions. */
public final class StockpileScenario {
    static final Set<Integer> EXPECTED=Set.of(0,1,2,3,4,6,8,9), CITY=Set.of(0,1,2,6);
    static final Set<Integer> seen=new HashSet<>();
    public static void install(Path directory){
        seen.clear();String copied=System.getProperty("syx.smoke.copiedSave");PathCheck.validate(copied);
        SceneScenario.install(directory,Path.of(copied),()->observe(directory));
    }
    @SuppressWarnings("unchecked")
    static void observe(Path directory){
        try{
            int index=SceneScenario.phase;
            if(index==10){
                if(seen.size()!=8)throw new IllegalStateException("Incomplete housing scene observations");
                Files.writeString(directory.resolve("housing-scenes-clean-exit.json"),JsonWriter.encode(object("passed",true,"phases",8)));return;
            }
            if(!EXPECTED.contains(index) || seen.contains(index) || System.currentTimeMillis()-SceneScenario.began<2500)return;
            var scene=UiContextCollector.scene();String active=(String)scene.get("active_view");
            String expected=index==1?"settlement_battle":index==3 || index==4?"battle":index==8 || index==9?"world_generation":"settlement";
            if(!expected.equals(active))return;
            int tick=GAME.updateI();var candidate=HousingObservation.collect(10000,1000);boolean available=CITY.contains(index);
            if(!Boolean.valueOf(available).equals(candidate.get("available")))throw new IllegalStateException("Housing scope mismatch "+index);
            int homeRows=0,residentLinks=0,cohorts=0;
            if(available){
                var data=(Map<String,Object>)candidate.get("data");var rows=(List<Map<String,Object>>)data.get("rooms");
                if(!Boolean.TRUE.equals(data.get("room_scan_complete")))throw new IllegalStateException("Fixture scan incomplete");
                for(String k:List.of("failed_room_reads","failed_rosters","truncated_rosters"))if(!Integer.valueOf(0).equals(data.get(k)))throw new IllegalStateException("Unexpected fixture refusal");
                for(var row:rows){
                    var room=SETT.ROOMS().map.getByIndex((Integer)row.get("room_id"));HOME home=(HOME)room;
                    boolean ordinary=room instanceof HomeInstance;
                    if(!ordinary && !(room instanceof ChamberInstance))throw new IllegalStateException("Unsupported concrete home");
                    if(!row.get("occupants_reported").equals(home.occupants()) || !row.get("capacity_configured").equals(home.occupantsMax()) ||
                        ((Number)row.get("isolation_reported")).doubleValue()!=home.isolation() || !row.get("service_tile_x").equals(home.serviceX()) || !row.get("service_tile_y").equals(home.serviceY()))throw new IllegalStateException("Home scalar mismatch");
                    var roster=(Map<String,Object>)row.get("occupant_roster");var ids=(List<Integer>)roster.get("ids");
                    if(!Boolean.TRUE.equals(roster.get("available")) || Boolean.TRUE.equals(roster.get("truncated")) || ids.size()!=home.occupants())throw new IllegalStateException("Roster count mismatch");
                    for(int i=0;i<ids.size();i++)if(ids.get(i)!=home.occupant(i).id())throw new IllegalStateException("Resident ID mismatch");
                    residentLinks+=ids.size();homeRows++;
                }
                int directRows=0;for(int i=0;i<SETT.ROOMS().map.max();i++){var room=SETT.ROOMS().map.getByIndex(i);if(room instanceof HomeInstance || room instanceof ChamberInstance)directRows++;}
                if(directRows!=homeRows || homeRows==0)throw new IllegalStateException("Home scan mismatch");
                var ledger=(List<Map<String,Object>>)data.get("ordinary_home_cohort_ledger");
                if(ledger.size()!=HGROUP.all().size())throw new IllegalStateException("Cohort count mismatch");
                for(int i=0;i<ledger.size();i++){
                    var group=HGROUP.all().get(i);var r=ledger.get(i);
                    if(!r.get("group_id").equals(group.key) || !r.get("capacity_reported_raw").equals(SETT.ROOMS().HOME.total(group)) || !r.get("used_reported_raw").equals(SETT.ROOMS().HOME.used(group)))throw new IllegalStateException("Cohort mismatch");cohorts++;
                }
                if(!data.get("capacity_group_sum_reported_raw").equals(SETT.ROOMS().HOME.total(null)) || !data.get("used_group_sum_reported_raw").equals(SETT.ROOMS().HOME.used(null)))throw new IllegalStateException("Null ledger mismatch");
            }else if(candidate.get("data")!=null)throw new IllegalStateException("Unavailable housing leaked data");
            if(GAME.updateI()!=tick)throw new IllegalStateException("Housing read crossed update callback");
            Files.writeString(directory.resolve("housing-scene-"+index+".json"),JsonWriter.encode(object("phase",index,"observer_tick",tick,"same_callback",true,"candidate",candidate,"scene",scene,"home_rows_checked",homeRows,"resident_ids_checked",residentLinks,"cohort_rows_checked",cohorts)));
            seen.add(index);if(index==0)Files.writeString(directory.resolve("stockpile-fixture.json"),"{\"passed\":true}\n");
        }catch(Exception failure){throw new IllegalStateException("Housing scene fixture failed",failure);}
    }
}
