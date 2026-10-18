import java.nio.file.*;
import java.util.*;
import game.GAME;
import init.resources.RESOURCE;
import init.resources.RESOURCES;
import settlement.main.SETT;
import settlement.room.infra.stockpile.StockpileInstance;
import settlement.room.infra.stockpile.StockpileTally;
import snake2d.CORE;
import syx.assistant.JsonWriter;
import syx.assistant.StateCollector;
import static syx.assistant.StateCollector.object;

/** TEST ONLY: stockpile reader parity in a paused copied city; no saves or logistics actions. */
public final class StockpileScenario {
    private static int[] values(StockpileTally tally, RESOURCE resource, StockpileInstance room) {
        int ri=resource.index();
        StockpileTally.TallyData[] fields={tally.crates,tally.space,tally.spaceReserved,tally.amount,tally.amountReserved};
        int[] values=new int[fields.length];
        for(int i=0;i<fields.length;i++) {
            values[i]=room==null?fields[i].total(ri):fields[i].get(ri,room);
            int other=room==null?fields[i].total(resource):fields[i].get(resource,room);
            if(values[i]!=other)throw new IllegalStateException("Integer/resource overload mismatch");
        }
        return values;
    }
    public static void install(Path directory) {
        GAME.SPEED.speedSet(0);
        long began=System.currentTimeMillis();boolean[] written={false};
        GAME.addAfterUpdate(()->{
            try {
                if(!written[0] && System.currentTimeMillis()-began>10000) {
                    written[0]=true;
                    if(!SETT.exists() || SETT.WORLD_AREA().isBattle || !world.WORLD.GEN().isDone)
                        throw new IllegalStateException("Requires copied completed campaign city");
                    if(RESOURCES.ALL().size()>1000 || SETT.ROOMS().STOCKPILE.all().size()>100)
                        throw new IllegalStateException("Stockpile probe resource/room bounds exceeded");
                    var tally=SETT.ROOMS().STOCKPILE.tally();
                    List<Object> totals=new ArrayList<>(),rooms=new ArrayList<>();
                    long[][] sums=new long[RESOURCES.ALL().size()][5];
                    int zeroCapacity=0,zeroRoomCapacity=0,zeroAggregateRooms=0,active=0,inactive=0,overloads=0;
                    int[] positiveTotals=new int[5];int assignedCrates=0,totalCrates=0;
                    for(var room:SETT.ROOMS().STOCKPILE.all()) {
                        if(rooms.size()+RESOURCES.ALL().size()>10000)
                            throw new IllegalStateException("Stockpile probe row bound exceeded");
                        if(room.active())active++;else inactive++;
                        int assigned=0;double storedSum=0,capacitySum=0;
                        for(RESOURCE resource:RESOURCES.ALL()) {
                            int[] v=values(tally,resource,room);overloads+=5;
                            for(int i=0;i<5;i++)sums[resource.index()][i]+=v[i];
                            assigned+=v[0];storedSum+=v[3];capacitySum+=v[1];
                            double expected=v[1]==0?1.0:((double)v[3]-v[4])/v[1];
                            if(Math.abs(room.storedD(resource)-expected)>1e-12)
                                throw new IllegalStateException("Per-resource available ratio mismatch");
                            if(v[1]==0)zeroRoomCapacity++;
                            rooms.add(object("room_id",room.index(),"active",room.active(),"resource_id",resource.key,
                                "crates",v[0],"space",v[1],"space_reserved",v[2],"amount",v[3],"amount_reserved",v[4]));
                        }
                        if(capacitySum==0)zeroAggregateRooms++;
                        if(Math.abs(room.getUsedSpace()-(capacitySum==0?0:storedSum/capacitySum))>1e-12)
                            throw new IllegalStateException("Room aggregate fullness mismatch");
                        if(assigned>room.totalCrates())throw new IllegalStateException("Assigned crates exceed room crate count");
                        assignedCrates+=assigned;totalCrates+=room.totalCrates();
                    }
                    for(RESOURCE resource:RESOURCES.ALL()) {
                        int[] v=values(tally,resource,null);overloads+=5;
                        for(int i=0;i<5;i++) {
                            if(sums[resource.index()][i]!=v[i])throw new IllegalStateException("Per-room sum differs from global tally");
                            if(v[i]>0)positiveTotals[i]++;
                        }
                        if(v[1]==0)zeroCapacity++;
                        if(Math.abs(tally.load(resource)-(v[1]==0?1.0:(double)v[3]/v[1]))>1e-12)
                            throw new IllegalStateException("Global resource load mismatch");
                        totals.add(object("resource_id",resource.key,"crates",v[0],"space",v[1],
                            "space_reserved",v[2],"amount",v[3],"amount_reserved",v[4]));
                    }
                    if(totals.isEmpty() || rooms.isEmpty() || positiveTotals[3]==0 || zeroCapacity==0)
                        throw new IllegalStateException("Copied city lacks positive storage or zero-capacity case");
                    Map<String,Object> observation=StateCollector.collect(UUID.randomUUID().toString(),1);
                    // Controlled public lifecycle action on this disposable copied room only.
                    // Baseline observation above precedes the action; no fixture save is written.
                    var controlled=SETT.ROOMS().STOCKPILE.all().get(0);
                    if(!controlled.active())throw new IllegalStateException("Controlled room must begin active");
                    List<int[]> baseline=new ArrayList<>();
                    for(RESOURCE resource:RESOURCES.ALL())baseline.add(values(tally,resource,controlled));
                    controlled.deactivate();
                    try {
                        if(controlled.active())throw new IllegalStateException("Room did not deactivate");
                        for(RESOURCE resource:RESOURCES.ALL())
                            if(!Arrays.equals(baseline.get(resource.index()),values(tally,resource,controlled)))
                                throw new IllegalStateException("Stored tally unexpectedly changes at immediate deactivation");
                    } finally {controlled.activate(true);}
                    if(!controlled.active())throw new IllegalStateException("Controlled room was not restored active");
                    Files.createDirectories(directory);
                    Files.writeString(directory.resolve("stockpile-observation.json"),JsonWriter.encode(observation));
                    Files.writeString(directory.resolve("stockpile-fixture.json"),JsonWriter.encode(object(
                        "passed",true,"totals",totals,"room_rows",rooms,"resource_count",totals.size(),
                        "room_count",active+inactive,"active_rooms",active,"inactive_rooms",inactive,
                        "zero_capacity_resources",zeroCapacity,"zero_capacity_aggregate_rooms",zeroAggregateRooms,"zero_capacity_room_resource_pairs",zeroRoomCapacity,
                        "positive_tallies",object("crates",positiveTotals[0],"space",positiveTotals[1],
                            "space_reserved",positiveTotals[2],"amount",positiveTotals[3],"amount_reserved",positiveTotals[4]),
                        "assigned_crates",assignedCrates,"total_crates",totalCrates,"overload_comparisons",overloads,
                        "per_room_sum_global_parity",true,"resource_zero_denominator_default_one",true,
                        "controlled_inactive_room_stored_tallies_unchanged",true,"controlled_reactivation_restored",true)));
                    System.err.println("STOCKPILE TEST: direct getter candidate checks ready");
                }
                if(Files.exists(directory.resolve("verifier.done")) || System.currentTimeMillis()-began>110000)CORE.annihilate();
            }catch(Exception error){CORE.annihilate(error);}
        });
    }
}
