import java.nio.file.*;
import java.util.*;
import game.GAME;
import settlement.main.SETT;
import settlement.room.industry.module.*;
import syx.assistant.JsonWriter;
import snake2d.CORE;

/** TEST ONLY: public getter expectations in an isolated paused city. Never writes a save. */
public final class ProductionScenario {
    private static Object finite(double value) {return Double.isFinite(value)?value:null;}
    public static void install(Path output) {
        GAME.SPEED.speedSet(0);
        long began=System.currentTimeMillis();boolean[] ready={false};
        GAME.addAfterUpdate(()->{
            try {
                if(!ready[0] && System.currentTimeMillis()-began>10000) {
                    ready[0]=true;List<Object> expected=new ArrayList<>();int producers=0;
                    for(var blueprint:SETT.ROOMS().ins())for(var room:blueprint.all()) {
                        if(!(room instanceof ROOM_PRODUCER_INSTANCE))continue;
                        var instance=(ROOM_PRODUCER_INSTANCE)room;var industry=instance.industry();producers++;
                        for(String direction:List.of("input","output"))for(var resource:direction.equals("input")?industry.ins():industry.outs()) {
                            Map<String,Object> row=new LinkedHashMap<>();
                            row.put("room_id",room.index());row.put("blueprint_id",blueprint.key);
                            row.put("industry_id",industry.index());row.put("recipe_index",instance.industryI());
                            row.put("direction",direction);row.put("resource_id",resource.resource.key);
                            row.put("reference_id","resource:"+resource.resource.key);row.put("room_reference_id","room:"+blueprint.key);row.put("base_rate_raw",resource.rate);
                            row.put("day_accumulator_raw",resource.day.getD(instance));row.put("previous_day_units",resource.dayPrev.get(instance));
                            row.put("year_units",resource.year.get(instance));row.put("previous_year_units",resource.yearPrev.get(instance));
                            expected.add(row);
                        }
                    }
                    if(producers==0 || expected.isEmpty())throw new IllegalStateException("No production fixture");
                    List<Object> workforce=new ArrayList<>();int scanned=0;
                    for(var blueprint:SETT.ROOMS().ins())for(var room:blueprint.all()) {
                        scanned++;
                        if(blueprint.employment()==null || room.employees()==null)continue;
                        var staff=room.employees();
                        Map<String,Object> row=new LinkedHashMap<>();
                        row.put("room_id",room.index());row.put("active",room.active());
                        row.put("employed",staff.employed());row.put("needed",staff.needed());
                        row.put("target",staff.target());row.put("capacity",staff.max());
                        Map<String,Object> factors=new LinkedHashMap<>();
                        factors.put("efficiency_stored_raw",finite(staff.efficiency()));
                        factors.put("proximity_stored_raw",finite(staff.proximity()));
                        factors.put("fetch_proximity_stored_raw",finite(staff.fetchProximity()));
                        factors.put("fetch_factor_applies",blueprint.employment().countInput());
                        factors.put("combined_efficiency_raw",finite(staff.totEfficiency()));
                        row.put("work_factors",factors);workforce.add(row);
                    }
                    Files.createDirectories(output);
                    Files.writeString(output.resolve("workforce-fixture.json"),JsonWriter.encode(Map.of("rooms",workforce,"scanned_rooms",scanned)));
                    Files.writeString(output.resolve("production-fixture.json"),JsonWriter.encode(Map.of("producer_rooms",producers,"flows",expected)));
                    System.err.println("PRODUCTION TEST: public-getter fixture ready");
                }
                if(Files.exists(output.resolve("verifier.done")) || System.currentTimeMillis()-began>120000)CORE.annihilate();
            }catch(Exception error){CORE.annihilate(error);}
        });
    }
}
