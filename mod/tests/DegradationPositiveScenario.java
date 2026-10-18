import java.nio.file.*;
import java.time.Instant;
import java.util.*;
import game.GAME;
import settlement.main.SETT;
import settlement.room.industry.module.ROOM_PRODUCER_INSTANCE;
import snake2d.CORE;
import syx.assistant.JsonWriter;

/** TEST ONLY: creates one positive wear value through a public action in a disposable copied game. */
public final class DegradationPositiveScenario {
    public static void install(Path output) {
        GAME.SPEED.speedSet(0);
        long began=System.currentTimeMillis();boolean[] changed={false};
        GAME.addAfterUpdate(()->{
            if(changed[0] || System.currentTimeMillis()-began<2000)return;
            changed[0]=true;
            try {
                for(var blueprint:SETT.ROOMS().ins())for(var room:blueprint.all()) {
                    if(!(room instanceof ROOM_PRODUCER_INSTANCE))continue;
                    var producer=(ROOM_PRODUCER_INSTANCE)room;
                    if(producer.industry()==null || producer.industry().outs().size()==0 || room.getDegrade()!=0)continue;
                    double before=room.getDegrade();int calls=0;
                    while(room.getDegrade()<=0 && calls<512) {
                        SETT.MAINTENANCE().vandalise(room.mX(),room.mY());calls++;
                    }
                    double after=room.getDegrade();
                    if(!Double.isFinite(after) || after<=0)throw new IllegalStateException("Public action did not produce a positive room value within 512 calls");
                    Files.createDirectories(output);
                    Files.writeString(output.resolve("degradation-positive-fixture.json"),JsonWriter.encode(Map.of(
                        "created_at",Instant.now().toString(),"room_id",room.index(),"before",before,"after",after,
                        "public_action_calls",calls,"public_action","MAINTENANCE.vandalise(int,int)",
                        "test_only",true,"save_written",false)));
                    return;
                }
                throw new IllegalStateException("No zero-valued producer with output for controlled fixture");
            }catch(Exception error){CORE.annihilate(error);}
        });
        // This existing fixture waits ten seconds, so it samples only after the controlled action above.
        ProductionScenario.install(output);
    }
}
