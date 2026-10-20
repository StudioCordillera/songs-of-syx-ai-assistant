package syx.assistant;

import game.GAME;
import game.save.GameLoader;
import snake2d.CORE;
import snake2d.MButt;
import snake2d.util.datatypes.Coo;
import snake2d.util.gui.renderable.RENDEROBJ;
import util.gui.misc.GInput;
import util.gui.misc.GTextR;
import view.main.VIEW;
import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.util.*;

/** TEST ONLY: own chat widgets and one copied-save reload; no paid inference or native input. */
public final class ChatAutoConnectScenario {
    private static int phase;
    private static long started;
    private static String chat,firstSession,secondSession,beforeProtocolAction;
    private static final List<String> checks=new ArrayList<>();
    public static void install(Path directory,Path save) {
        phase=0;started=System.nanoTime();checks.clear();VIEW.s().activate();GAME.SPEED.speedSet(1);register(directory,save);
    }
    private static void require(boolean ok,String message){if(!ok)throw new IllegalStateException(message);}
    private static void press(RENDEROBJ row) {
        require(!VIEW.inters().manager.hover(new Coo(row.body().cX(),row.body().cY()),true),"Own hover escaped");
        require(!VIEW.inters().manager.click(MButt.LEFT),"Own click escaped");
    }
    private static GInput composer(ChatPanel panel) {
        for(RENDEROBJ row:panel.section().elements())if(row instanceof GInput)return (GInput)row;
        throw new IllegalStateException("No composer");
    }
    private static void send(ChatPanel panel,String text){composer(panel).text().clear().add(text);press(panel.section().elements().get(panel.section().elements().size()-2));}
    private static void filter(ChatPanel panel) {
        for(RENDEROBJ row:panel.section().elements())if(row.body().x1()==460&&row.body().y1()==86){press(row);return;}
        throw new IllegalStateException("No history filter");
    }
    private static boolean completed(Path directory)throws Exception {
        String ui=Files.readString(directory.resolve("chat-ui.txt"));
        String request=Files.readAllLines(directory.resolve("chat-action.txt")).get(0);
        String notice="";for(String line:ui.split("\n"))if(line.startsWith("notice="))notice=new String(Base64.getDecoder().decode(line.substring(7)),StandardCharsets.UTF_8);
        if(notice.startsWith("Reply failed"))throw new IllegalStateException("Simulated reply failed");
        return notice.equals("Reply completed")&&ui.contains(request+"\n")&&ui.contains("running=false\n");
    }
    private static boolean ready(ChatPanel panel,Path directory,String stage)throws Exception {
        String session=panel.context().get("runtime_session_id").toString();
        Files.writeString(directory.resolve("native-phase.json"),JsonWriter.encode(StateCollector.object("phase",stage,"session_id",session)));
        return Files.exists(directory.resolve("session-ready-"+session));
    }
    private static void register(Path directory,Path save) {
        GAME.addAfterUpdate(()->{
            try {
                if(System.nanoTime()-started>210_000_000_000L)throw new IllegalStateException("Automatic connection fixture timeout");
                ChatPanel panel=AssistantScript.currentChatPanel();if(panel==null)return;
                Map<String,Object> c=panel.context();
                switch(phase) {
                    case 0:
                        if(!ready(panel,directory,"initial"))return;
                        firstSession=c.get("runtime_session_id").toString();press(panel.section().elements().get(0));phase=1;break;
                    case 1:
                        if(c.get("chat_id")==null||Boolean.TRUE.equals(c.get("action_pending")))return;
                        require(Boolean.TRUE.equals(c.get("automatic_connection")),"No automatic player mode");
                        chat=c.get("chat_id").toString();checks.add("opening creates/selects Pro conversation without New or Attach");
                        send(panel,"First session fixture question");phase=2;break;
                    case 2:
                        if(!completed(directory)||Boolean.TRUE.equals(c.get("action_pending")))return;
                        checks.add("first simulated reply completed");phase=-1;
                        new GameLoader(save){public void doAfterSet(){
                            VIEW.inters().load.deactivate();VIEW.s().activate();GAME.SPEED.speedSet(1);phase=3;register(directory,save);
                        }}.set();return;
                    case 3:
                        if(!ready(panel,directory,"reloaded"))return;
                        secondSession=c.get("runtime_session_id").toString();require(!firstSession.equals(secondSession),"Session did not rotate");
                        if(!Boolean.TRUE.equals(c.get("panel_open")))press(panel.section().elements().get(0));phase=4;break;
                    case 4:
                        if(Boolean.TRUE.equals(c.get("action_pending"))||!chat.equals(c.get("chat_id")))return;
                        require(!Boolean.TRUE.equals(c.get("attachment_required")),"Player still requires manual attachment");
                        for(RENDEROBJ row:panel.section().elements())require(row.body().x1()!=340||row.body().y1()!=86,"Manual attachment button visible");
                        Files.writeString(directory.resolve("test-reconnect-notice"),"ready\n");
                        boolean errorVisible=false;
                        for(RENDEROBJ row:panel.section().elements())if(row instanceof GTextR&&((GTextR)row).text().toString().equals("Game connection timed out; no question was sent"))errorVisible=true;
                        if(!errorVisible)return;
                        checks.add("reconnect hint does not hide a coordinator error for an older chat");
                        send(panel,"Second session fixture question");phase=5;break;
                    case 5:
                        if(!completed(directory)||Boolean.TRUE.equals(c.get("action_pending"))||!secondSession.equals(c.get("attached_session_id")))return;
                        require(chat.equals(c.get("chat_id")),"Automatic reconnect changed conversation");
                        checks.add("same chat reconnects on question after real reload without Attach");
                        Files.writeString(directory.resolve("populate-filters"),"ready\n");phase=6;break;
                    case 6:
                        if(!Files.exists(directory.resolve("filters-populated.done"))||((Number)c.get("all_listed_chat_count")).intValue()!=2)return;
                        require(((Number)c.get("listed_chat_count")).intValue()==1,"Current-load list leaked old load");
                        filter(panel);require(((Number)panel.context().get("listed_chat_count")).intValue()==2,"All-chats filter missing history");
                        filter(panel);require(((Number)panel.context().get("listed_chat_count")).intValue()==1,"Current filter did not restore");
                        checks.add("This load / All chats switch exposes expected own rows");
                        beforeProtocolAction=Files.readString(directory.resolve("chat-action.txt"));
                        Files.writeString(directory.resolve("test-old-protocol"),"ready\n");phase=7;break;
                    case 7:
                        if(((Number)c.get("coordinator_protocol")).intValue()!=1)return;
                        send(panel,"Must not send to incompatible helper");
                        require(Files.readString(directory.resolve("chat-action.txt")).equals(beforeProtocolAction),"Old-protocol send escaped");
                        require(composer(panel).text().toString().equals("Must not send to incompatible helper"),"Refused send lost draft");
                        checks.add("protocol 1 refused without clearing unsent question");
                        Files.writeString(directory.resolve("protocol-refusal-checked"),"verified\n");phase=8;break;
                    case 8:
                        if(((Number)c.get("coordinator_protocol")).intValue()!=2)return;
                        require(composer(panel).text().toString().equals("Must not send to incompatible helper"),"Protocol recovery lost draft");
                        Files.writeString(directory.resolve("draft-switch-request"),"ready\n");phase=9;break;
                    case 9:
                        if(chat.equals(c.get("chat_id")))return;
                        require(composer(panel).text().length()==0,"Another chat inherited the unsent draft");
                        Files.writeString(directory.resolve("draft-switch-back"),"ready\n");phase=10;break;
                    case 10:
                        if(!chat.equals(c.get("chat_id")))return;
                        require(composer(panel).text().toString().equals("Must not send to incompatible helper"),"Chat round-trip lost draft");
                        checks.add("per-chat unsent draft survives coordinator selection round-trip");
                        Files.writeString(directory.resolve("auto-native-validation.json"),JsonWriter.encode(StateCollector.object("passed",true,"checks",checks,"reloads",1)));
                        phase=11;break;
                    case 11:
                        if(!Files.exists(directory.resolve("verifier.done")))return;
                        Files.writeString(directory.resolve("auto-clean-exit.json"),"{\"passed\":true,\"turns\":2,\"reloads\":1}");
                        phase=12;CORE.annihilate();return;
                }
            } catch(Exception error) {
                System.err.println("SMOKE_FIXTURE_FAILURE: "+error);
                try{Files.writeString(directory.resolve("auto-fixture-failure.json"),error.getClass().getSimpleName());}catch(Exception ignored){}
                CORE.annihilate(error);
            }
        });
    }
}
