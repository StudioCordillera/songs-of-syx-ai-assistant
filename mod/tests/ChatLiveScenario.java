package syx.assistant;

import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import game.GAME;
import snake2d.CORE;
import snake2d.MButt;
import snake2d.util.datatypes.Coo;
import snake2d.util.gui.renderable.RENDEROBJ;
import util.gui.misc.GInput;
import view.main.VIEW;

/** TEST ONLY: two explicitly requested paid turns through mod-owned GUI controls. */
public final class ChatLiveScenario {
    private static long started,last;
    private static int phase;
    private static String chat,previousAction,deepseekChat;
    private static boolean secondProvider;
    public static void install(Path directory) {
        started=last=System.currentTimeMillis();phase=0;secondProvider=false;
        GAME.addAfterUpdate(()->{
            long now=System.currentTimeMillis();if(now-last<1500)return;
            try {
                if(now-started>420000)throw new IllegalStateException("Live chat fixture exceeded seven minutes");
                ChatPanel panel=AssistantScript.currentChatPanel();require(panel!=null,"No panel");
                switch(phase) {
                    case 0:press(panel.section().elements().get(0));phase=1;break;
                    case 1:
                        if(Boolean.getBoolean("syx.smoke.chatClaude")) {
                            boolean found=false;
                            for(RENDEROBJ row:panel.section().elements())if(row.body().x1()==650&&row.body().y1()==640){press(row);found=true;break;}
                            require(found,"No Claude subscription choice");
                        }else if(!Boolean.TRUE.equals(panel.context().get("automatic_connection")))press(panel.section().elements().get(1));
                        phase=2;break;
                    case 2:
                        Object id=panel.context().get("chat_id");if(id==null)return;
                        if(secondProvider && !"claude".equals(panel.context().get("provider")))return;
                        if(secondProvider)require(!id.toString().equals(deepseekChat),"Provider switch reused the earlier chat");
                        if(!Boolean.getBoolean("syx.smoke.chatClaude")&&!secondProvider) {
                            require("simple".equals(panel.context().get("interface")),"Expected simple player interface");
                            require("deepseek-v4-pro".equals(panel.context().get("model")),"Expected DeepSeek Pro");
                            for(RENDEROBJ control:panel.section().elements())if(control instanceof GInput) {
                                require(control.body().width()==792,"Question box width is incorrect");
                                require(control.body().y2()<620,"Question box overlaps its hint or send controls");
                                require(((GInput)control).text().length()+((GInput)control).text().spaceLeft()==240,"Question capacity is incorrect");
                            }
                            for(RENDEROBJ control:panel.section().elements())require(control.body().x1()!=650,"Developer/provider control is visible");
                        }
                        chat=id.toString();send(panel,directory,Boolean.getBoolean("syx.smoke.chatSelect")?"Use select_game_state: 3 least positive owned.":Boolean.getBoolean("syx.smoke.chatGuidance")?"Use search_guidance: food. Cite a URL briefly.":"Use tools: population total; cite session and tick.");phase=3;break;
                    case 3:
                        if(!complete(directory)||Boolean.TRUE.equals(panel.context().get("generating")))return;
                        require(chat.equals(panel.context().get("chat_id")),"Chat changed");
                        Files.copy(directory.resolve("snapshot.json"),directory.resolve("first-answer-observation.json"),StandardCopyOption.REPLACE_EXISTING);
                        send(panel,directory,Boolean.getBoolean("syx.smoke.chatSelect")?"Use search_guidance food; cite one source URL.":Boolean.getBoolean("syx.smoke.chatGuidance")?"Select 3 resources with least positive owned.":"Use UI context and a cited food guide. Be brief.");phase=4;break;
                    case 4:
                        if(!complete(directory)||Boolean.TRUE.equals(panel.context().get("generating")))return;
                        require(chat.equals(panel.context().get("chat_id")),"Follow-up changed chat");
                        if(Boolean.getBoolean("syx.smoke.chatBoth")&&!secondProvider) {
                            deepseekChat=chat;secondProvider=true;
                            boolean found=false;
                            for(RENDEROBJ row:panel.section().elements())if(row.body().x1()==650&&row.body().y1()==640){press(row);found=true;break;}
                            require(found,"No Claude subscription choice");phase=2;last=now;return;
                        }
                        phase=5;
                        Files.copy(directory.resolve("snapshot.json"),directory.resolve("chat-observation.json"),StandardCopyOption.REPLACE_EXISTING);
                        Files.writeString(directory.resolve("chat-live-gui-validation.json"),JsonWriter.encode(Map.of(
                            "passed",true,"checks",List.of(Boolean.getBoolean("syx.smoke.chatBoth")?"GUI send with real DeepSeek API and Claude subscription in separate chats":Boolean.getBoolean("syx.smoke.chatClaude")?"GUI send with real Claude subscription":"GUI send with real DeepSeek API","two completed turns in same chat","own clicks consumed"),
                            "limitations",List.of("Text entered through test-only own-widget API; no physical keyboard test","Limited city scene","Answer/citation quality verified separately"))));
                        System.err.println("CHAT LIVE GUI PASS");CORE.annihilate();return;
                }
                last=now;
            }catch(Exception error){phase=99;System.err.println("CHAT LIVE GUI FAILURE: "+error);CORE.annihilate(error);}
        });
    }
    private static boolean complete(Path directory)throws Exception {
        String ui=Files.readString(directory.resolve("chat-ui.txt"));
        String action=Files.readAllLines(directory.resolve("chat-action.txt")).get(0);
        if(action.equals(previousAction))return false;
        if(!ui.contains(action+"\n"))return false;
        String notice="";
        for(String line:ui.split("\n"))if(line.startsWith("notice="))notice=new String(Base64.getDecoder().decode(line.substring(7)),StandardCharsets.UTF_8);
        if(notice.startsWith("Reply failed")||notice.contains("rejected"))throw new IllegalStateException("Coordinator rejected/failed the live turn; inspect private history");
        return notice.equals("Reply completed")&&ui.contains("running=false\n");
    }
    private static void send(ChatPanel panel,Path directory,String text)throws Exception {
        previousAction=Files.readAllLines(directory.resolve("chat-action.txt")).get(0);
        GInput composer=null;
        for(RENDEROBJ row:panel.section().elements())if(row instanceof GInput)composer=(GInput)row;
        require(composer!=null,"No composer");composer.text().clear().add(text);
        require(composer.text().toString().equals(text),"Question does not fit composer");
        press(panel.section().elements().get(panel.section().elements().size()-2));
    }
    private static void require(boolean value,String message){if(!value)throw new IllegalStateException(message);}
    private static void press(RENDEROBJ control) {
        require(!VIEW.inters().manager.hover(new Coo(control.body().cX(),control.body().cY()),true),"Own hover not consumed");
        require(!VIEW.inters().manager.click(MButt.LEFT),"Own click passed through");
    }
}
