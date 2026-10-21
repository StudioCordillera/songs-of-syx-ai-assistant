import java.nio.file.*;
import java.util.*;
import game.GAME;
import settlement.main.SETT;
import settlement.stats.STATS;
import settlement.entity.humanoid.Humanoid;
import settlement.room.home.chamber.ChamberInstance;
import settlement.room.main.util.RoomInit;
import snake2d.CORE;
import syx.assistant.JsonWriter;
import syx.assistant.HousingObservation;
import syx.assistant.StateCollector;
import static syx.assistant.StateCollector.object;

/** TEST ONLY: create/assign/restore/remove one real chamber in a disposable paused copied city. Never saves. */
public final class StockpileScenario {
    @SuppressWarnings("unchecked")
    private static Map<String,Object> data(int scans,int rows){
        var result=HousingObservation.collect(scans,rows);
        if(!Boolean.TRUE.equals(result.get("available")))throw new IllegalStateException("Housing unavailable");
        var d=(Map<String,Object>)result.get("data");
        for(String key:List.of("failed_room_reads","failed_rosters","truncated_rosters"))
            if(!Integer.valueOf(0).equals(d.get(key)))throw new IllegalStateException("Unexpected read failure or cap");
        return d;
    }
    @SuppressWarnings("unchecked")
    private static List<Map<String,Object>> rows(Map<String,Object> data){return (List<Map<String,Object>>)data.get("rooms");}
    private static void require(boolean ok,String why){if(!ok)throw new IllegalStateException(why);}
    public static void install(Path directory){
        GAME.SPEED.speedSet(0);view.main.VIEW.s().activate();long began=System.nanoTime();boolean[] done={false},finished={false};
        GAME.addAfterUpdate(()->{
            if(finished[0])return;
            try{
                if(Files.exists(directory.resolve("verifier.done"))){
                    require(done[0],"Premature completion");
                    Files.writeString(directory.resolve("housing-chamber-clean-exit.json"),JsonWriter.encode(object("passed",true,"created_empty_chambers",1,"removed_chambers",1)));
                    finished[0]=true;CORE.annihilate();return;
                }
                require(System.nanoTime()-began<100_000_000_000L,"Housing chamber timeout");
                if(done[0] || System.nanoTime()-began<5_000_000_000L)return;
                var baseline=data(10000,1000);require(Boolean.TRUE.equals(baseline.get("room_scan_complete")),"Incomplete baseline");
                var blueprint=SETT.ROOMS().CHAMBER;var item=blueprint.constructor().item(1);
                require(item!=null && item.width()==6 && item.height()==7,"Unexpected paired chamber furnishing");
                ChamberInstance chamber=null;int candidates=0;
                search:for(int y=8;y<SETT.THEIGHT-16;y+=8)for(int x=8;x<SETT.TWIDTH-16;x+=8){
                    require(++candidates<=10000,"Placement search cap");boolean free=true;
                    for(int dy=0;dy<item.height();dy++)for(int dx=0;dx<item.width();dx++)
                        if(SETT.ROOMS().map.get(x+dx,y+dy)!=null || SETT.PATH().availability.get(x+dx,y+dy).player<=0 || SETT.ROOMS().fData.item.get(x+dx,y+dy)!=null)free=false;
                    if(!free)continue;
                    var area=SETT.ROOMS().tmpArea(StockpileScenario.class);
                    for(int dy=0;dy<item.height();dy++)for(int dx=0;dx<item.width();dx++)if(item.get(dx,dy)!=null)area.set(x+dx,y+dy);
                    SETT.ROOMS().fData.itemSet(x,y,item,area.room());
                    chamber=(ChamberInstance)blueprint.constructor().create(area,new RoomInit(blueprint,0));
                    SETT.ROOMS().stats.finished().add(chamber.mX(),chamber.mY());break search;
                }
                require(chamber!=null,"No placement found");int id=chamber.index();
                var created=data(10000,1000);require(Boolean.TRUE.equals(created.get("room_scan_complete")),"Incomplete created scan");
                var matches=new ArrayList<Map<String,Object>>();for(var r:rows(created))if(r.get("room_id").equals(id))matches.add(r);
                require(matches.size()==1 && rows(created).size()==rows(baseline).size()+1,"Created chamber missing/duplicated");var r=matches.get(0);
                require("noble_chamber".equals(r.get("kind")) && "resolved_chamber_occupant_count".equals(r.get("occupant_count_kind")),"Chamber count provenance");
                require(r.get("occupants_reported").equals(0) && chamber.occupants()==0 && chamber.occupant(0)==null && chamber.occupant(1)==null,"Empty resolved roster");
                require(r.get("capacity_configured").equals(1) && chamber.occupantsMax()==1 && r.get("odd_occupants_stored")==null,"Chamber capacity/ordinary-only field");
                require(r.get("service_tile_x").equals(chamber.serviceX()) && r.get("service_tile_y").equals(chamber.serviceY()),"Service coordinates");
                require("conditional_room_instance_value".equals(r.get("isolation_kind")) && ((Number)r.get("isolation_reported")).doubleValue()==chamber.isolation(),"Isolation parity");
                var roster=(Map<?,?>)r.get("occupant_roster");require(Boolean.TRUE.equals(roster.get("available")) && ((List<?>)roster.get("ids")).isEmpty() && Boolean.FALSE.equals(roster.get("truncated")),"Empty roster DTO");
                require(created.get("ordinary_home_cohort_ledger").equals(baseline.get("ordinary_home_cohort_ledger")),"Chamber affected ordinary ledger");
                var capped=data(10000,1);require(rows(capped).size()==1 && rows(capped).get(0).equals(rows(created).get(0)) && Boolean.FALSE.equals(capped.get("room_scan_complete")),"Real row bound");
                require(id>0 && id<10000,"Fixture room outside prefix budgets");
                for(int bound:new int[]{1,id,id+1}){
                    var prefix=data(bound,1000);var expected=new ArrayList<Map<String,Object>>();
                    for(var full:rows(created))if(((Number)full.get("room_id")).intValue()<bound)expected.add(full);
                    require(rows(prefix).equals(expected) && prefix.get("room_slots_scanned").equals(bound),"Scan prefix differs");
                    require(prefix.get("room_scan_complete").equals(bound==((Number)prefix.get("room_map_size")).intValue()),"Scan completeness mismatch");
                }
                // TEST ONLY: copied city has no existing noble; create/promote a fresh subject.
                var firstRoom=SETT.ROOMS().map.getByIndex((Integer)rows(baseline).get(0).get("room_id"));
                var example=((settlement.room.home.HOME)firstRoom).occupant(0);
                require(example!=null,"Need a real race example");
                Humanoid noble=new Humanoid(chamber.serviceX()*init.constant.C.TILE_SIZE+init.constant.C.TILE_SIZEH,
                    chamber.serviceY()*init.constant.C.TILE_SIZE+init.constant.C.TILE_SIZEH,example.race(),init.type.HTYPES.SUBJECT(),init.type.CAUSE_ARRIVES.IMMIGRATED());
                require(!noble.isRemoved() && SETT.ENTITIES().getByID(noble.id())==noble,"New fixture subject not registered");
                noble.nobleSet();
                require(noble.noble()!=null && noble.indu().hType()==init.type.HTYPES.NOBILITY() && chamber.canOccupy(noble),"Public noble promotion failed");
                var priorHome=STATS.HOME().GETTER.get(noble,StockpileScenario.class);
                require(priorHome==null,"Fresh promoted fixture noble unexpectedly has a home");
                String session=UUID.randomUUID().toString();
                try{
                    STATS.HOME().GETTER.set(noble,chamber);
                    require(chamber.occupant()==noble && chamber.occupants()==1,"Assignment did not resolve");
                    var occupied=data(10000,1000);Map<String,Object> occupiedRow=null;
                    for(var row:rows(occupied))if(row.get("room_id").equals(id))occupiedRow=row;
                    require(occupiedRow!=null && occupiedRow.get("occupants_reported").equals(1),"Occupied chamber missing");
                    var assigned=(Map<?,?>)occupiedRow.get("occupant_roster");
                    require(Boolean.TRUE.equals(assigned.get("available")) && ((List<?>)assigned.get("ids")).equals(List.of(noble.id())),"Assigned roster mismatch");
                    var coo=STATS.HOME().GETTER.hCoo(noble);
                    require(coo!=null && coo.x()==chamber.serviceX() && coo.y()==chamber.serviceY(),"Assigned coordinate mismatch");
                    require("resolved_chamber_occupant_count".equals(occupiedRow.get("occupant_count_kind")),"Occupied provenance mismatch");
                    Files.writeString(directory.resolve("housing-occupied-observation.json"),JsonWriter.encode(StateCollector.collect(session,1)));
                }finally{STATS.HOME().GETTER.set(noble,priorHome);}
                require(chamber.occupants()==0 && STATS.HOME().GETTER.get(noble,StockpileScenario.class)==priorHome,"Prior assignment not restored");
                require(rows(data(10000,1000)).equals(rows(created)),"Restored home rows differ");
                chamber.remove(chamber.mX(),chamber.mY(),false,StockpileScenario.class,true).clearAndUpdate();
                require(!chamber.exists() && SETT.ROOMS().map.getByIndex(id)==null,"Chamber removal failed");var removed=data(10000,1000);
                require(rows(removed).equals(rows(baseline)) && removed.get("ordinary_home_cohort_ledger").equals(baseline.get("ordinary_home_cohort_ledger")),"Baseline home rows/ledger not restored");
                Files.writeString(directory.resolve("housing-after-chamber-observation.json"),JsonWriter.encode(StateCollector.collect(session,2)));
                Files.writeString(directory.resolve("stockpile-fixture.json"),JsonWriter.encode(object("passed",true,"created_empty_chambers",1,"removed_chambers",1,"ordinary_baseline_rows",rows(baseline).size(),"empty_chamber_scalar_roster_parity",true,"ordinary_ledger_unchanged",true,"row_budget_cases",1,"scan_prefix_cases",3,"baseline_rows_restored",true,"occupied_chamber_cases",1,"prior_noble_assignment_restored",true,"test_subjects_created_promoted",1,"placement_candidates_checked",candidates)));
                done[0]=true;
            }catch(Exception failure){finished[0]=true;System.err.println("SMOKE_FIXTURE_FAILURE: "+failure);CORE.annihilate(failure);}
        });
    }
}
