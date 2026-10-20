import java.nio.file.Paths;
import game.GAME;
import game.save.GameLoader;
import init.paths.PATHS;
import init.settings.S;
import launcher.LSettings;
import snake2d.*;
import snake2d.util.sets.LIST;
import util.error.ErrorHandler;
import util.text.D;

/** Loads only a copied save using a throwaway user.home. No automatic input. */
public final class LiveSmoke {
    public static void main(String[] args) {
        if (args.length != 1) throw new IllegalArgumentException("Pass a COPIED save file");
        PathCheck.validate(args[0]);
        if(Boolean.getBoolean("syx.smoke.validateOnly")) {System.out.println("Fixture paths validated");return;}
        CORE.init(new ErrorHandler() {
            @Override public void handle(String output,String dump) {
                // Keep engine stderr in the test log, without launching its external Swing error dialog.
                System.out.println("SMOKE_CAPTURED_ENGINE_OUTPUT: "+output);
            }
        });
        LSettings settings = new LSettings();
        settings.screenMode.set(2); settings.windowWidth.set(12); settings.windowHeight.set(9);
        settings.rpc.set(0); settings.save();
        PATHS.init(new String[]{"syx-ai-assistant"}, null, false);
        D.init(); CORE.create(S.get().make());
        CORE.start(new CORE_STATE.Constructor() {
            public CORE_STATE getState() {
                menu.Menu screen=menu.Menu.make();
                return new CORE_STATE() {
                    final long start=System.currentTimeMillis();
                    boolean loading;
                    protected void update(float ds,double slow) {
                        screen.update(ds,slow);
                        if (!loading && System.currentTimeMillis()-start>1000) {
                            loading=true;
                            System.err.println("SMOKE: loading copied save on updater thread");
                            new GameLoader(Paths.get(args[0])) {
                                public void doAfterSet() {
                                    GAME.SPEED.speedSet(0);
                                    view.main.VIEW.inters().load.deactivate();
                                    if (Boolean.getBoolean("syx.smoke.chatVisibility")) {
                                        syx.assistant.ChatVisibilityScenario.install(Paths.get(System.getProperty("syx.assistant.stateDir")));
                                        return;
                                    }
                                    if (Boolean.getBoolean("syx.smoke.chatAuto")) {
                                        syx.assistant.ChatAutoConnectScenario.install(Paths.get(System.getProperty("syx.assistant.stateDir")),Paths.get(args[0]));
                                        return;
                                    }
                                    if (Boolean.getBoolean("syx.smoke.chatBackground")) {
                                        syx.assistant.ChatBackgroundScenario.install(Paths.get(System.getProperty("syx.assistant.stateDir")));
                                        return;
                                    }
                                    if (Boolean.getBoolean("syx.smoke.viewport")) {
                                        ViewportScenario.install(Paths.get(System.getProperty("syx.assistant.stateDir")));
                                        return;
                                    }
                                    if (Boolean.getBoolean("syx.smoke.groundMoisture")) {
                                        GroundMoistureScenario.install(Paths.get(System.getProperty("syx.assistant.stateDir")));
                                        return;
                                    }
                                    if (Boolean.getBoolean("syx.smoke.regionalCapture")) {
                                        RegionalCaptureScenario.install(Paths.get(System.getProperty("syx.assistant.stateDir")),Paths.get(args[0]));
                                        return;
                                    }
                                    if (Boolean.getBoolean("syx.smoke.regionalCost")) {
                                        RegionalCostScenario.install(Paths.get(System.getProperty("syx.assistant.stateDir")));
                                        return;
                                    }
                                    if (Boolean.getBoolean("syx.smoke.regionalLive")) {
                                        RegionalLiveScenario.install(Paths.get(System.getProperty("syx.assistant.stateDir")),Paths.get(args[0]));
                                        return;
                                    }
                                    if (Boolean.getBoolean("syx.smoke.regionalExport")) {
                                        RegionalOutputExportScenario.install(Paths.get(System.getProperty("syx.assistant.stateDir")));
                                        return;
                                    }
                                    if (Boolean.getBoolean("syx.smoke.regionalOutput")) {
                                        RegionalOutputScenario.install(Paths.get(System.getProperty("syx.assistant.stateDir")));
                                        return;
                                    }
                                    if (Boolean.getBoolean("syx.smoke.worldLists")) {
                                        WorldListScenario.install(Paths.get(System.getProperty("syx.assistant.stateDir")));
                                        return;
                                    }
                                    if (Boolean.getBoolean("syx.smoke.factionUi")) {
                                        FactionUiScenario.install(Paths.get(System.getProperty("syx.assistant.stateDir")));
                                        return;
                                    }
                                    if (Boolean.getBoolean("syx.smoke.stockpile")) {
                                        StockpileScenario.install(Paths.get(System.getProperty("syx.assistant.stateDir")));
                                        return;
                                    }
                                    if (Boolean.getBoolean("syx.smoke.collectionCost")) {
                                        CollectionCostScenario.install(Paths.get(System.getProperty("syx.assistant.stateDir")));
                                        return;
                                    }
                                    if (Boolean.getBoolean("syx.smoke.services")) {
                                        ServiceScenario.install(Paths.get(System.getProperty("syx.assistant.stateDir")));
                                        return;
                                    }
                                    if (Boolean.getBoolean("syx.smoke.trade")) {
                                        TradeScenario.install(Paths.get(System.getProperty("syx.assistant.stateDir")));
                                        return;
                                    }
                                    if (Boolean.getBoolean("syx.smoke.world")) {
                                        WorldScenario.install(Paths.get(System.getProperty("syx.assistant.stateDir")));
                                        return;
                                    }
                                    if (Boolean.getBoolean("syx.smoke.degradationPositive")) {
                                        DegradationPositiveScenario.install(Paths.get(System.getProperty("syx.assistant.stateDir")));
                                        return;
                                    }
                                    if (Boolean.getBoolean("syx.smoke.production")) {
                                        ProductionScenario.install(Paths.get(System.getProperty("syx.assistant.stateDir")));
                                        return;
                                    }
                                    if (Boolean.getBoolean("syx.smoke.research")) {
                                        ResearchScenario.install(Paths.get(System.getProperty("syx.assistant.stateDir")));
                                        return;
                                    }
                                    if (Boolean.getBoolean("syx.smoke.chatLifecycle")) {
                                        syx.assistant.ChatLifecycleScenario.install(Paths.get(System.getProperty("syx.assistant.stateDir")),Paths.get(args[0]));
                                        return;
                                    }
                                    if (Boolean.getBoolean("syx.smoke.chatLive")) {
                                        syx.assistant.ChatLiveScenario.install(Paths.get(System.getProperty("syx.assistant.stateDir")));
                                        return;
                                    }
                                    if (Boolean.getBoolean("syx.smoke.chat")) {
                                        syx.assistant.ChatUiScenario.install(Paths.get(System.getProperty("syx.assistant.stateDir")));
                                        return;
                                    }
                                    if (Boolean.getBoolean("syx.smoke.tiles")) {
                                        TileScenario.install(Paths.get(System.getProperty("syx.assistant.stateDir")),Paths.get(args[0]));
                                        return;
                                    }
                                    if (Boolean.getBoolean("syx.smoke.battleLifecycle")) {
                                        BattleLifecycleScenario.install(Paths.get(System.getProperty("syx.assistant.stateDir")));
                                        return;
                                    }
                                    if (Boolean.getBoolean("syx.smoke.extended")) {
                                        ExtendedContextScenario.install(Paths.get(System.getProperty("syx.assistant.stateDir")),Paths.get(args[0]));
                                        return;
                                    }
                                    if (Boolean.getBoolean("syx.smoke.entities") || Boolean.getBoolean("syx.smoke.capture")) {
                                        EntityScenario.install(Paths.get(System.getProperty("syx.assistant.stateDir")));
                                        return;
                                    }
                                    if (Boolean.getBoolean("syx.smoke.scenes")) {
                                        SceneScenario.install(Paths.get(System.getProperty("syx.assistant.stateDir")),Paths.get(args[0]));
                                        return;
                                    }
                                    if (Boolean.getBoolean("syx.smoke.context")) {
                                        ContextScenario.install(Paths.get(System.getProperty("syx.assistant.stateDir")),Paths.get(args[0]));
                                        return;
                                    }
                                    final long loaded=System.currentTimeMillis();
                                    GAME.addAfterUpdate(() -> { if (System.currentTimeMillis()-loaded>180_000) CORE.annihilate(); });
                                }
                            }.set();
                        }
                    }
                    protected void render(Renderer r,float ds) { screen.render(r,ds); }
                    protected void mouseClick(MButt b) { screen.mouseClick(b); }
                    protected void keyPush(LIST<KeyBoard.KeyEvent> keys,boolean cleared) { }
                };
            }
        });
    }
}


/** Refuse accidental use of the real profile or original saves before the engine starts. */
final class PathCheck {
    static void validate(String save) {
        try {
            String configured=System.getProperty("syx.assistant.stateDir");
            if(configured==null)throw new IllegalArgumentException("Set an isolated state directory");
            java.nio.file.Path root=java.nio.file.Paths.get(configured).toAbsolutePath().normalize().getParent().toRealPath();
            java.nio.file.Path expected=root.resolve("smoke-home");
            if(java.nio.file.Files.isSymbolicLink(expected))throw new IllegalArgumentException("Fixture home must not be a symlink");
            java.nio.file.Path home=java.nio.file.Paths.get(System.getProperty("user.home")).toRealPath();
            if(!home.equals(expected.toRealPath()))throw new IllegalArgumentException("Use the sibling smoke-home profile, never your normal home");
            if(!java.nio.file.Paths.get(save).toRealPath().startsWith(root))throw new IllegalArgumentException("Save must be a copy inside the fixture runtime root");
        } catch(java.io.IOException e){throw new IllegalArgumentException("Fixture paths must exist",e);}
    }
}
