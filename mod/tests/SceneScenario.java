import game.GAME;
import game.save.GameLoader;
import game.battle.state.*;
import game.battle.util.DivGeneration;
import game.battle.util.DIV_SPEC.DIV_SPECImp;
import init.paths.PATHS;
import view.main.VIEW;
import view.world.generator.WorldViewGenerator;
import world.WORLD;
import snake2d.*;
import java.nio.file.*;
import java.time.Instant;
import java.util.*;
import syx.assistant.JsonWriter;

/** TEST ONLY: valid battle generation/new-game public setup paths, isolated home and copied save. */
public final class SceneScenario {
    static Path output,save;
    static long began;
    static int phase;
    static void announce(String name) {
        began=System.currentTimeMillis();
        try {Files.writeString(output.resolve("phase.json"),JsonWriter.encode(Map.of("phase",name,"index",phase,"started_at",Instant.now().toString())));}
        catch(Exception e){throw new IllegalStateException(e);}
        System.err.println("SCENE TEST "+phase+": "+name);
    }
    public static void install(Path directory,Path copiedSave) {
        output=directory;save=copiedSave;
        try {Files.createDirectories(output);}catch(Exception e){throw new IllegalStateException(e);}
        VIEW.s().activate();GAME.SPEED.speedSet(0);phase=0;announce("city");register();
    }
    static void register() {
        GAME.addAfterUpdate(()->{
            if(System.currentTimeMillis()-began<8000)return;
            try {next();}catch(Exception e){System.err.println("SCENE TEST FAILURE: "+e);CORE.annihilate(e);}
        });
    }
    static DivGeneration division(String name) {
        DIV_SPECImp spec=new DIV_SPECImp();
        spec.raceSet(GAME.player().race());spec.menSet(10);spec.nameE().clear().add(name);spec.factionSet(GAME.player());
        return new DivGeneration(spec,spec);
    }
    static void next() {
        phase++;
        switch(phase) {
            case 1: VIEW.s().battle.activate();announce("settlement_battle");return;
            case 2: VIEW.s().activate();announce("city_restored");return;
            case 3:
                BattleStateSpec spec=new BattleStateSpec();
                spec.player.wCoo.set(WORLD.TWIDTH()/2,WORLD.THEIGHT()/2);
                spec.enemy.wCoo.set(WORLD.TWIDTH()/2+1,WORLD.THEIGHT()/2);
                spec.player.moraleBase=1;spec.enemy.moraleBase=1;
                spec.player.divs.add(division("Fixture player"));spec.enemy.divs.add(division("Fixture enemy"));
                // BattleState writes its own fixture saves only under the isolated user.home.
                BattleState.setGenerate(new BattleStateExiter(){public void afterExit(BattleStateResult result){}},spec);
                GAME.SPEED.speedSet(0);announce("battle_deployment");return;
            case 4: VIEW.inters().menu.show();announce("battle_menu");return;
            case 5:
                announce("restoring_city");
                new GameLoader(save) {
                    public void doAfterSet() {
                        VIEW.inters().load.deactivate();VIEW.s().activate();GAME.SPEED.speedSet(0);
                        phase=6;announce("city_reloaded");register();
                    }
                }.set();return;
            case 7:
                announce("new_game_pending");
                CORE.setCurrentState(new CORE_STATE.Constructor() {
                    public CORE_STATE getState() {
                        VIEW view=GAME.create();GAME.SPEED.speedSet(0);VIEW.inters().load.deactivate();
                        phase=8;announce("world_generation");register();return view;
                    }
                });return;
            case 9:
                WORLD.TERRAIN().saver().generate(WorldViewGenerator.loadPrint);
                WORLD.LANDMARKS().saver().generate(WorldViewGenerator.loadPrint);
                WORLD.MINIMAP().repaint();WORLD.GEN().hasGeneratedTerrain=true;
                init.sprite.SPRITES.loader().minify(false,"");
                announce("terrain_generated");return;
            case 10: announce("complete");CORE.annihilate();return;
            default:throw new IllegalStateException("Unexpected scene fixture phase "+phase);
        }
    }
}
