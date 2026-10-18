import game.GAME;
import game.faction.FACTIONS;
import game.faction.npc.FactionNPC;
import snake2d.CORE;
import snake2d.util.misc.ACTION;
import view.main.VIEW;
import syx.assistant.JsonWriter;
import java.nio.file.*;
import java.time.Instant;
import java.util.*;

/** TEST ONLY: public panel actions in a disposable copied profile; never shipped. */
public final class FactionUiScenario {
    public static void install(Path directory) {
        GAME.SPEED.speedSet(0);VIEW.s().activate();
        List<FactionNPC> choices=new ArrayList<>();
        for(var faction:FACTIONS.active())if(faction instanceof FactionNPC)choices.add((FactionNPC)faction);
        if(choices.size()<2)throw new IllegalStateException("Requires two active copied-world NPC factions");
        int[] step={0};long[] began={System.nanoTime()};boolean[] ready={false};
        GAME.addAfterUpdate(()->{
            try {
                if(Files.exists(directory.resolve("verifier.done"))) {CORE.annihilate();return;}
                if(System.nanoTime()-began[0]>180_000_000_000L)throw new IllegalStateException("Faction UI verifier timed out");
                if(ready[0] && !Files.exists(directory.resolve("phase-"+step[0]+".done")))return;
                if(ready[0])step[0]++;
                int n=step[0];var ui=VIEW.world().UI.factions;
                String phase;Integer expected=null;Boolean dip=null;boolean available=true,list=false,modal=false;
                switch(n) {
                    case 0:phase="city_unavailable";available=false;break;
                    case 1:VIEW.world().activate();VIEW.world().panels.clear();phase="world_closed";break;
                    case 2:ui.open(null);phase="faction_list";list=true;break;
                    case 3:ui.open(choices.get(0));phase="first_detail";expected=choices.get(0).index();dip=false;list=true;break;
                    case 4:ui.openDip(choices.get(0));phase="diplomacy_tab";expected=choices.get(0).index();dip=true;list=true;break;
                    case 5:ui.open(choices.get(1));phase="other_detail";expected=choices.get(1).index();dip=true;list=true;break;
                    case 6:VIEW.inters().yesNo.activate("Disposable faction context check",ACTION.NOP,ACTION.NOP,true);
                        phase="modal_over_detail";expected=choices.get(1).index();dip=true;list=true;modal=true;break;
                    case 7:VIEW.inters().yesNo.deactivate();VIEW.s().activate();phase="hidden_world_panels";available=false;
                        if(!ui.openIs(choices.get(1)))throw new IllegalStateException("Fixture lost underlying hidden panel");break;
                    case 8:VIEW.world().activate();phase="return_world_clears_panels";break;
                    case 9:ui.open(choices.get(1));phase="reopened_detail";expected=choices.get(1).index();dip=true;list=true;break;
                    case 10:VIEW.world().panels.clear();phase="closed_after_detail";break;
                    default:throw new IllegalStateException("Unexpected faction UI phase");
                }
                if(available) {
                    if(ui.openIs()!=list)throw new IllegalStateException("Direct list getter disagrees");
                    int matched=0;
                    for(var faction:FACTIONS.active())if(ui.openIs(faction)) {
                        matched++;
                        if(expected==null || faction.index()!=expected || ui.diploIs(faction)!=dip)
                            throw new IllegalStateException("Direct identity/tab getter disagrees");
                    }
                    if(matched!=(expected==null?0:1))throw new IllegalStateException("Direct match count disagrees");
                }
                Map<String,Object> record=new LinkedHashMap<>();
                record.put("phase",phase);record.put("step",n);record.put("started_at",Instant.now().toString());
                record.put("available",available);record.put("list_open",available?list:null);
                record.put("faction_id",expected);record.put("diplomacy_tab",dip);record.put("modal",modal);
                Files.writeString(directory.resolve("phase.json"),JsonWriter.encode(record));ready[0]=true;
                System.err.println("FACTION UI TEST: "+phase);
            }catch(Exception error){CORE.annihilate(error);}
        });
    }
}
