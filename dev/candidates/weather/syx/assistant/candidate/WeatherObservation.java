package syx.assistant.candidate;

import java.time.Instant;
import java.util.*;
import game.GAME;
import settlement.main.SETT;
import world.WORLD;
import static syx.assistant.StateCollector.object;

/** Unregistered candidate. Call collect only from GAME.addAfterUpdate; no engine handles escape. */
public final class WeatherObservation {
    public static final List<String> FACTORS=List.of("precipitation_history","ground_snow","water_ice","wind_strength","temperature_scale",
        "cloud_amount","downfall_intensity","thunder_amount","plant_growth","seasonal_ripeness");
    public static final List<String> FLAGS=List.of("downfall_is_snow","growth_autumn","crops_ripe","ripening");
    private WeatherObservation(){}
    public static Map<String,Object> detached(double[] factors,boolean[] flags){
        if(factors==null || flags==null || factors.length!=10 || flags.length!=4)throw new IllegalArgumentException("Fixed weather shape required");
        Map<String,Object> values=new LinkedHashMap<>(),cached=new LinkedHashMap<>();
        for(int i=0;i<10;i++){
            double d=factors[i];if(!Double.isFinite(d) || d<0 || d>1)throw new IllegalArgumentException("Invalid stored weather factor: "+FACTORS.get(i));
            values.put(FACTORS.get(i),d);
        }
        for(int i=0;i<4;i++)cached.put(FLAGS.get(i),flags[i]);
        return object("factors",values,"flags",cached);
    }
    public static Map<String,Object> collect(){
        try{
        if(!SETT.exists() || SETT.WORLD_AREA().isBattle || !WORLD.GEN().isDone)
            return object("available",false,"scope","instantiated_city_weather","data",null,"reason","No completed instantiated campaign city");
            var w=SETT.WEATHER();
            Map<String,Object> data=detached(new double[]{w.moisture.getD(),w.snow.getD(),w.ice.getD(),w.wind.getD(),w.temp.getD(),
                w.clouds.getD(),w.rain.getD(),w.thunder.getD(),w.growth.getD(),w.growthRipe.getD()},
                new boolean[]{w.snow.rainIsSnow(),w.growth.isAutumn(),w.growthRipe.cropsAreRipe(),w.growthRipe.ripening()});
            return object("available",true,"scope","instantiated_city_weather","data",data,"tick",Math.max(0,GAME.updateI()),
                "captured_at",Instant.now().toString(),"observer_phase","GAME.addAfterUpdate",
                "reason","Stored game-scale factors and cached flags; no physical units, exact age, per-tile moisture, individual crop yield or forecast. Cached flags may use the previous factor during engine update.");
        }catch(RuntimeException failure){
            return object("available",false,"scope","instantiated_city_weather","data",null,"reason","Weather read unavailable: "+failure.getMessage());
        }
    }
}
