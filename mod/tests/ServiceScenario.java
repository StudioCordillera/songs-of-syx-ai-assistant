import java.nio.file.*;
import java.util.*;
import game.GAME;
import settlement.main.SETT;
import settlement.room.service.module.ROOM_SERVICER;
import syx.assistant.JsonWriter;
import snake2d.CORE;

/** TEST ONLY: independent public reads and controlled cohort-policy seeds in paused copied city, no save. */
public final class ServiceScenario {
    public static void install(Path directory) {
        GAME.SPEED.speedSet(0);long began=System.currentTimeMillis();boolean[] ready={false},seeded={false};
        GAME.addAfterUpdate(()->{
            try {
                if(!seeded[0] && System.currentTimeMillis()-began>10000) {
                    seeded[0]=true;var service=settlement.room.service.module.RoomServiceAccess.ALL().get(0);
                    var race=init.race.RACES.all().get(0);var permission=service.stats().permission();
                    permission.set(init.type.HCLASS_RACE.clP(race,init.type.HCLASSES.CITIZEN()),false);
                    permission.set(init.type.HCLASS_RACE.clP(race,init.type.HCLASSES.SLAVE()),true);
                }
                if(!ready[0] && System.currentTimeMillis()-began>14000) {
                    ready[0]=true;List<Object> rows=new ArrayList<>();int scanned=0;
                    for(var blueprint:SETT.ROOMS().ins())for(var room:blueprint.all()) {
                        scanned++;if(!(room instanceof ROOM_SERVICER))continue;
                        var service=((ROOM_SERVICER)room).service();
                        rows.add(Map.of("room_id",room.index(),"blueprint_id",blueprint.key,"reference_id","room:"+blueprint.key,
                            "active",room.active(),"total_slots_raw",service.total(),"available_slots_raw",service.available(),"reserved_slots_raw",service.reserved()));
                    }
                    if(rows.isEmpty())throw new IllegalStateException("No service fixture");
                    List<Object> types=new ArrayList<>(),rules=new ArrayList<>();
                    for(var service:settlement.room.service.module.RoomServiceAccess.ALL()) {
                        types.add(Map.of("service_id",service.index(),"blueprint_id",service.room().key,"reference_id","room:"+service.room().key));
                        for(var race:init.race.RACES.all())for(var cl:init.type.HCLASSES.ALL())rules.add(Map.of(
                            "service_id",service.index(),"blueprint_id",service.room().key,"race_id",race.key,"class_id",cl.key,
                            "allowed_by_configured_rule",service.stats().permission().is(init.type.HCLASS_RACE.clP(race,cl))));
                    }
                    if(types.isEmpty() || rules.isEmpty())throw new IllegalStateException("No service policy fixture");
                    var first=settlement.room.service.module.RoomServiceAccess.ALL().get(0);var firstRace=init.race.RACES.all().get(0);
                    if(first.stats().permission().is(init.type.HCLASS_RACE.clP(firstRace,init.type.HCLASSES.CITIZEN())) ||
                       !first.stats().permission().is(init.type.HCLASS_RACE.clP(firstRace,init.type.HCLASSES.SLAVE())))throw new IllegalStateException("Policy seed failed");
                    Files.writeString(directory.resolve("service-fixture.json"),JsonWriter.encode(Map.of("rooms",rows,"scanned_rooms",scanned,
                        "service_types",types,"cohort_rules",rules,"seeded_service",first.index(),"seeded_race",firstRace.key,
                        "seeded_denied_class",init.type.HCLASSES.CITIZEN().key,"seeded_allowed_class",init.type.HCLASSES.SLAVE().key,
                        "fixture_note","Public policy setters used only in paused copied city to establish true/false cases; never saves. Observer does not set policy.")));
                    System.err.println("SERVICE TEST: public getter fixture ready");
                }
                if(Files.exists(directory.resolve("verifier.done")) || System.currentTimeMillis()-began>120000)CORE.annihilate();
            }catch(Exception error){CORE.annihilate(error);}
        });
    }
}
