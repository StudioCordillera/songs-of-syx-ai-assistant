import game.GAME;
import init.resources.*;
import init.trade.TR;
import world.WORLD;
import world.region.RD;
import world.map.regions.Region;
import snake2d.CORE;
import syx.assistant.JsonWriter;
import java.nio.file.*;
import java.time.Instant;
import java.util.*;

/** TEST ONLY: held copied-world counter, independent getters and public scene follow-up. */
public final class RegionalLiveScenario {
    public static void install(Path directory,Path save) {
        GAME.SPEED.speedSet(0);view.main.VIEW.s().activate();
        if(WORLD.REGIONS().active().size()<100 || RESOURCES.ALL().size()>100 || RESOURCES.ALL().size()*100<=4096)
            throw new IllegalStateException("Fixture requires a >4096-cell finite selection");
        List<Integer> ids=new ArrayList<>();for(Region r:WORLD.REGIONS().active())if(ids.size()<100)ids.add(r.index());
        List<String> keys=new ArrayList<>();for(RESOURCE r:RESOURCES.ALL())keys.add(r.key);
        Region target=WORLD.REGIONS().active().get(99);RESOURCE targetResource=RESOURCES.ALL().get(RESOURCES.ALL().size()-1);
        var counter=RD.OUTPUT().get(TR.get(targetResource)).yearlyAccumilation;int original=counter.get(target);
        long began=System.nanoTime();boolean[] written={false},started={false};
        GAME.addAfterUpdate(()->{
            if(started[0])return;
            try {
                if(Files.exists(directory.resolve("live-regional.done"))) {
                    counter.set(target,original);if(counter.get(target)!=original)throw new IllegalStateException("Counter restoration failed");
                    Files.writeString(directory.resolve("live-regional-restored.json"),JsonWriter.encode(Map.of("passed",true,"controlled_counter_restored",true)));
                    started[0]=true;SceneScenario.install(directory,save);return;
                }
                if(System.nanoTime()-began>150_000_000_000L)throw new IllegalStateException("Live regional verifier timed out");
                if(written[0] || System.nanoTime()-began<5_000_000_000L)return;
                counter.set(target,Integer.MAX_VALUE);
                List<Object> rows=new ArrayList<>();
                for(int rid:ids) {
                    Region region=null;for(Region r:WORLD.REGIONS().active())if(r.index()==rid)region=r;
                    var owner=region.faction();
                    for(RESOURCE resource:RESOURCES.ALL()) {
                        var output=RD.OUTPUT().get(TR.get(resource));
                        Map<String,Object> row=new LinkedHashMap<>();row.put("region_id",rid);row.put("resource_id",resource.key);
                        row.put("accrued_output_raw",output.yearlyAccumilation.get(region));
                        row.put("days_until_configured_output",output.daysUntilDailydelivery());
                        row.put("reference_id","resource:"+resource.key);row.put("faction_id",owner==null?null:owner.index());rows.add(row);
                    }
                }
                Set<Integer> active=new HashSet<>();for(Region r:WORLD.REGIONS().active())active.add(r.index());
                int inactive=-1;for(Region r:WORLD.REGIONS().all())if(!active.contains(r.index())){inactive=r.index();break;}
                if(inactive<0)throw new IllegalStateException("Fixture needs an inactive region ID");
                Map<String,Object> fixture=new LinkedHashMap<>();fixture.put("region_ids",ids);fixture.put("resource_ids",keys);
                fixture.put("rows",rows);fixture.put("target_region",target.index());fixture.put("target_resource",targetResource.key);
                fixture.put("inactive_region",inactive);fixture.put("started_at",Instant.now().toString());
                Files.writeString(directory.resolve("live-regional-fixture.json"),JsonWriter.encode(fixture));written[0]=true;
            }catch(Exception error){counter.set(target,original);CORE.annihilate(error);}
        });
    }
}
