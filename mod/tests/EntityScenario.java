import java.nio.file.*;
import java.time.Instant;
import java.util.*;
import game.GAME;
import settlement.main.SETT;
import settlement.entity.ENTITY;
import settlement.entity.humanoid.Humanoid;
import settlement.stats.STATS;
import settlement.stats.stat.STAT;
import view.main.VIEW;
import snake2d.CORE;
import syx.assistant.JsonWriter;

/** TEST ONLY: add temporary citizens to an isolated copied game, never save it. */
public final class EntityScenario {
    public static void install(Path output) {
        try {
            VIEW.s().activate();GAME.SPEED.speedSet(0);
            Humanoid seed=null;
            for(ENTITY e:SETT.ENTITIES().getAllEnts())if(e instanceof Humanoid && !e.isRemoved()){seed=(Humanoid)e;break;}
            if(seed==null)throw new IllegalStateException("No seed citizen");
            for(int i=0;i<1100;i++)new Humanoid(seed.body().cX(),seed.body().cY(),seed.race(),init.type.HTYPES.SUBJECT(),init.type.CAUSE_ARRIVES.IMMIGRATED());
            ENTITY[] all=SETT.ENTITIES().getAllEnts();Humanoid target=null;int slot=-1,total=0;
            for(int i=0;i<all.length;i++)if(all[i]!=null && !all[i].isRemoved()) {
                total++;
                if(all[i] instanceof Humanoid){target=(Humanoid)all[i];slot=i;}
            }
            if(total<=1100 || target==null || slot<=1000)throw new IllegalStateException("Fixture did not exceed prefix");
            VIEW.s().ui.subjects.showSingle(target);
            STAT chosen=null;for(STAT stat:STATS.all())if(stat.hasIndu() && stat.indu()!=null){chosen=stat;break;}
            if(chosen==null)throw new IllegalStateException("No individual stat fixture");
            Map<String,Object> expected=new LinkedHashMap<>();
            expected.put("entity_id",target.id());expected.put("slot",slot);expected.put("total",total);
            expected.put("race_id",target.race().key);expected.put("class_id",target.indu().clas().key);expected.put("humanoid_type_id",target.indu().hType().key);
            expected.put("tile_x",target.tc().x());expected.put("tile_y",target.tc().y());
            expected.put("stat_id",chosen.index());expected.put("stat_value",chosen.indu().get(target.indu()));
            Files.createDirectories(output);
            Files.writeString(output.resolve("entity-fixture.json"),JsonWriter.encode(Map.of("started_at",Instant.now().toString(),"expected",expected)));
            long began=System.currentTimeMillis();
            GAME.addAfterUpdate(()->{if(Files.exists(output.resolve("verifier.done")) || System.currentTimeMillis()-began>140000)CORE.annihilate();});
            System.err.println("ENTITY TEST: isolated fixture ready; live entities="+total+", target slot="+slot);
        }catch(Exception error){CORE.annihilate(error);}
    }
}
