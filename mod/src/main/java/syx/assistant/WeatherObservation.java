package syx.assistant;

import java.time.Instant;
import java.util.*;
import game.GAME;
import settlement.main.SETT;
import world.WORLD;
import static syx.assistant.StateCollector.object;

/** Fixed stored weather reads on the after-update thread; detached values only. */
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
    private static Map<String,Object> definitions(){
        Map<String,Object> definitions=new LinkedHashMap<>();
        String[] members={"moisture","snow","ice","wind","temp","clouds","rain","thunder","growth","growthRipe"};
        String[] meanings={"Stored precipitation/rain-thaw history; not current rainfall or tile moisture. Drought behavior uses a below-0.25 source threshold.",
            "Global stored ground-snow factor, not local snow depth.","Global stored water-ice factor, not tile passability or usable water access.",
            "Stored game wind strength, not physical speed, target or forecast.","Stored game temperature scale, not Celsius/Fahrenheit or a future target.",
            "Stored cloud amount, not local geometry or rain probability.","Stored current downfall intensity, distinct from precipitation history and type.",
            "Stored thunder factor, not a particular flash/sound or predicted event.","Global stored plant-growth factor, not an individual crop yield or full productivity modifier.",
            "Global stored seasonal ripeness factor, not a crop's harvestable inventory."};
        for(int i=0;i<10;i++)definitions.put(FACTORS.get(i),object("unit","game-defined factor in [0,1]","source","SETT.WEATHER()."+members[i]+".getD()","meaning",meanings[i]));
        String[] flags={"snow.rainIsSnow()","growth.isAutumn()","growthRipe.cropsAreRipe()","growthRipe.ripening()"};
        for(int i=0;i<4;i++)definitions.put(FLAGS.get(i),object("unit","boolean stored/sign flag","source","SETT.WEATHER()."+flags[i],
            "meaning","Stored flag or snow-history sign; exact age unknown. Ripeness flags may use the prior factor during engine update, so do not re-derive from simultaneous factors."));
        return definitions;
    }
    public static Map<String,Object> collect(){
        try{
            if(!SETT.exists() || SETT.WORLD_AREA().isBattle || !WORLD.GEN().isDone)
                return object("available",false,"coverage","unavailable","scope","instantiated_city_weather","data",null,"reason","No completed instantiated campaign city");
            var w=SETT.WEATHER();
            Map<String,Object> data=detached(new double[]{w.moisture.getD(),w.snow.getD(),w.ice.getD(),w.wind.getD(),w.temp.getD(),
                w.clouds.getD(),w.rain.getD(),w.thunder.getD(),w.growth.getD(),w.growthRipe.getD()},
                new boolean[]{w.snow.rainIsSnow(),w.growth.isAutumn(),w.growthRipe.cropsAreRipe(),w.growthRipe.ripening()});
            return object("available",true,"coverage","partial","scope","instantiated_city_weather","data",data,"field_definitions",definitions(),"tick",Math.max(0,GAME.updateI()),
                "captured_at",Instant.now().toString(),"observer_phase","GAME.addAfterUpdate",
                "reason","Stored game-scale factors and cached flags; no physical units, exact age, per-tile moisture, individual crop yield or forecast. Cached flags may use the previous factor during engine update.");
        }catch(RuntimeException failure){
            return object("available",false,"coverage","unavailable","scope","instantiated_city_weather","data",null,"reason","Weather read unavailable: "+failure.getMessage());
        }
    }
}
