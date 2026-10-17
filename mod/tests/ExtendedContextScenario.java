import game.GAME;
import game.save.GameLoader;
import game.battle.state.*;
import init.sprite.UI.UI;
import snake2d.CORE;
import snake2d.util.color.COLOR;
import snake2d.util.gui.GuiSection;
import snake2d.util.gui.clickable.CLICKABLE;
import snake2d.util.misc.ACTION;
import util.gui.misc.GButt;
import util.gui.misc.GTextR;
import view.main.VIEW;
import world.WORLD;
import java.nio.file.*;
import java.time.Instant;
import java.util.*;
import syx.assistant.JsonWriter;

/** TEST ONLY: public UI construction/editor/retreat paths in an isolated copied game. */
public final class ExtendedContextScenario {
    static Path output,save;static long began;static int phase;
    static void announce(String name) {
        began=System.currentTimeMillis();
        try {Files.writeString(output.resolve("phase.json"),JsonWriter.encode(Map.of("phase",name,"started_at",Instant.now().toString())));}
        catch(Exception error){throw new IllegalStateException(error);}
        System.err.println("EXTENDED CONTEXT: "+name);
    }
    public static void install(Path directory,Path copiedSave) {
        output=directory;save=copiedSave;
        try {Files.createDirectories(output);}catch(Exception error){throw new IllegalStateException(error);}
        VIEW.s().activate();GAME.SPEED.speedSet(0);phase=0;announce("city");register();
    }
    static void register() {
        GAME.addAfterUpdate(()->{
            if(System.currentTimeMillis()-began<7000)return;
            try {next();}catch(Exception error){System.err.println("EXTENDED FAILURE: "+error);CORE.annihilate(error);}
        });
    }
    static GuiSection panel(String title) {
        GuiSection panel=new GuiSection();panel.add(new GTextR(UI.FONT().S,title),0,0);
        GuiSection nested=new GuiSection();nested.add(new GTextR(UI.FONT().S,"Nested readable label"),0,0);
        panel.add(nested,0,30);
        GButt.ButtPanel opaque=new GButt.ButtPanel("Opaque button label");opaque.selectedSet(true);opaque.activeSet(false);
        panel.add(opaque,0,60);
        CLICKABLE.ClickSwitch switching=new CLICKABLE.ClickSwitch(new GTextR(UI.FONT().S,"Readable switch label"));
        panel.add(switching,0,100);
        GTextR hidden=new GTextR(UI.FONT().S,"Hidden label");hidden.visableSet(false);panel.add(hidden,0,130);
        GTextR shared=new GTextR(UI.FONT().S,"Shared label");panel.add(shared,0,160);panel.add(shared,0,190);
        return panel;
    }
    static void next() {
        phase++;
        switch(phase) {
            case 1:VIEW.inters().popup.show(panel("Primary popup label"),null);announce("popup");return;
            case 2:
                VIEW.inters().popup.close();VIEW.inters().popup2.show(panel("Secondary popup label"),null);announce("popup_secondary");return;
            case 3:
                VIEW.inters().popup2.close();VIEW.inters().section.activate(panel("Section label"));announce("section");return;
            case 4:
                GuiSection large=new GuiSection();
                for(int i=0;i<100;i++)large.add(new GTextR(UI.FONT().S,"Budget "+i+" "+"x".repeat(600)),0,i*20);
                VIEW.inters().section.activate(large);announce("content_budget");return;
            case 5:
                GuiSection deep=new GuiSection();deep.add(new GTextR(UI.FONT().S,"Beyond depth budget"),0,0);
                for(int i=0;i<10;i++){GuiSection parent=new GuiSection();parent.add(deep,0,0);deep=parent;}
                VIEW.inters().section.activate(deep);announce("content_depth");return;
            case 6:VIEW.inters().section.close();announce("content_closed");return;
            case 7:
                VIEW.inters().input.requestInput(value->{},"Fixture text entry","Private input fixture value");announce("text_input");return;
            case 8:
                VIEW.inters().manager.remove(VIEW.inters().input);
                VIEW.inters().fullScreen.activate("Fixture full screen prompt",COLOR.WHITE100,ACTION.NOP);announce("full_screen_prompt");return;
            case 9:
                VIEW.inters().fullScreen.deactivate();announce("reloading");
                new GameLoader(save){public void doAfterSet(){
                    VIEW.inters().load.deactivate();VIEW.s().activate();GAME.SPEED.speedSet(0);
                    phase=10;announce("city_reloaded");register();
                }}.set();return;
            case 11:VIEW.world().editor.activate();announce("world_editor");return;
            case 12:VIEW.s().activate();announce("after_world_editor");return;
            case 13:VIEW.b().editor.activate();announce("battle_setup");return;
            case 14:VIEW.s().activate();announce("after_battle_setup");return;
            case 15:
                BattleStateSpec spec=new BattleStateSpec();
                spec.player.wCoo.set(WORLD.TWIDTH()/2,WORLD.THEIGHT()/2);spec.enemy.wCoo.set(WORLD.TWIDTH()/2+1,WORLD.THEIGHT()/2);
                spec.player.moraleBase=1;spec.enemy.moraleBase=1;
                spec.player.divs.add(SceneScenario.division("Fixture player"));spec.enemy.divs.add(SceneScenario.division("Fixture enemy"));
                BattleState.setGenerate(new BattleStateExiter(){public void afterExit(BattleStateResult result){
                    if(result.result!=world.battle.spec.BATTLE_RESULT.RETREAT)throw new IllegalStateException("Expected retreat result");
                    VIEW.inters().load.deactivate();VIEW.s().activate();GAME.SPEED.speedSet(0);
                    phase=18;announce("after_retreat");register();
                }},spec);
                GAME.SPEED.speedSet(0);phase=16;announce("battle_deployment");return;
            case 17:announce("retreat_loading");VIEW.b().state().liveRetreat();return;
            case 19:announce("complete");CORE.annihilate();return;
            default:throw new IllegalStateException("Unexpected phase "+phase);
        }
    }
}
