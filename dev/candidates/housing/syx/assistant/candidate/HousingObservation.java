package syx.assistant.candidate;

import java.util.*;
import settlement.main.SETT;
import settlement.room.home.HOME;
import settlement.room.home.house.HomeInstance;
import settlement.room.home.chamber.ChamberInstance;
import init.type.HGROUP;
import static syx.assistant.StateCollector.object;

/** Unregistered fixed public reader. Use only on GAME.addAfterUpdate; no engine handles escape. */
public final class HousingObservation {
    private HousingObservation(){}
    public static Map<String,Object> collect(int scanLimit,int rowLimit){
        if(scanLimit<1 || scanLimit>10000 || rowLimit<1 || rowLimit>1000)throw new IllegalArgumentException("Invalid housing budgets");
        try{
            if(!SETT.exists() || SETT.WORLD_AREA().isBattle || !world.WORLD.GEN().isDone)
                return object("available",false,"coverage","unavailable","scope","instantiated_city_home_records","data",null,"reason","No completed instantiated campaign city");
            int size=SETT.ROOMS().map.max(),scanned=0,failed=0,rosterFailed=0,rosterTruncated=0;List<Object> rows=new ArrayList<>();
            while(scanned<size && scanned<scanLimit && rows.size()<rowLimit){
                var room=SETT.ROOMS().map.getByIndex(scanned++);
                if(!(room instanceof HomeInstance) && !(room instanceof ChamberInstance))continue;
                try{
                    HOME home=(HOME)room;boolean ordinary=room instanceof HomeInstance;
                    int count=home.occupants(),capacity=home.occupantsMax();double isolation=home.isolation();
                    if(!Double.isFinite(isolation) || isolation<0 || isolation>1)throw new IllegalStateException("Invalid reported isolation");
                    Map<String,Object> roster;
                    try{
                        if(count<0)throw new IllegalStateException("Negative reported occupant count");
                        List<Integer> ids=new ArrayList<>();
                        for(int i=0;i<Math.min(count,64);i++){
                            var h=home.occupant(i);if(h==null)throw new IllegalStateException("Unresolved recorded occupant");ids.add(h.id());
                        }
                        boolean truncated=count>64;if(truncated)rosterTruncated++;
                        roster=object("available",true,"coverage","partial","ids",ids,"truncated",truncated,"id_limit",64);
                    }catch(RuntimeException error){rosterFailed++;roster=object("available",false,"coverage","unavailable","ids",null,"reason",error.getClass().getSimpleName());}
                    rows.add(object("room_id",room.index(),"blueprint_id",room.blueprint().key,"kind",ordinary?"ordinary_home":"noble_chamber",
                        "service_tile_x",home.serviceX(),"service_tile_y",home.serviceY(),"occupants_reported",count,"capacity_configured",capacity,
                        "occupant_count_kind",ordinary?"stored_assigned_count":"resolved_chamber_occupant_count",
                        "odd_occupants_stored",ordinary?((HomeInstance)room).occupantsOdd():null,
                        "isolation_reported",isolation,"isolation_kind",ordinary?"stored_eight_bit_fraction":"conditional_room_instance_value",
                        "occupant_roster",roster));
                }catch(RuntimeException failure){failed++;}
            }
            if(HGROUP.all().size()>1000)throw new IllegalStateException("Cohort registry budget exceeded");
            List<Object> ledger=new ArrayList<>();var blueprint=SETT.ROOMS().HOME;
            for(var group:HGROUP.all())ledger.add(object("group_id",group.key,"class_id",group.type.key,"race_id",group.race.key,
                "capacity_reported_raw",blueprint.total(group),"used_reported_raw",blueprint.used(group)));
            return object("available",true,"coverage","partial","scope","instantiated_city_home_records","data",object(
                "rooms",rows,"room_slots_scanned",scanned,"room_map_size",size,"scan_limit",scanLimit,"row_limit",rowLimit,
                "room_scan_complete",scanned==size,"failed_room_reads",failed,"failed_rosters",rosterFailed,"truncated_rosters",rosterTruncated,
                "ordinary_home_cohort_ledger",ledger,"capacity_group_sum_reported_raw",blueprint.total(null),"used_group_sum_reported_raw",blueprint.used(null)),
                "reason","Home IDs are reusable room slots; rosters are recorded/resolved assignments, not physical presence. Cohort ledgers can count one empty home for multiple eligible groups. Null-group sums are not unique beds or free housing. No eligibility/use/resource/cache/light action or mutable policy handle is read.");
        }catch(RuntimeException failure){return object("available",false,"coverage","unavailable","scope","instantiated_city_home_records","data",null,"reason",failure.getClass().getSimpleName());}
    }
}
