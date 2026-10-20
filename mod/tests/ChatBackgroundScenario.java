package syx.assistant;

import java.nio.file.*;
import java.util.*;
import game.GAME;
import game.time.TIME;
import snake2d.CORE;
import snake2d.MButt;
import snake2d.util.datatypes.Coo;
import snake2d.util.gui.renderable.RENDEROBJ;
import util.gui.misc.GInput;
import view.main.VIEW;

/** TEST ONLY: copied-save speed and own widgets; delayed fake inference, never a paid request. */
public final class ChatBackgroundScenario {
    private static void require(boolean value,String message) {if(!value)throw new IllegalStateException(message);}
    private static void press(RENDEROBJ row) {
        require(!VIEW.inters().manager.hover(new Coo(row.body().cX(),row.body().cY()),true),"Own hover escaped");
        require(!VIEW.inters().manager.click(MButt.LEFT),"Own click escaped");
    }
    public static void install(Path directory) {
        VIEW.s().activate();GAME.SPEED.speedSet(1);
        int[] phase={0};long[] wait={0};long start=System.nanoTime();double[] seconds={0};String[] cid={null};
        List<Map<String,Object>> checks=new ArrayList<>();
        GAME.addAfterUpdate(()->{
            try {
                if(System.nanoTime()-start>100_000_000_000L)throw new IllegalStateException("Background chat fixture timeout");
                ChatPanel panel=AssistantScript.currentChatPanel();if(panel==null)return;
                Map<String,Object> c=panel.context();boolean open=Boolean.TRUE.equals(c.get("panel_open"));
                boolean generating=Boolean.TRUE.equals(c.get("generating"));
                switch(phase[0]) {
                    case 0:
                        if(!Files.exists(directory.resolve("chat-ui.txt")))return;
                        press(panel.section().elements().get(0));phase[0]=1;break;
                    case 1:
                        require(open,"Panel failed to open");press(panel.section().elements().get(1));phase[0]=2;break;
                    case 2:
                        if(c.get("chat_id")==null)return;
                        cid[0]=c.get("chat_id").toString();require("simple".equals(c.get("interface")),"Expected simple player");
                        GInput input=null;for(RENDEROBJ row:panel.section().elements())if(row instanceof GInput)input=(GInput)row;
                        require(input!=null,"No composer");input.text().clear().add("Background fixture: simulated delayed answer");
                        press(panel.section().elements().get(panel.section().elements().size()-2));phase[0]=3;break;
                    case 3:
                        if(!generating)return;
                        seconds[0]=TIME.currentSecond();wait[0]=System.nanoTime();phase[0]=4;break;
                    case 4:
                        if(System.nanoTime()-wait[0]<3_000_000_000L)return;
                        require(open&&generating,"Expected open pending chat");
                        require(TIME.currentSecond()>seconds[0],"Simulation stopped with open chat");
                        checks.add(StateCollector.object("phase","open_pending","game_seconds_advanced",TIME.currentSecond()-seconds[0],"passed",true));
                        press(panel.section().elements().get(0));seconds[0]=TIME.currentSecond();wait[0]=System.nanoTime();phase[0]=5;break;
                    case 5:
                        if(System.nanoTime()-wait[0]<3_000_000_000L)return;
                        require(!open&&generating,"Closing panel cancelled pending reply");
                        require(TIME.currentSecond()>seconds[0],"Simulation stopped with closed chat");
                        checks.add(StateCollector.object("phase","closed_pending","game_seconds_advanced",TIME.currentSecond()-seconds[0],"passed",true));
                        Files.writeString(directory.resolve("release-simulated-answer"),"release\n");phase[0]=6;break;
                    case 6:
                        if(generating)return;
                        require(!open&&cid[0].equals(c.get("chat_id")),"Closed completion changed chat");
                        if(!Files.exists(directory.resolve("simulated-reply-completed")))return;
                        checks.add(StateCollector.object("phase","closed_completed","passed",true));
                        press(panel.section().elements().get(0));phase[0]=7;break;
                    case 7:
                        require(open&&cid[0].equals(c.get("chat_id")),"Reopen lost completed chat");
                        Files.writeString(directory.resolve("background-native.json"),JsonWriter.encode(StateCollector.object("passed",true,"checks",checks,"reopened_same_chat",true)));
                        phase[0]=8;break;
                    case 8:
                        if(!Files.exists(directory.resolve("verifier.done")))return;
                        Files.writeString(directory.resolve("chat-background-clean-exit.json"),"{\"passed\":true,\"verified_phases\":3}");
                        CORE.annihilate();phase[0]=9;break;
                }
            } catch(Exception e) {
                System.err.println("SMOKE_FIXTURE_FAILURE: "+e);
                try {Files.writeString(directory.resolve("chat-background-fixture-failure.json"),e.getClass().getSimpleName());}catch(Exception ignored){}
                CORE.annihilate(e);
            }
        });
    }
}
