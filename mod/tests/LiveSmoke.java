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
