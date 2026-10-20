import java.nio.file.*;
import java.util.*;
import game.GAME;
import settlement.main.SETT;
import settlement.room.home.HOME;
import settlement.room.home.house.HomeInstance;
import settlement.room.home.chamber.ChamberInstance;
import settlement.stats.STATS;
import init.type.HGROUP;
import snake2d.CORE;
import syx.assistant.JsonWriter;
import syx.assistant.candidate.HousingObservation;
import static syx.assistant.StateCollector.object;

/** TEST ONLY: unmodified paused copied city, fixed public getter parity and assignment joins. */
public final class StockpileScenario {
    @SuppressWarnings("unchecked")
    public static void install(Path directory){
        GAME.SPEED.speedSet(0);view.main.VIEW.s().activate();long began=System.nanoTime();long[] last={0};boolean[] written={false},finished={false};
        boolean[] capacityDifference={false},usedDifference={false};
        List<Long> collectTimes=new ArrayList<>();int[] houses={0},chambers={0},rosterIds={0},assignmentMatches={0};String[] first={null};
        GAME.addAfterUpdate(()->{
            if(finished[0])return;
            try{
                if(Files.exists(directory.resolve("verifier.done"))){
                    if(!written[0])throw new IllegalStateException("Premature verifier completion");
                    Files.writeString(directory.resolve("housing-clean-exit.json"),JsonWriter.encode(object("passed",true,"samples",32)));
                    finished[0]=true;CORE.annihilate();return;
                }
                long now=System.nanoTime();if(now-began>100_000_000_000L)throw new IllegalStateException("Housing verifier timeout");
                if(written[0] || now-began<5_000_000_000L || now-last[0]<100_000_000L)return;last[0]=now;
                long start=System.nanoTime();var collected=HousingObservation.collect(10000,1000);long end=System.nanoTime();
                if(!Boolean.TRUE.equals(collected.get("available")))throw new IllegalStateException("City housing unavailable");
                Map<String,Object> data=(Map<String,Object>)collected.get("data");var rows=(List<Map<String,Object>>)data.get("rooms");
                if(!(Boolean)data.get("room_scan_complete") || !Integer.valueOf(0).equals(data.get("failed_room_reads")) || !Integer.valueOf(0).equals(data.get("failed_rosters")))throw new IllegalStateException("Incomplete/error fixture homes");
                if(rows.isEmpty())throw new IllegalStateException("Need naturally existing copied-city homes");
                Set<Integer> roomIds=new HashSet<>();int ordinary=0,noble=0,ids=0,matched=0;long uniqueCapacity=0,uniqueAssigned=0;
                for(var row:rows){
                    int rid=(Integer)row.get("room_id");if(!roomIds.add(rid))throw new IllegalStateException("Duplicate physical home");
                    var room=SETT.ROOMS().map.getByIndex(rid);HOME home=(HOME)room;
                    if(room instanceof HomeInstance){ordinary++;uniqueCapacity+=home.occupantsMax();uniqueAssigned+=home.occupants();}else if(room instanceof ChamberInstance)noble++;else throw new IllegalStateException("Wrong home type");
                    if(!row.get("occupants_reported").equals(home.occupants()) || !row.get("capacity_configured").equals(home.occupantsMax()) || ((Number)row.get("isolation_reported")).doubleValue()!=home.isolation())throw new IllegalStateException("Public scalar mismatch");
                    var roster=(Map<String,Object>)row.get("occupant_roster");if(!Boolean.TRUE.equals(roster.get("available")) || Boolean.TRUE.equals(roster.get("truncated")))throw new IllegalStateException("Incomplete fixture roster");
                    var entries=(List<Integer>)roster.get("ids");if(entries.size()!=home.occupants())throw new IllegalStateException("Roster/count mismatch");
                    for(int i=0;i<entries.size();i++){
                        var h=home.occupant(i);if(h.id()!=entries.get(i))throw new IllegalStateException("Resident identity mismatch");
                        // Public scratch coordinate is copied immediately, never retained/exported as an engine handle.
                        var coo=STATS.HOME().GETTER.hCoo(h);if(coo!=null && coo.x()==home.serviceX() && coo.y()==home.serviceY())matched++;ids++;
                    }
                }
                int directCount=0;for(int i=0;i<SETT.ROOMS().map.max();i++){var r=SETT.ROOMS().map.getByIndex(i);if(r instanceof HomeInstance || r instanceof ChamberInstance)directCount++;}
                if(directCount!=rows.size())throw new IllegalStateException("Physical home scan mismatch");
                var ledger=(List<Map<String,Object>>)data.get("ordinary_home_cohort_ledger");if(ledger.size()!=HGROUP.all().size())throw new IllegalStateException("Cohort count mismatch");
                long capacity=0,used=0;for(int i=0;i<ledger.size();i++){
                    var group=HGROUP.all().get(i);var row=ledger.get(i);int c=SETT.ROOMS().HOME.total(group),u=SETT.ROOMS().HOME.used(group);
                    if(!row.get("group_id").equals(group.key) || !row.get("capacity_reported_raw").equals(c) || !row.get("used_reported_raw").equals(u))throw new IllegalStateException("Cohort getter mismatch");capacity+=c;used+=u;
                }
                if(capacity!=SETT.ROOMS().HOME.total(null) || used!=SETT.ROOMS().HOME.used(null))throw new IllegalStateException("Group-sum ledger mismatch");
                String encoded=JsonWriter.encode(collected);if(first[0]==null){first[0]=encoded;houses[0]=ordinary;chambers[0]=noble;rosterIds[0]=ids;assignmentMatches[0]=matched;capacityDifference[0]=capacity!=uniqueCapacity;usedDifference[0]=used!=uniqueAssigned;}
                else if(!first[0].equals(encoded))throw new IllegalStateException("Paused read changed housing output");
                collectTimes.add(end-start);
                if(collectTimes.size()==32){
                    Files.writeString(directory.resolve("stockpile-fixture.json"),JsonWriter.encode(object("passed",true,"ordinary_homes",houses[0],"noble_chambers",chambers[0],"resolved_roster_ids",rosterIds[0],"assignment_coordinate_matches",assignmentMatches[0],"cohort_rows",ledger.size(),"capacity_group_sum_differs_from_unique_ordinary_home_sum",capacityDifference[0],"used_group_sum_differs_from_unique_ordinary_home_sum",usedDifference[0],"samples",32,"collector_ns",collectTimes,"candidate_bytes",encoded.getBytes(java.nio.charset.StandardCharsets.UTF_8).length)));
                    written[0]=true;
                }
            }catch(Exception failure){finished[0]=true;System.err.println("SMOKE_FIXTURE_FAILURE: "+failure);CORE.annihilate(failure);}
        });
    }
}
