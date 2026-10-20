import java.nio.file.*;
import java.util.*;
import game.GAME;
import settlement.main.SETT;
import snake2d.CORE;
import syx.assistant.JsonWriter;
import syx.assistant.UiContextCollector;
import syx.assistant.candidate.WeatherObservation;
import static syx.assistant.StateCollector.object;

/** TEST ONLY: fixed weather observer/fault probe around the existing real scene fixture. */
public final class StockpileScenario {
    static final Set<Integer> EXPECTED=Set.of(0,1,2,3,4,6,8,9);
    static final Set<Integer> CITY=Set.of(0,1,2,6);
    static final Set<Integer> seen=new HashSet<>();
    static boolean faultChecked;
    public static void install(Path directory){
        seen.clear();faultChecked=false;
        String copied=System.getProperty("syx.smoke.copiedSave");PathCheck.validate(copied);
        SceneScenario.install(directory,Path.of(copied),()->observe(directory));
    }
    static void observe(Path directory){
        try{
            int index=SceneScenario.phase;
            if(index==10){
                if(seen.size()!=8 || !faultChecked)throw new IllegalStateException("Incomplete weather lifecycle/fault observations");
                Files.writeString(directory.resolve("weather-scenes-clean-exit.json"),JsonWriter.encode(object("passed",true,"phases",8,"fault_restored",true)));
                return;
            }
            if(!EXPECTED.contains(index) || seen.contains(index) || System.currentTimeMillis()-SceneScenario.began<2500)return;
            var scene=UiContextCollector.scene();String active=(String)scene.get("active_view");
            String expected=index==1?"settlement_battle":index==3 || index==4?"battle":index==8 || index==9?"world_generation":"settlement";
            if(!expected.equals(active))return;
            var candidate=WeatherObservation.collect();boolean available=CITY.contains(index);
            if(!Boolean.valueOf(available).equals(candidate.get("available")))throw new IllegalStateException("Weather scope mismatch at "+index);
            int compared=0;
            if(available){
                var w=SETT.WEATHER();var direct=WeatherObservation.detached(new double[]{w.moisture.getD(),w.snow.getD(),w.ice.getD(),w.wind.getD(),w.temp.getD(),w.clouds.getD(),w.rain.getD(),w.thunder.getD(),w.growth.getD(),w.growthRipe.getD()},
                    new boolean[]{w.snow.rainIsSnow(),w.growth.isAutumn(),w.growthRipe.cropsAreRipe(),w.growthRipe.ripening()});
                if(!direct.equals(candidate.get("data")))throw new IllegalStateException("Weather getter mismatch");compared=14;
            }else if(candidate.get("data")!=null)throw new IllegalStateException("Unavailable weather leaked values");
            if(index==0){
                var wind=SETT.WEATHER().wind;double prior=wind.getD();
                double[] inputs={Double.NaN,Double.NEGATIVE_INFINITY,Double.POSITIVE_INFINITY,-.25,1.25,0,1};
                double[] normalized={0,0,1,0,1,0,1};
                Map<?,?> baseline=(Map<?,?>)candidate.get("data");Map<?,?> factors=(Map<?,?>)baseline.get("factors");
                for(int i=0;i<inputs.length;i++){
                    try{
                        // Public base setter normalizes invalid input. This cannot inject a bad stored getter.
                        wind.setD(inputs[i]);
                        if(wind.getD()!=normalized[i])throw new IllegalStateException("Unexpected public setter normalization");
                        var controlled=WeatherObservation.collect();
                        if(!Boolean.TRUE.equals(controlled.get("available")))throw new IllegalStateException("Valid normalized weather was refused");
                        Map<?,?> data=(Map<?,?>)controlled.get("data"),values=(Map<?,?>)data.get("factors");
                        if(((Number)values.get("wind_strength")).doubleValue()!=normalized[i] || !baseline.get("flags").equals(data.get("flags")))
                            throw new IllegalStateException("Normalized factor or unrelated flags changed");
                        for(var key:factors.keySet())if(!key.equals("wind_strength") && !factors.get(key).equals(values.get(key)))
                            throw new IllegalStateException("Unrelated factor changed");
                    }finally{wind.setD(prior);}
                    if(Double.doubleToLongBits(wind.getD())!=Double.doubleToLongBits(prior) || !Boolean.TRUE.equals(WeatherObservation.collect().get("available")))
                        throw new IllegalStateException("Native weather control restoration failed");
                }
                faultChecked=true;
            }
            Files.writeString(directory.resolve("weather-scene-"+index+".json"),JsonWriter.encode(object("phase",index,"observer_tick",GAME.updateI(),"candidate",candidate,"scene",scene,"getter_comparisons",compared,"fault_restored",faultChecked)));
            seen.add(index);
            if(index==0)Files.writeString(directory.resolve("stockpile-fixture.json"),"{\"passed\":true}\n");
        }catch(Exception failure){throw new IllegalStateException("Weather lifecycle fixture failed",failure);}
    }
}
