import java.nio.file.*;
import java.util.*;
import game.GAME;
import settlement.main.SETT;
import snake2d.CORE;
import syx.assistant.StateCollector;
import syx.assistant.JsonWriter;
import static syx.assistant.StateCollector.object;

/** TEST ONLY: actual full production observations and independent same-callback weather getters. */
public final class WeatherScenario {
    @SuppressWarnings("unchecked")
    public static void install(Path directory,Path save){
        GAME.SPEED.speedSet(0);view.main.VIEW.s().activate();
        long began=System.nanoTime();int[] phase={0};boolean[] finished={false},restored={false};
        double prior=SETT.WEATHER().wind.getD();String session=UUID.randomUUID().toString();
        GAME.addAfterUpdate(()->{
            if(finished[0])return;
            try{
                if(System.nanoTime()-began>160_000_000_000L)throw new IllegalStateException("Weather MCP verifier timeout");
                if(phase[0]==0 && System.nanoTime()-began<5_000_000_000L)return;
                if(phase[0]>0 && !Files.exists(directory.resolve("weather-"+(phase[0]-1)+".done")))return;
                if(phase[0]==4){
                    if(!restored[0])throw new IllegalStateException("Wind not restored");finished[0]=true;SceneScenario.install(directory,save);return;
                }
                if(phase[0]==1)SETT.WEATHER().wind.setD(0);
                if(phase[0]==2)SETT.WEATHER().wind.setD(1);
                if(phase[0]==3){
                    SETT.WEATHER().wind.setD(prior);restored[0]=Double.doubleToLongBits(prior)==Double.doubleToLongBits(SETT.WEATHER().wind.getD());
                    if(!restored[0])throw new IllegalStateException("Wind restoration failed");view.main.VIEW.world().activate();
                }
                var w=SETT.WEATHER();double[] f={w.moisture.getD(),w.snow.getD(),w.ice.getD(),w.wind.getD(),w.temp.getD(),w.clouds.getD(),w.rain.getD(),w.thunder.getD(),w.growth.getD(),w.growthRipe.getD()};
                boolean[] b={w.snow.rainIsSnow(),w.growth.isAutumn(),w.growthRipe.cropsAreRipe(),w.growthRipe.ripening()};
                var snapshot=StateCollector.collect(session,phase[0]);
                var domains=(Map<String,Object>)snapshot.get("domains");var map=(Map<String,Object>)((Map<String,Object>)domains.get("map")).get("data");
                var weather=(Map<String,Object>)map.get("weather");var data=(Map<String,Object>)weather.get("data");
                var factors=(Map<String,Object>)data.get("factors");var flags=(Map<String,Object>)data.get("flags");
                String[] fn={"precipitation_history","ground_snow","water_ice","wind_strength","temperature_scale","cloud_amount","downfall_intensity","thunder_amount","plant_growth","seasonal_ripeness"};
                String[] bn={"downfall_is_snow","growth_autumn","crops_ripe","ripening"};
                for(int i=0;i<10;i++)if(((Number)factors.get(fn[i])).doubleValue()!=f[i])throw new IllegalStateException("Weather factor mapping mismatch");
                for(int i=0;i<4;i++)if(!Boolean.valueOf(b[i]).equals(flags.get(bn[i])))throw new IllegalStateException("Weather flag mapping mismatch");
                if(!snapshot.get("tick").equals(weather.get("tick")))throw new IllegalStateException("Weather tick differs from snapshot");
                Files.writeString(directory.resolve("weather-observation-"+phase[0]+".json"),JsonWriter.encode(snapshot));
                Files.writeString(directory.resolve("weather-fixture-"+phase[0]+".json"),JsonWriter.encode(object("phase",phase[0],"expected_data",data,"tick",snapshot.get("tick"),"snapshot_id",snapshot.get("snapshot_id"),"getter_comparisons",14)));
                phase[0]++;
            }catch(Exception failure){
                if(!restored[0])SETT.WEATHER().wind.setD(prior);
                finished[0]=true;System.err.println("SMOKE_FIXTURE_FAILURE: "+failure);CORE.annihilate(failure);
            }
        });
    }
}
