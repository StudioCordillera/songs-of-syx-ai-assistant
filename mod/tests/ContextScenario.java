import game.GAME;
import game.save.GameLoader;
import settlement.entity.ENTITY;
import settlement.entity.humanoid.Humanoid;
import settlement.main.SETT;
import settlement.room.main.RoomBlueprintIns;
import settlement.room.main.RoomInstance;
import view.main.VIEW;
import snake2d.*;
import java.nio.file.*;
import java.time.Instant;
import java.util.*;
import syx.assistant.JsonWriter;

/** TEST ONLY: opens UI via public game methods in an isolated profile and copied save. */
public final class ContextScenario {
    static Path output,save;
    static long began;
    static int phase;
    static void announce(String name) {
        began=System.currentTimeMillis();
        try { Files.writeString(output.resolve("phase.json"),JsonWriter.encode(Map.of("phase",name,"index",phase,"started_at",Instant.now().toString()))); }
        catch(Exception e){throw new IllegalStateException(e);}
        System.err.println("CONTEXT TEST "+phase+": "+name);
    }
    public static void install(Path directory,Path copiedSave) {
        output=directory;save=copiedSave;
        try {Files.createDirectories(output);}catch(Exception e){throw new IllegalStateException(e);}
        VIEW.s().activate();GAME.SPEED.speedSet(0);
        writeHelpExpectations();phase=0;announce("settlement");register();
    }
    static String hash(CharSequence text) throws Exception {
        byte[] digest=java.security.MessageDigest.getInstance("SHA-256").digest((text==null?"":text.toString()).getBytes(java.nio.charset.StandardCharsets.UTF_8));
        StringBuilder result=new StringBuilder();for(byte b:digest)result.append(String.format("%02x",b&255));return result.toString();
    }
    static void writeHelpExpectations() {
        try {
            List<Object> rows=new ArrayList<>();
            for(var blueprint:SETT.ROOMS().all())if(blueprint instanceof settlement.room.main.RoomBlueprintImp) {
                var bp=(settlement.room.main.RoomBlueprintImp)blueprint;
                rows.add(Map.of("id","room:"+bp.key,"category","room","title_sha256",hash(bp.info.name),"text_sha256",hash(bp.info.desc)));
            }
            for(var currency:init.tech.TECHS.COSTS())rows.add(Map.of("id","research_currency:"+currency.bo.key,
                "category","research_currency","title_sha256",hash(currency.bo.name),"text_sha256",hash(currency.bo.desc)));
            Files.writeString(output.resolve("help-fixture.json"),JsonWriter.encode(Map.of("references",rows)));
        }catch(Exception error){throw new IllegalStateException(error);}
    }
    static void register() {
        GAME.addAfterUpdate(()->{
            if(System.currentTimeMillis()-began<7000)return;
            try { next(); }catch(Exception e){System.err.println("CONTEXT TEST FAILURE: "+e);CORE.annihilate(e);}
        });
    }
    static void next() {
        phase++;
        switch(phase) {
            case 1:
                Humanoid last=null;
                for(ENTITY e:SETT.ENTITIES().getAllEnts()) if(e instanceof Humanoid && !e.isRemoved()) last=(Humanoid)e;
                if(last==null) throw new IllegalStateException("No subject fixture");
                VIEW.s().ui.subjects.showSingle(last);announce("subject");return;
            case 2: VIEW.inters().menu.show();announce("game_menu");return;
            case 3:
                VIEW.inters().manager.remove(VIEW.inters().menu);
                VIEW.inters().yesNo.activate("Isolated fixture; do not interact",snake2d.util.misc.ACTION.NOP,snake2d.util.misc.ACTION.NOP,true);
                announce("confirmation");return;
            case 4: VIEW.inters().yesNo.deactivate();VIEW.world().activate();announce("world");return;
            case 5: VIEW.UI().goods.activate();announce("management");return;
            case 6: VIEW.UI().manager.close();VIEW.UI().wiki.activate();announce("encyclopedia");return;
            case 7: VIEW.UI().wiki.hide();VIEW.inters().load.activate();announce("loading_overlay");return;
            case 8:
                VIEW.inters().load.deactivate();VIEW.s().activate();VIEW.s().panels.clear();
                for(RoomBlueprintIns<?> bp:SETT.ROOMS().ins())for(RoomInstance room:bp.all()) {
                    VIEW.s().ui.rooms.open(room);
                    if(VIEW.s().ui.rooms.openIs(bp)){announce("room");return;}
                }
                throw new IllegalStateException("No room fixture with detail/table panels");
            case 9:
                announce("reloading");
                new GameLoader(save) {
                    public void doAfterSet() {
                        VIEW.inters().load.deactivate();VIEW.s().activate();GAME.SPEED.speedSet(0);
                        phase=10;announce("reloaded");register();
                    }
                }.set();return;
            case 11:
                announce("main_menu");
                CORE.setCurrentState(new CORE_STATE.Constructor() {
                    public CORE_STATE getState() {
                        menu.Menu screen=menu.Menu.make();
                        return new CORE_STATE() {
                            final long opened=System.currentTimeMillis();
                            protected void update(float ds,double slow){screen.update(ds,slow);if(System.currentTimeMillis()-opened>37000)CORE.annihilate();}
                            protected void render(Renderer r,float ds){screen.render(r,ds);}
                            protected void mouseClick(MButt b){screen.mouseClick(b);}
                            protected void keyPush(snake2d.util.sets.LIST<KeyBoard.KeyEvent> keys,boolean cleared){}
                        };
                    }
                });return;
            default:throw new IllegalStateException("Unexpected fixture phase "+phase);
        }
    }
}
