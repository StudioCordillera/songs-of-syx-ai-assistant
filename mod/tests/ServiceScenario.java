import java.nio.file.*;
import java.util.*;
import game.GAME;
import settlement.main.SETT;
import settlement.room.service.module.ROOM_SERVICER;
import syx.assistant.JsonWriter;
import snake2d.CORE;

/** TEST ONLY: independent public reads in paused copied city, no report/refresh/save. */
public final class ServiceScenario {
    public static void install(Path directory) {
        GAME.SPEED.speedSet(0);long began=System.currentTimeMillis();boolean[] ready={false};
        GAME.addAfterUpdate(()->{
            try {
                if(!ready[0] && System.currentTimeMillis()-began>10000) {
                    ready[0]=true;List<Object> rows=new ArrayList<>();int scanned=0;
                    for(var blueprint:SETT.ROOMS().ins())for(var room:blueprint.all()) {
                        scanned++;if(!(room instanceof ROOM_SERVICER))continue;
                        var service=((ROOM_SERVICER)room).service();
                        rows.add(Map.of("room_id",room.index(),"blueprint_id",blueprint.key,"reference_id","room:"+blueprint.key,
                            "active",room.active(),"total_slots_raw",service.total(),"available_slots_raw",service.available(),"reserved_slots_raw",service.reserved()));
                    }
                    if(rows.isEmpty())throw new IllegalStateException("No service fixture");
                    Files.writeString(directory.resolve("service-fixture.json"),JsonWriter.encode(Map.of("rooms",rows,"scanned_rooms",scanned)));
                    System.err.println("SERVICE TEST: public getter fixture ready");
                }
                if(Files.exists(directory.resolve("verifier.done")) || System.currentTimeMillis()-began>120000)CORE.annihilate();
            }catch(Exception error){CORE.annihilate(error);}
        });
    }
}
