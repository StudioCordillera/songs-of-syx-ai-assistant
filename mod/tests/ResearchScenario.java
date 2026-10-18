import java.nio.file.*;
import java.time.Instant;
import java.util.*;
import game.GAME;
import init.tech.*;
import snake2d.CORE;
import syx.assistant.JsonWriter;

/** TEST ONLY: independent public-getter expectations, in a paused copied game. No save writes. */
public final class ResearchScenario {
    public static void install(Path output) {
        try {
            GAME.SPEED.speedSet(0);
            final long settling=System.currentTimeMillis();
            final boolean[] ready={false};
            GAME.addAfterUpdate(()->{
                if(ready[0] || System.currentTimeMillis()-settling<10000)return;
                ready[0]=true;
                writeFixture(output);
            });
        }catch(Exception error){CORE.annihilate(error);}
    }
    private static void writeFixture(Path output) {
        try {
            var player=GAME.player().tech();
            List<Object> technologies=new ArrayList<>(),requirements=new ArrayList<>(),costs=new ArrayList<>(),currencies=new ArrayList<>();
            for(TECH tech:TECHS.ALL()) {
                technologies.add(Map.of("id",tech.key,"level",player.level(tech),"max_level",tech.levelMax));
                for(var requirement:tech.requires())requirements.add(Map.of("technology_id",tech.key,
                    "required_technology_id",requirement.tech.key,"required_level",requirement.level));
                for(var cost:tech.costs) {
                    Map<String,Object> row=new LinkedHashMap<>();
                    row.put("technology_id",tech.key);row.put("currency_id",cost.cu.bo.key);row.put("base_amount",cost.amount);
                    row.put("allocated_for_current_level",player.costTotal(cost,tech));
                    row.put("next_level_cost",player.level(tech)==tech.levelMax?null:player.costLevelNext(cost.amount,tech));
                    costs.add(row);
                }
            }
            for(var currency:player.currs())currencies.add(Map.of("id",currency.cu.bo.key,"total",currency.total(),
                "allocated",currency.allocated(),"frozen",currency.frozen(),"available",currency.available(),"penalty_raw",currency.penalty()));
            List<Object> rooms=new ArrayList<>();
            for(var blueprint:settlement.main.SETT.ROOMS().ins())for(var room:blueprint.all()) {
                if(blueprint.employment()==null || room.employees()==null)continue;
                rooms.add(Map.of("room_id",room.index(),"blueprint_id",blueprint.key));
            }
            settlement.entity.humanoid.Humanoid worker=null;
            for(var entity:settlement.main.SETT.ENTITIES().getAllEnts()) {
                if(entity instanceof settlement.entity.humanoid.Humanoid && !entity.isRemoved()) {
                    var h=(settlement.entity.humanoid.Humanoid)entity;
                    var assigned=settlement.stats.STATS.WORK().EMPLOYED.get(h);
                    if(assigned!=null && assigned.employees()!=null && assigned.blueprint().employment()!=null){worker=h;break;}
                }
            }
            if(worker==null)throw new IllegalStateException("No assigned worker for relationship fixture");
            view.main.VIEW.s().ui.subjects.showSingle(worker);
            var workplace=settlement.stats.STATS.WORK().EMPLOYED.get(worker);
            Map<String,Object> selection=Map.of("entity_id",worker.id(),"room_id",workplace.index(),"blueprint_id",workplace.blueprint().key);
            Files.createDirectories(output);
            Files.writeString(output.resolve("research-fixture.json"),JsonWriter.encode(Map.of("started_at",Instant.now().toString(),
                "technologies",technologies,"requirements",requirements,"costs",costs,"currencies",currencies,"rooms",rooms,"selection",selection)));
            final long began=System.currentTimeMillis();
            final boolean[] capped={false};
            GAME.addAfterUpdate(()->{
                try {
                    if(!capped[0] && Files.exists(output.resolve("research-cap.request"))) {
                        // Exercise maximum-level null cost semantics without changing the normal save.
                        TECH tech=TECHS.ALL().get(0);player.levelSet(tech,tech.levelMax);capped[0]=true;
                        Files.writeString(output.resolve("research-cap.json"),JsonWriter.encode(Map.of("technology_id",tech.key,"level",tech.levelMax)));
                    }
                    if(Files.exists(output.resolve("verifier.done")) || System.currentTimeMillis()-began>120000)CORE.annihilate();
                }catch(Exception error){CORE.annihilate(error);}
            });
            System.err.println("RESEARCH TEST: public-getter fixture ready");
        }catch(Exception error){CORE.annihilate(error);}
    }
}
