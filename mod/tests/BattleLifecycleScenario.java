import game.GAME;
import game.battle.Army;
import game.battle.div.Div;
import game.battle.state.*;
import game.battle.thread.order.BattleOrderTask;
import game.battle.util.DivGeneration;
import game.battle.util.DIV_SPEC.DIV_SPECImp;
import init.constant.C;
import init.type.CAUSE_LEAVES;
import settlement.entity.ENTITY;
import settlement.entity.humanoid.Humanoid;
import settlement.main.SETT;
import snake2d.CORE;
import snake2d.MButt;
import snake2d.util.datatypes.Coo;
import snake2d.util.gui.GuiSection;
import snake2d.util.gui.clickable.CLICKABLE;
import snake2d.util.gui.renderable.RENDEROBJ;
import view.battle.UIBattleResult;
import view.main.VIEW;
import util.text.Dic;
import world.WORLD;
import world.battle.spec.BATTLE_RESULT;
import java.nio.file.*;
import java.time.Instant;
import java.util.*;
import syx.assistant.JsonWriter;

/** TEST ONLY: normal public game UI dispatch; no OS/native input, screenshots or private reads. */
public final class BattleLifecycleScenario {
    static Path output;static String phase;static int round;static long began,started;
    static boolean engagementSeen;
    static void announce(String name) {
        phase=name;began=System.currentTimeMillis();
        try {Files.writeString(output.resolve("phase.json"),JsonWriter.encode(Map.of("phase",name,"started_at",Instant.now().toString(),"engagement_seen",engagementSeen)));}
        catch(Exception error){throw new IllegalStateException(error);}
        System.err.println("BATTLE LIFECYCLE: "+name);
    }
    public static void install(Path directory) {
        output=directory;started=System.currentTimeMillis();
        try {Files.createDirectories(output);}catch(Exception error){throw new IllegalStateException(error);}
        VIEW.s().activate();GAME.SPEED.speedSet(0);round=0;announce("city");register();
    }
    static String suffix(){return round==0?"victory":"defeat";}
    static void register(){GAME.addAfterUpdate(()->{try{step();}catch(Exception error){System.err.println("BATTLE FIXTURE FAILURE: "+error);CORE.annihilate(error);}});}
    static DivGeneration division(String name) {
        DIV_SPECImp spec=new DIV_SPECImp();spec.raceSet(GAME.player().race());spec.menSet(40);
        spec.nameE().clear().add(name);spec.factionSet(GAME.player());return new DivGeneration(spec,spec);
    }
    static Div populated(Army army){for(Div d:army.divisions())if(d.menNrOf()>0)return d;throw new IllegalStateException("No populated division");}
    static void generate() {
        engagementSeen=false;
        BattleStateSpec spec=new BattleStateSpec();spec.player.wCoo.set(WORLD.TWIDTH()/2,WORLD.THEIGHT()/2);
        spec.enemy.wCoo.set(WORLD.TWIDTH()/2+1,WORLD.THEIGHT()/2);spec.player.moraleBase=1;spec.enemy.moraleBase=1;
        spec.player.divs.add(division("Fixture player"));spec.enemy.divs.add(division("Fixture enemy"));
        BattleState.setGenerate(new BattleStateExiter(){public void afterExit(BattleStateResult result){
            BATTLE_RESULT expected=round==0?BATTLE_RESULT.VICTORY:BATTLE_RESULT.DEFEAT;
            if(result.result!=expected)throw new IllegalStateException("Unexpected result "+result.result+" expected "+expected);
            VIEW.inters().load.deactivate();VIEW.s().activate();GAME.SPEED.speedSet(0);
            announce("after_"+suffix());register();
        }},spec);
        GAME.SPEED.speedSet(0);announce("deployment_"+suffix());
    }
    static void startViaPublicDispatcher() {
        // IDeploy's source places its Start button at the top center. Dispatch through the same
        // public manager route used by VIEW; do not obtain the private button or overlay instance.
        VIEW.b().uiManager.hover(new Coo(C.WIDTH()/2,1),true);VIEW.b().uiManager.click(MButt.LEFT);
        if(VIEW.b().state().deploying())throw new IllegalStateException("Public dispatch did not start battle");
        Div player=populated(GAME.ARMIES().player()),enemy=populated(GAME.ARMIES().enemy());
        BattleOrderTask order=new BattleOrderTask();order.attackMelee(enemy,player);player.order().task.set(order);
        order=new BattleOrderTask();order.attackMelee(player,enemy);enemy.order().task.set(order);
        GAME.SPEED.speedSet(5);announce("running_"+suffix());
    }
    static boolean fighting(){for(Army army:Arrays.asList(GAME.ARMIES().player(),GAME.ARMIES().enemy()))for(Div d:army.divisions())if(d.menNrOf()>0 && d.status().isFighting())return true;return false;}
    static void applyFixtureElimination() {
        // Deterministic result-screen setup after genuine engagement; this is not an AI victory benchmark.
        Army losing=round==0?GAME.ARMIES().enemy():GAME.ARMIES().player();
        List<Humanoid> remove=new ArrayList<>();
        for(ENTITY e:SETT.ENTITIES().getAllEnts())if(e instanceof Humanoid && !e.isRemoved()) {
            Humanoid h=(Humanoid)e;if(h.division()!=null && h.division().army()==losing)remove.add(h);
        }
        for(Humanoid h:remove)h.kill(false,CAUSE_LEAVES.SLAYED());
        announce("elimination_"+suffix());
    }
    static void closeResultViaPublicDispatcher() {
        // Build the public result-layout type as a coordinate reference from the same game state.
        // Its tree is public; the actual private conclusion overlay is never inspected.
        UIBattleResult reference=new UIBattleResult(round==0?Dic.¤¤Victory:Dic.¤¤Defeat){protected void close(){}};
        reference.body().centerIn(C.DIM());CLICKABLE close=null;
        for(RENDEROBJ obj:reference.elements())if(obj instanceof GuiSection) {
            GuiSection section=(GuiSection)obj;
            if(section.elements().size()==2 && section.elements().get(0) instanceof CLICKABLE && section.elements().get(1) instanceof CLICKABLE)
                close=(CLICKABLE)section.elements().get(0);
        }
        if(close==null)throw new IllegalStateException("Public result layout has no Close reference");
        VIEW.inters().manager.hover(new Coo(close.body().cX(),close.body().cY()),true);
        VIEW.inters().manager.click(MButt.LEFT);
    }
    static void step() {
        if(System.currentTimeMillis()-started>420000)throw new IllegalStateException("Battle fixture watchdog");
        long age=System.currentTimeMillis()-began;
        if(phase.equals("city") && age>7000){generate();return;}
        if(phase.startsWith("deployment_") && age>7000){startViaPublicDispatcher();return;}
        if(phase.startsWith("running_")) {
            if(fighting()){engagementSeen=true;GAME.SPEED.speedSet(1);announce("engagement_"+suffix());return;}
            if(age>90000)throw new IllegalStateException("No engine engagement observed in running battle");
        }
        if(phase.startsWith("engagement_") && age>7000){GAME.SPEED.speedSet(0);applyFixtureElimination();return;}
        if(phase.startsWith("elimination_") && age>3000) {
            Army losing=round==0?GAME.ARMIES().enemy():GAME.ARMIES().player();
            if(losing.men()!=0)throw new IllegalStateException("Fixture elimination incomplete");
            VIEW.inters().manager.hover(new Coo(C.WIDTH()/2,C.HEIGHT()/2),true);
            announce("result_"+suffix());return;
        }
        if(phase.startsWith("result_") && age>7000){closeResultViaPublicDispatcher();return;}
        if(phase.equals("after_victory") && age>7000){round=1;generate();return;}
        if(phase.equals("after_defeat") && age>7000){announce("complete");CORE.annihilate();}
    }
}
