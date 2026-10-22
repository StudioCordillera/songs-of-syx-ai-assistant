package syx.assistant;

import java.nio.file.*;
import java.util.*;
import game.GAME;
import game.time.TIME;
import snake2d.CORE;
import snake2d.MButt;
import snake2d.util.datatypes.Coo;
import snake2d.util.gui.clickable.CLICKABLE;
import syx.assistant.candidate.GestureReducer;
import util.gui.misc.GInput;
import view.main.VIEW;

/** TEST ONLY: owned overlay controls, real helper IPC, deterministic fake inference. */
public final class ChatBackgroundScenario {
    private static void require(boolean value,String why){if(!value)throw new IllegalStateException(why);}
    private static void press(CLICKABLE button){
        require(button!=null,"Missing own control");
        require(!VIEW.inters().manager.hover(new Coo(button.body().cX(),button.body().cY()),true),"Own hover escaped");
        require(!VIEW.inters().manager.click(MButt.LEFT),"Own click escaped");
    }
    private static void open(ChatPanel p,double at){
        var h=p.candidateHandle(GestureReducer.Target.launcher);
        require(h!=null&&p.beginGesture(GestureReducer.Target.launcher,h.body().cX(),h.body().cY(),at),"Own launcher begin");
        require(p.sampleGesture(h.body().cX(),h.body().cY(),at+1,false).equals("toggle"),"Own short launcher toggle");
    }
    public static void install(Path directory){
        VIEW.s().activate();GAME.SPEED.speedSet(1);
        int[] phase={0};long[] wait={0};long start=System.nanoTime();double[] seconds={0};String[] chat={null};
        GInput[] composer={null};List<Map<String,Object>> checks=new ArrayList<>();String draft="Keep next question draft while first answer arrives";
        GAME.addAfterUpdate(()->{
            try{
                if(System.nanoTime()-start>140_000_000_000L)throw new IllegalStateException("Layout background timeout");
                ChatPanel p=AssistantScript.currentChatPanel();if(p==null)return;
                var c=p.context();boolean opened=Boolean.TRUE.equals(c.get("panel_open")),running=Boolean.TRUE.equals(c.get("generating"));
                switch(phase[0]){
                case 0:
                    require(Boolean.TRUE.equals(c.get("candidate_layout")),"Expected own candidate overlay");
                    if(!Files.exists(directory.resolve("chat-ui.txt")))return;
                    open(p,0);phase[0]=1;break;
                case 1:
                    require(opened,"Panel failed to open");
                    if(c.get("chat_id")==null||Boolean.TRUE.equals(c.get("action_pending")))return;
                    require("simple".equals(c.get("interface"))&&c.get("runtime_session_id").equals(c.get("attached_session_id")),"Automatic session admission failed");
                    chat[0]=c.get("chat_id").toString();composer[0]=p.candidateComposer();
                    composer[0].text().clear().add("Fixture: original warehouse teaching grid with source caveats");
                    press(p.candidateButton("Send"));checks.add(StateCollector.object("phase","automatic_native_session","passed",true));phase[0]=2;break;
                case 2:{
                    if(!running)return;
                    composer[0].text().clear().add(draft);
                    press(p.candidateButton("Style"));press(p.candidateButton("Parchment"));press(p.candidateButton("Style"));
                    require(p.candidateTheme().name.equals("Parchment")&&!p.candidateAppearanceOpen()&&composer[0].text().toString().equals(draft),"Pending style change lost composer/state");
                    var h=p.candidateHandle(GestureReducer.Target.resize);double x=h.body().cX(),y=h.body().cY();
                    require(p.beginGesture(GestureReducer.Target.resize,x,y,100),"Begin pending own resize");
                    p.sampleGesture(x+40,y+20,101,true);p.sampleGesture(x+40,y+20,102,false);
                    require(p.candidateLayout().width==880&&p.candidateLayout().height==660,"Pending resize failed");
                    Files.writeString(directory.resolve("release-layout-partial"),"release\n");phase[0]=3;break;}
                case 3:
                    if(p.candidateTranscript().stream().noneMatch(t->t.contains("SIMULATED partial")))return;
                    require(opened&&running&&p.candidateComposer()==composer[0]&&composer[0].text().toString().equals(draft),"Real partial frame lost controls/draft");
                    require(p.candidateLayout().width==880&&p.candidateLayout().height==660,"Real partial frame reset geometry");
                    checks.add(StateCollector.object("phase","responsive_pending_draft_partial","passed",true));
                    seconds[0]=TIME.currentSecond();wait[0]=System.nanoTime();phase[0]=4;break;
                case 4:
                    if(System.nanoTime()-wait[0]<3_000_000_000L)return;
                    require(opened&&running&&TIME.currentSecond()>seconds[0],"Open pending progression failed");
                    checks.add(StateCollector.object("phase","open_pending","game_seconds_advanced",TIME.currentSecond()-seconds[0],"passed",true));
                    require(composer[0].text().toString().equals(draft),"Pending heartbeat lost draft");
                    press(p.candidateButton("Close"));seconds[0]=TIME.currentSecond();wait[0]=System.nanoTime();phase[0]=5;break;
                case 5:
                    if(System.nanoTime()-wait[0]<3_000_000_000L)return;
                    require(!opened&&running&&TIME.currentSecond()>seconds[0],"Closed pending progression failed");
                    checks.add(StateCollector.object("phase","closed_pending","game_seconds_advanced",TIME.currentSecond()-seconds[0],"passed",true));
                    Files.writeString(directory.resolve("release-simulated-answer"),"release\n");phase[0]=6;break;
                case 6:
                    if(running||!Files.exists(directory.resolve("simulated-reply-completed")))return;
                    require(!opened&&chat[0].equals(c.get("chat_id")),"Closed completion changed chat");
                    checks.add(StateCollector.object("phase","closed_completed","passed",true));open(p,200);phase[0]=7;break;
                case 7:
                    require(opened&&chat[0].equals(c.get("chat_id")),"Reopen changed chat");
                    if(Boolean.TRUE.equals(c.get("action_pending")))return;
                    require(p.candidateTranscript().stream().anyMatch(t->t.contains("SIMULATED FIXTURE ANSWER")),"Completed plain answer missing from panel model");
                    require(composer[0]==p.candidateComposer()&&composer[0].text().toString().equals(draft),"Reopen lost next draft");
                    checks.add(StateCollector.object("phase","reopened_same_chat_reply","passed",true));
                    composer[0].text().clear().add("Fixture: cancel the second reply");press(p.candidateButton("Send"));phase[0]=8;break;
                case 8:
                    if(!running||!Files.exists(directory.resolve("second-provider-started")))return;
                    press(p.candidateButton("Stop"));phase[0]=9;break;
                case 9:
                    if(running||Boolean.TRUE.equals(c.get("action_pending"))||!Files.exists(directory.resolve("second-provider-closed")))return;
                    checks.add(StateCollector.object("phase","stop_second_turn","passed",true));
                    Files.writeString(directory.resolve("layout-background-native.json"),JsonWriter.encode(StateCollector.object("passed",true,"checks",checks,"reopened_same_chat",true,"native_width",CORE.getGraphics().nativeWidth,"native_height",CORE.getGraphics().nativeHeight,"handle_render_callbacks",p.candidateDraws(),"supplied_gesture_primitives",true)));
                    phase[0]=10;break;
                case 10:
                    if(!Files.exists(directory.resolve("verifier.done")))return;
                    Files.writeString(directory.resolve("layout-background-clean-exit.json"),"{\"passed\":true,\"verified_phases\":7}");CORE.annihilate();phase[0]=11;break;
                }
            }catch(Exception error){
                System.err.println("SMOKE_FIXTURE_FAILURE: "+error);
                try{Files.writeString(directory.resolve("layout-background-fixture-failure.json"),error.getClass().getSimpleName());}catch(Exception ignored){}
                CORE.annihilate(error);
            }
        });
    }
}
