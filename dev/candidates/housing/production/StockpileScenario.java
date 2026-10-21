import java.nio.file.*;
import java.util.*;
import game.GAME;
import snake2d.CORE;
import syx.assistant.JsonWriter;
import syx.assistant.StateCollector;
import syx.assistant.candidate.HousingObservation;
import static syx.assistant.StateCollector.object;

/** TEST ONLY: same-callback production housing mapping, independently compared with the reviewed fixed reader. */
public final class StockpileScenario {
    @SuppressWarnings("unchecked")
    public static void install(Path directory){
        GAME.SPEED.speedSet(0);view.main.VIEW.s().activate();long began=System.nanoTime();boolean[] written={false},finished={false};
        GAME.addAfterUpdate(()->{
            if(finished[0])return;
            try{
                if(Files.exists(directory.resolve("verifier.done"))){
                    if(!written[0])throw new IllegalStateException("Premature completion");
                    Files.writeString(directory.resolve("housing-query-clean-exit.json"),JsonWriter.encode(object("passed",true,"same_callback",true)));
                    finished[0]=true;CORE.annihilate();return;
                }
                if(System.nanoTime()-began>100_000_000_000L)throw new IllegalStateException("Housing query timeout");
                if(written[0] || System.nanoTime()-began<5_000_000_000L)return;
                int tick=GAME.updateI();var observation=StateCollector.collect(UUID.randomUUID().toString(),1);
                var candidate=HousingObservation.collect(10000,1000);var capped=HousingObservation.collect(10000,1);
                if(!Boolean.TRUE.equals(candidate.get("available")) || !Boolean.TRUE.equals(capped.get("available")))throw new IllegalStateException("Need available city housing");
                var domains=(Map<String,Object>)observation.get("domains");var housing=(Map<String,Object>)domains.get("housing");
                var data=(Map<String,Object>)housing.get("data");
                if(!JsonWriter.encode(data.get("home_records")).equals(JsonWriter.encode(candidate)))
                    throw new IllegalStateException("Production home DTO differs from fixed candidate");
                if(GAME.updateI()!=tick)throw new IllegalStateException("Crossed callback");
                Files.writeString(directory.resolve("housing-query-observation.json"),JsonWriter.encode(observation));
                Files.writeString(directory.resolve("stockpile-fixture.json"),JsonWriter.encode(object("passed",true,"same_callback",true,"observer_tick",tick,"candidate",candidate,"capped",capped)));
                written[0]=true;
            }catch(Exception failure){finished[0]=true;System.err.println("SMOKE_FIXTURE_FAILURE: "+failure);CORE.annihilate(failure);}
        });
    }
}
