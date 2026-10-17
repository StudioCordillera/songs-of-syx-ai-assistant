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
            if(Boolean.getBoolean("syx.smoke.capture")) {
                int added=0;
                for(int y=2;y<SETT.THEIGHT-2 && added<1100;y+=4)for(int x=2;x<SETT.TWIDTH-2 && added<1100;x+=4) {
                    if(!SETT.PATH().getAvailability(x,y).availableToStandOn || !SETT.PATH().reachability.is(x,y) || SETT.ENTITIES().hasAtTile(x,y))continue;
                    Humanoid made=new Humanoid(x*init.constant.C.TILE_SIZE+init.constant.C.TILE_SIZEH,
                        y*init.constant.C.TILE_SIZE+init.constant.C.TILE_SIZEH,seed.race(),init.type.HTYPES.SUBJECT(),init.type.CAUSE_ARRIVES.IMMIGRATED());
                    if(!made.isRemoved())added++;
                }
                if(added!=1100)throw new IllegalStateException("Not enough separated public walkable fixture tiles: "+added);
            } else {
                for(int i=0;i<1100;i++)new Humanoid(seed.body().cX(),seed.body().cY(),seed.race(),init.type.HTYPES.SUBJECT(),init.type.CAUSE_ARRIVES.IMMIGRATED());
            }
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
            List<Object> relationshipCases=new ArrayList<>();
            Map<String,Boolean> found=new LinkedHashMap<>();
            for(String relation:List.of("workplace","profession","home_assignment","division"))found.put(relation,false);
            // Null assignments on newly added citizens, plus real pre-existing non-null assignments.
            relationshipCases.add(Map.of("entity_id",target.id(),"relations",expectedRelationships(target)));
            for(ENTITY e:all)if(e instanceof Humanoid && !e.isRemoved()) {
                Humanoid h=(Humanoid)e;Map<String,Object> relations=expectedRelationships(h);boolean useful=false;
                for(String key:found.keySet())if(!found.get(key) && relations.get(key)!=null){found.put(key,true);useful=true;}
                if(useful)relationshipCases.add(Map.of("entity_id",h.id(),"relations",relations));
                if(!found.containsValue(false))break;
            }
            if(found.containsValue(false))throw new IllegalStateException("Missing non-null relationship fixture: "+found);
            expected.put("relationship_cases",relationshipCases);
            Files.createDirectories(output);
            Files.writeString(output.resolve("entity-fixture.json"),JsonWriter.encode(Map.of("started_at",Instant.now().toString(),"expected",expected)));
            if(Boolean.getBoolean("syx.smoke.capture")) {
                final Humanoid source=seed;final boolean[] mutated={false};
                final boolean[] resumed={false};
                GAME.addAfterUpdate(()->{
                    if(mutated[0] && !resumed[0] && Files.exists(output.resolve("capture-resume.request"))) {
                        resumed[0]=true;VIEW.inters().manager.remove(VIEW.inters().menu);VIEW.inters().manager.clear();VIEW.current().uiManager.clear();GAME.SPEED.speedSet(1);
                        try {Files.writeString(output.resolve("capture-resumed.json"),JsonWriter.encode(Map.of("tick",GAME.updateI())));}
                        catch(Exception error){CORE.annihilate(error);}
                    }
                    if(mutated[0] || !Files.exists(output.resolve("capture-mutate.request")))return;
                    mutated[0]=true;
                    try {
                        Humanoid added=new Humanoid(source.body().cX(),source.body().cY(),source.race(),init.type.HTYPES.SUBJECT(),init.type.CAUSE_ARRIVES.IMMIGRATED());
                        VIEW.world().activate();VIEW.inters().menu.show();GAME.SPEED.speedSet(1);
                        Files.writeString(output.resolve("capture-mutated.json"),JsonWriter.encode(Map.of("added_entity_id",added.id(),"mutation_tick",GAME.updateI())));
                    }catch(Exception error){CORE.annihilate(error);}
                });
            }
            long began=System.currentTimeMillis();
            GAME.addAfterUpdate(()->{if(Files.exists(output.resolve("verifier.done")) || System.currentTimeMillis()-began>140000)CORE.annihilate();});
            System.err.println("ENTITY TEST: isolated fixture ready; live entities="+total+", target slot="+slot);
        }catch(Exception error){CORE.annihilate(error);}
    }
    static Map<String,Object> expectedRelationships(Humanoid h) {
        Map<String,Object> values=new LinkedHashMap<>();
        var room=STATS.WORK().EMPLOYED.get(h);
        values.put("workplace",room==null?null:Map.of("room_id",room.index(),"blueprint_id",room.blueprint().key,
            "name",room.name().toString(),"anchor_tile_x",room.mX(),"anchor_tile_y",room.mY()));
        var profession=STATS.WORK().profession.get(h.indu());
        values.put("profession",profession==null?null:Map.of("blueprint_id",profession.key));
        var home=STATS.HOME().GETTER.hCoo(h);
        values.put("home_assignment",home==null?null:Map.of("tile_x",home.x(),"tile_y",home.y()));
        var div=h.division();
        values.put("division",div==null?null:Map.of("division_id",(int)div.index(),"army_division_index",(int)div.indexArmy(),"side",div.player()?"player":"enemy"));
        return values;
    }

}
