import game.GAME;
import game.battle.state.*;
import settlement.main.SETT;
import world.WORLD;
import snake2d.CORE;
import snake2d.util.datatypes.RECTANGLE;
import snake2d.util.misc.ACTION;
import view.main.VIEW;
import view.subview.GameWindow;
import syx.assistant.JsonWriter;
import java.nio.file.*;
import java.time.Instant;
import java.util.*;
import static syx.assistant.StateCollector.object;

/** TEST ONLY: public camera/view/menu actions in a disposable copied profile; no pointer/input injection. */
public final class ViewportScenario {
    static List<Integer> rectangle(RECTANGLE r){return Arrays.asList(r.x1(),r.y1(),r.x2(),r.y2());}
    static Map<String,Object> read(GameWindow w){return object("zoomout",w.zoomout(),"tiles",rectangle(w.tiles()),"pixels",rectangle(w.pixels()),"screen",rectangle(w.view()));}
    static void check(GameWindow w,boolean frozen){
        Map<String,Object> a=read(w);if(!a.equals(read(w)))throw new IllegalStateException("Immediate public reads disagree");
        if(w.zoomout()<0 || w.zoomout()>w.zoomoutmax())throw new IllegalStateException("Zoom outside public maximum");
        if(!frozen && (w.pixels().width()!=(w.view().width()<<w.zoomout()) || w.pixels().height()!=(w.view().height()<<w.zoomout())))
            throw new IllegalStateException("Expected refreshed pixel/screen scaling");
    }
    static void place(GameWindow w,int x,int y,int z){w.setZoomout(z);w.centerAtTile(x,y);check(w,false);}
    public static void install(Path directory){
        GAME.SPEED.speedSet(0);VIEW.s().activate();int[] step={0};boolean[] ready={false};long began=System.nanoTime();
        Map<String,Object> cityBefore=new LinkedHashMap<>();GameWindow[] handles=new GameWindow[4];
        GAME.addAfterUpdate(()->{
            try{
                if(Files.exists(directory.resolve("verifier.done"))){
                    Files.writeString(directory.resolve("viewport-clean-exit.json"),JsonWriter.encode(object("passed",true,"verified_phases",11)));CORE.annihilate();return;
                }
                if(System.nanoTime()-began>230_000_000_000L)throw new IllegalStateException("Viewport verifier timed out");
                if(ready[0] && !Files.exists(directory.resolve("phase-"+step[0]+".done")))return;
                if(ready[0] && step[0]==10)return;if(ready[0])step[0]++;
                String name,kind="settlement",scope="instantiated_settlement_tiles";boolean frozen=false,modal=false,hidden=false,menu=false;
                GameWindow w=VIEW.s().getWindow();Map<String,Object> control=object("public_camera_reads_only",false);
                switch(step[0]){
                    case 0:name="city_baseline";handles[0]=w;place(w,200,200,0);cityBefore.putAll(read(w));break;
                    case 1:name="city_shift_and_zoom";place(w,300,300,1);if(cityBefore.equals(read(w)))throw new IllegalStateException("Camera test did not change geometry");break;
                    case 2:
                        name="management_cached_mismatch";VIEW.UI().goods.activate();frozen=true;
                        if(!VIEW.UI().manager.open() || w.zoomoutmax()<2)throw new IllegalStateException("Management/zoom fixture unavailable");
                        Map<String,Object> before=read(w);w.setZoomout(2);Map<String,Object> after=read(w);
                        if(!before.get("pixels").equals(after.get("pixels")) || !before.get("tiles").equals(after.get("tiles")) || before.get("zoomout").equals(after.get("zoomout")))
                            throw new IllegalStateException("Expected frozen caches with changed zoom while management open");
                        control=object("cached_rectangles_unchanged_after_public_zoom_action",true,"zoom_changed",true);break;
                    case 3:name="management_closed_refresh";VIEW.UI().manager.close();place(w,300,300,2);break;
                    case 4:name="city_tactical";VIEW.s().battle.activate();w=VIEW.s().battle.getWindow();handles[1]=w;kind="settlement_battle";place(w,200,200,0);break;
                    case 5:name="world";VIEW.world().activate();w=VIEW.world().window;handles[2]=w;kind="world";scope="campaign_world_tiles";place(w,WORLD.TWIDTH()/2,WORLD.THEIGHT()/2,0);break;
                    case 6:name="world_confirmation";w=VIEW.world().window;kind="world";scope="campaign_world_tiles";modal=true;
                        VIEW.inters().yesNo.activate("Disposable viewport context",ACTION.NOP,ACTION.NOP,true);break;
                    case 7:name="city_return";VIEW.inters().yesNo.deactivate();VIEW.s().activate();w=VIEW.s().getWindow();place(w,200,200,0);break;
                    case 8:
                        name="battle_deployment";BattleStateSpec spec=new BattleStateSpec();
                        spec.player.wCoo.set(WORLD.TWIDTH()/2,WORLD.THEIGHT()/2);spec.enemy.wCoo.set(WORLD.TWIDTH()/2+1,WORLD.THEIGHT()/2);
                        spec.player.moraleBase=spec.enemy.moraleBase=1;spec.player.divs.add(SceneScenario.division("Viewport player"));spec.enemy.divs.add(SceneScenario.division("Viewport enemy"));
                        BattleState.setGenerate(new BattleStateExiter(){public void afterExit(BattleStateResult result){}},spec);
                        GAME.SPEED.speedSet(0);w=VIEW.b().getWindow();handles[3]=w;kind="battle";place(w,SETT.TWIDTH/2,SETT.THEIGHT/2,0);break;
                    case 9:name="battle_menu";VIEW.inters().menu.show();w=VIEW.b().getWindow();kind="battle";menu=true;break;
                    case 10:name="battle_hidden";VIEW.inters().manager.remove(VIEW.inters().menu);VIEW.hide();w=VIEW.b().getWindow();kind="battle";hidden=true;break;
                    default:throw new IllegalStateException("Unexpected viewport phase");
                }
                check(w,frozen);
                if(step[0]>=8)for(int i=0;i<4;i++)for(int j=i+1;j<4;j++)if(handles[i]==handles[j])throw new IllegalStateException("Expected four distinct window handles");
                Map<String,Object> phase=object("phase",name,"step",step[0],"started_at",Instant.now().toString(),"expected_view",kind,
                    "management",frozen,"modal",modal,"hidden",hidden,"menu",menu,"coordinate_scope",scope,"candidate_geometry",read(w),"control_checks",control);
                Files.writeString(directory.resolve("phase.json"),JsonWriter.encode(phase));ready[0]=true;
            }catch(Exception e){System.err.println("SMOKE_FIXTURE_FAILURE: "+e);try{Files.writeString(directory.resolve("viewport-fixture-failure.json"),e.getClass().getSimpleName());}catch(Exception ignored){}CORE.annihilate(e);}
        });
    }
}
