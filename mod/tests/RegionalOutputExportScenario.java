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

/** TEST ONLY: native expectations and held/restored public counter controls in a disposable copied game. */
public final class RegionalOutputExportScenario {
    public static void install(Path directory) {
        if(!WORLD.GEN().isDone || WORLD.REGIONS().active().size()==0 || RESOURCES.ALL().size()==0 ||
            (long)WORLD.REGIONS().active().size()*RESOURCES.ALL().size()>10000)
            throw new IllegalStateException("Requires finite completed copied-world regional fixture");
        GAME.SPEED.speedSet(0);view.main.VIEW.s().activate();
        Region target=WORLD.REGIONS().active().get(0);RESOURCE resource=RESOURCES.ALL().get(0);
        var controlled=RD.OUTPUT().get(TR.get(resource)).yearlyAccumilation;
        int original=controlled.get(target);long began=System.nanoTime();int[] phase={0};boolean[] emitted={false};
        GAME.addAfterUpdate(()->{
            try {
                if(Files.exists(directory.resolve("verifier.done"))){controlled.set(target,original);CORE.annihilate();return;}
                if(System.nanoTime()-began>160_000_000_000L)throw new IllegalStateException("Regional export verification timed out");
                if(emitted[0] && !Files.exists(directory.resolve("regional-"+phase[0]+".done")))return;
                if(emitted[0])phase[0]++;
                String label;
                switch(phase[0]) {
                    case 0:label="natural";break;
                    case 1:controlled.set(target,37);label="controlled_37";break;
                    case 2:controlled.set(target,Integer.MAX_VALUE);label="controlled_max";break;
                    case 3:controlled.set(target,original);label="restored";break;
                    default:return;
                }
                List<Object> rows=new ArrayList<>(),schedules=new ArrayList<>();
                for(RESOURCE r:RESOURCES.ALL()) {
                    var output=RD.OUTPUT().get(TR.get(r));
                    if(output.res!=TR.get(r))throw new IllegalStateException("Independent resource route mismatch");
                    schedules.add(Map.of("resource_id",r.key,"reference_id","resource:"+r.key,
                        "days_until_configured_output",output.daysUntilDailydelivery()));
                }
                for(Region region:WORLD.REGIONS().active())for(RESOURCE r:RESOURCES.ALL())
                    rows.add(Map.of("region_id",region.index(),"resource_id",r.key,"reference_id","resource:"+r.key,
                        "accrued_output_raw",RD.OUTPUT().get(TR.get(r)).yearlyAccumilation.get(region)));
                Map<String,Object> fixture=new LinkedHashMap<>();fixture.put("phase",label);fixture.put("step",phase[0]);
                fixture.put("started_at",Instant.now().toString());fixture.put("rows",rows);fixture.put("schedules",schedules);
                fixture.put("controlled_region",target.index());fixture.put("controlled_resource",resource.key);
                fixture.put("restored",phase[0]==3 && controlled.get(target)==original);
                Files.writeString(directory.resolve("regional-output-fixture.json"),JsonWriter.encode(fixture));emitted[0]=true;
                System.err.println("REGIONAL OUTPUT EXPORT TEST: "+label);
            }catch(Exception error){controlled.set(target,original);CORE.annihilate(error);}
        });
    }
}
