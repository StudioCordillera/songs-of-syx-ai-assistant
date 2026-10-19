import game.GAME;
import snake2d.CORE;
import snake2d.util.misc.ACTION;
import view.main.VIEW;
import syx.assistant.JsonWriter;
import java.nio.file.*;
import java.time.Instant;
import java.util.*;

/** TEST ONLY: public panel/view actions in a disposable copied campaign; no game saves. */
public final class WorldListScenario {
    private static void together() {
        var w=VIEW.world();w.UI.armies.openList(null);
        w.panels.add(w.UI.regions.playerList,false);w.panels.add(w.UI.regions.allList,false);
    }
    public static void install(Path directory) {
        GAME.SPEED.speedSet(0);VIEW.s().activate();
        int[] step={0};boolean[] ready={false};long began=System.nanoTime();
        GAME.addAfterUpdate(()->{
            try {
                if(Files.exists(directory.resolve("verifier.done"))){
                    Files.writeString(directory.resolve("world-list-clean-exit.json"),JsonWriter.encode(Map.of("passed",true,"verified_phases",14)));
                    CORE.annihilate();return;
                }
                if(System.nanoTime()-began>180_000_000_000L)throw new IllegalStateException("World-list verifier timed out");
                if(ready[0] && !Files.exists(directory.resolve("phase-"+step[0]+".done")))return;
                if(ready[0] && step[0]==13)return;
                if(ready[0])step[0]++;
                String name;boolean available=true,modal=false,hidden=false;boolean[] flags={false,false,false};
                var w=VIEW.world();
                switch(step[0]) {
                    case 0:name="city_unavailable";available=false;break;
                    case 1:w.activate();w.panels.clear();name="world_closed";break;
                    case 2:w.UI.armies.openList(null);name="army_list";flags[0]=true;break;
                    case 3:w.UI.regions.openPlayerList();name="realm_list";flags[1]=true;break;
                    case 4:w.UI.regions.openOtherList();name="region_browser";flags[2]=true;break;
                    case 5:together();name="three_underlying_lists";Arrays.fill(flags,true);break;
                    case 6:VIEW.inters().yesNo.activate("Disposable list context check",ACTION.NOP,ACTION.NOP,true);
                        name="modal_over_lists";Arrays.fill(flags,true);modal=true;break;
                    case 7:VIEW.inters().yesNo.deactivate();VIEW.s().activate();name="inactive_world_lists";available=false;
                        if(!w.UI.armies.listIsOpen(w.panels))throw new IllegalStateException("Expected hidden underlying list state");break;
                    case 8:w.activate();name="world_return_clears_lists";break;
                    case 9:w.editor.activate();name="world_editor_unavailable";available=false;break;
                    case 10:w.activate();name="world_after_editor";break;
                    case 11:w.UI.regions.openOtherList();name="reopened_browser";flags[2]=true;break;
                    case 12:w.panels.clear();name="closed_lists";break;
                    case 13:together();VIEW.hide();name="hidden_ui_lists";Arrays.fill(flags,true);hidden=true;break;
                    default:throw new IllegalStateException("Unexpected list-context phase");
                }
                if(available) {
                    boolean[] direct={w.UI.armies.listIsOpen(w.panels),w.panels.added(w.UI.regions.playerList),w.panels.added(w.UI.regions.allList)};
                    if(!Arrays.equals(flags,direct))throw new IllegalStateException("Independent list actions/getters disagree in "+name);
                }
                Map<String,Object> phase=new LinkedHashMap<>();phase.put("phase",name);phase.put("step",step[0]);phase.put("available",available);
                phase.put("army_list_present",available?flags[0]:null);phase.put("player_realm_list_present",available?flags[1]:null);
                phase.put("region_browser_present",available?flags[2]:null);phase.put("modal",modal);phase.put("ui_hidden",hidden);
                phase.put("started_at",Instant.now().toString());Files.writeString(directory.resolve("phase.json"),JsonWriter.encode(phase));ready[0]=true;
                System.err.println("WORLD LIST TEST: "+name);
            }catch(Exception error){
                System.err.println("SMOKE_FIXTURE_FAILURE: "+error);
                try{Files.writeString(directory.resolve("world-list-fixture-failure.json"),JsonWriter.encode(Map.of("passed",false,"failure_class",error.getClass().getSimpleName())));}catch(Exception ignored){}
                CORE.annihilate(error);
            }
        });
    }
}
