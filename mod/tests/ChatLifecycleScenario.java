package syx.assistant;

import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import game.GAME;
import game.save.GameLoader;
import snake2d.CORE;
import snake2d.MButt;
import snake2d.util.datatypes.Coo;
import snake2d.util.gui.renderable.RENDEROBJ;
import util.gui.misc.GInput;
import view.main.VIEW;

/** TEST ONLY: own chat history controls and explicit attachment after copied-save reload. No inference. */
public final class ChatLifecycleScenario {
    private static long started,last;
    private static int phase;
    private static String chat,session,beforeAction;
    private static final List<String> checks=new ArrayList<>();
    public static void install(Path directory,Path save) {
        started=last=System.currentTimeMillis();phase=0;checks.clear();register(directory,save);
    }
    private static void register(Path directory,Path save) {
        GAME.addAfterUpdate(()->{
            long now=System.currentTimeMillis();if(now-last<1800)return;
            try {
                if(now-started>150000)throw new IllegalStateException("Chat lifecycle exceeded 150 seconds");
                ChatPanel panel=AssistantScript.currentChatPanel();require(panel!=null,"No panel");
                switch(phase) {
                    case 0:press(panel.section().elements().get(0));phase=1;break;
                    case 1:press(panel.section().elements().get(1));phase=2;break;
                    case 2:
                        if(panel.context().get("chat_id")==null)return;
                        chat=panel.context().get("chat_id").toString();session=panel.context().get("runtime_session_id").toString();
                        text(panel,"Lifecycle chat");at(panel,16,640);phase=3;break;
                    case 3:
                        if(!notice(directory).equals("Chat renamed"))return;
                        checks.add("rename through own GUI");at(panel,650,86);phase=4;break;
                    case 4:
                        if(!notice(directory).equals("Tool evidence expanded"))return;
                        checks.add("evidence toggle through own GUI");VIEW.world().activate();phase=5;break;
                    case 5:
                        require(panel.isActivated(),"Panel lost in world");VIEW.s().activate();VIEW.inters().menu.show();phase=6;break;
                    case 6:
                        require(panel.isActivated()&&VIEW.inters().menu.isActivated(),"Chat disturbed native menu");
                        checks.add("own panel persists without closing game menu");VIEW.inters().manager.remove(VIEW.inters().menu);
                        phase=7;
                        new GameLoader(save) {
                            public void doAfterSet() {
                                VIEW.inters().load.deactivate();VIEW.s().activate();GAME.SPEED.speedSet(0);
                                phase=8;last=System.currentTimeMillis();register(directory,save);
                            }
                        }.set();return;
                    case 8:
                        require(!session.equals(panel.context().get("runtime_session_id")),"Reload failed to rotate runtime identity");
                        if(!Boolean.TRUE.equals(panel.context().get("panel_open")))press(panel.section().elements().get(0));
                        if(!chat.equals(panel.context().get("chat_id")))return;
                        require(Boolean.TRUE.equals(panel.context().get("attachment_required")),"Reload silently attached old chat");
                        beforeAction=Files.readString(directory.resolve("chat-action.txt"));
                        text(panel,"Must not send before explicit attachment");send(panel);phase=9;break;
                    case 9:
                        require(beforeAction.equals(Files.readString(directory.resolve("chat-action.txt"))),"Wrong-session send was admitted");
                        checks.add("reload preserves chat and rejects send before explicit attachment");
                        at(panel,340,86);phase=10;break;
                    case 10:
                        if(Boolean.TRUE.equals(panel.context().get("attachment_required")))return;
                        require(chat.equals(panel.context().get("chat_id")),"Attach lost chat identity");
                        checks.add("explicit attach after reload");at(panel,200,640);phase=11;break;
                    case 11:
                        if(!notice(directory).startsWith("Chat exported locally:"))return;
                        checks.add("local export through own GUI");at(panel,340,640);phase=12;break;
                    case 12:
                        require(chat.equals(panel.context().get("chat_id")),"Delete was not confirmed");
                        at(panel,340,640);phase=13;break;
                    case 13:
                        if(panel.context().get("chat_id")!=null)return;
                        checks.add("confirmed deletion through own GUI");phase=14;
                        Files.writeString(directory.resolve("chat-lifecycle-validation.json"),JsonWriter.encode(Map.of(
                            "passed",true,"checks",checks,"limitations",List.of("No physical keyboard test","Standalone main menu has no established script lifecycle","No battle or world-generation input test"))));
                        System.err.println("CHAT LIFECYCLE PASS");CORE.annihilate();return;
                }
                last=now;
            }catch(Exception error){phase=99;System.err.println("CHAT LIFECYCLE FAILURE: "+error);CORE.annihilate(error);}
        });
    }
    private static String notice(Path directory)throws Exception {
        for(String line:Files.readAllLines(directory.resolve("chat-ui.txt")))if(line.startsWith("notice="))return new String(Base64.getDecoder().decode(line.substring(7)),StandardCharsets.UTF_8);
        return "";
    }
    private static void text(ChatPanel panel,String value) {
        for(RENDEROBJ row:panel.section().elements())if(row instanceof GInput){((GInput)row).text().clear().add(value);return;}
        throw new IllegalStateException("No composer");
    }
    private static void send(ChatPanel panel){press(panel.section().elements().get(panel.section().elements().size()-2));}
    private static void at(ChatPanel panel,int x,int y) {
        for(RENDEROBJ row:panel.section().elements())if(row.body().x1()==x&&row.body().y1()==y){press(row);return;}
        throw new IllegalStateException("Own control missing");
    }
    private static void require(boolean value,String message){if(!value)throw new IllegalStateException(message);}
    private static void press(RENDEROBJ control) {
        require(!VIEW.inters().manager.hover(new Coo(control.body().cX(),control.body().cY()),true),"Own hover not consumed");
        require(!VIEW.inters().manager.click(MButt.LEFT),"Own click passed through");
    }
}
