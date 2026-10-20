import java.nio.file.*;
import java.util.*;
import game.GAME;
import game.time.TIME;
import settlement.main.SETT;
import snake2d.CORE;
import syx.assistant.JsonWriter;
import syx.assistant.candidate.WeatherObservation;
import static syx.assistant.StateCollector.object;

/** TEST ONLY: explicit host-scenario override; weather reads, no stockpile candidate/shadow class. */
public final class StockpileScenario {
    public static void install(Path directory){
        GAME.SPEED.speedSet(0);view.main.VIEW.s().activate();
        long began=System.nanoTime();long[] last={0};List<Object> samples=new ArrayList<>();boolean[] written={false},finished={false};
        GAME.addAfterUpdate(()->{
            if(finished[0])return;
            try{
                if(Files.exists(directory.resolve("verifier.done"))){
                    if(!written[0])throw new IllegalStateException("Premature verifier completion");
                    Files.writeString(directory.resolve("weather-clean-exit.json"),JsonWriter.encode(object("passed",true,"samples",48)));
                    finished[0]=true;CORE.annihilate();return;
                }
                long now=System.nanoTime();if(now-began>90_000_000_000L)throw new IllegalStateException("Weather verifier timeout");
                if(written[0] || now-began<5_000_000_000L || now-last[0]<150_000_000L)return;last[0]=now;
                if(samples.size()==16)GAME.SPEED.speedSet(1);
                if(samples.size()==32){GAME.SPEED.speedSet(0);view.main.VIEW.world().activate();}
                long start=System.nanoTime();var candidate=WeatherObservation.collect();long end=System.nanoTime();
                if(!Boolean.TRUE.equals(candidate.get("available")))throw new IllegalStateException("City weather unavailable");
                var w=SETT.WEATHER();double[] direct={w.moisture.getD(),w.snow.getD(),w.ice.getD(),w.wind.getD(),w.temp.getD(),w.clouds.getD(),w.rain.getD(),w.thunder.getD(),w.growth.getD(),w.growthRipe.getD()};
                boolean[] flags={w.snow.rainIsSnow(),w.growth.isAutumn(),w.growthRipe.cropsAreRipe(),w.growthRipe.ripening()};
                if(!candidate.get("data").equals(WeatherObservation.detached(direct,flags)))throw new IllegalStateException("Weather public getter mismatch");
                String encoded=JsonWriter.encode(candidate);if(encoded.length()>8192)throw new IllegalStateException("Unexpected candidate size");
                samples.add(object("index",samples.size(),"phase",samples.size()<16?"paused_city":samples.size()<32?"running_city":"paused_world",
                    "world_view_active",view.main.VIEW.world().isActive(),"game_seconds",TIME.currentSecond(),"collector_ns",end-start,"json_bytes",encoded.getBytes(java.nio.charset.StandardCharsets.UTF_8).length,
                    "candidate",candidate,"getter_comparisons",14));
                if(samples.size()==48){
                    GAME.SPEED.speedSet(0);view.main.VIEW.s().activate();
                    Files.writeString(directory.resolve("stockpile-fixture.json"),JsonWriter.encode(object("passed",true,"samples",samples)));
                    written[0]=true;
                }
            }catch(Exception error){finished[0]=true;System.err.println("SMOKE_FIXTURE_FAILURE: "+error);CORE.annihilate(error);}
        });
    }
}
