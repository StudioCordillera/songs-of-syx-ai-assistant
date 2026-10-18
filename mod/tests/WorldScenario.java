import java.nio.file.*;
import java.util.*;
import game.GAME;
import snake2d.CORE;
import syx.assistant.JsonWriter;
import world.WORLD;
import world.region.RD;

/** TEST ONLY: direct public regional getter expectations, copied paused save only. */
public final class WorldScenario {
    public static void install(Path directory) {
        GAME.SPEED.speedSet(0);long began=System.currentTimeMillis();boolean[] ready={false};
        GAME.addAfterUpdate(()->{
            try {
                if(!ready[0] && System.currentTimeMillis()-began>10000) {
                    ready[0]=true;List<Object> regions=new ArrayList<>(),population=new ArrayList<>();
                    for(var region:WORLD.REGIONS().active()) {
                        var faction=region.faction();
                        regions.add(Map.of("id",region.index(),"total",RD.RACES().population.get(region),
                            "capital",region.capitol(),"area",region.info.area(),"player_owned",faction==GAME.player()));
                        for(var race:RD.RACES().all)population.add(Map.of("region_id",region.index(),"race_id",race.race.key,"population",race.pop.get(region)));
                    }
                    if(regions.isEmpty() || population.isEmpty())throw new IllegalStateException("No regional fixture");
                    Files.writeString(directory.resolve("world-fixture.json"),JsonWriter.encode(Map.of("regions",regions,"population",population,"race_count",RD.RACES().all.size())));
                    System.err.println("WORLD TEST: public getter fixture ready");
                }
                if(Files.exists(directory.resolve("verifier.done")) || System.currentTimeMillis()-began>120000)CORE.annihilate();
            }catch(Exception error){CORE.annihilate(error);}
        });
    }
}
