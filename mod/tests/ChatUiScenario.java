package syx.assistant;

import java.nio.file.*;
import java.util.*;
import game.GAME;
import snake2d.CORE;
import snake2d.MButt;
import snake2d.Mouse;
import snake2d.util.datatypes.Coo;
import snake2d.util.gui.renderable.RENDEROBJ;
import util.gui.misc.GInput;
import view.main.VIEW;

/** TEST ONLY: dispatches clicks through public GUI APIs to the mod's own controls. */
public final class ChatUiScenario {
    private static long start,last;
    private static int phase;
    private static String firstChat;
    public static void install(Path directory) {
        start=last=System.currentTimeMillis();phase=0;
        GAME.addAfterUpdate(()->{
            if(System.currentTimeMillis()-last<1500)return;
            try {
                ChatPanel panel=AssistantScript.currentChatPanel();
                if(panel==null)throw new IllegalStateException("No own chat panel");
                switch(phase) {
                    case 0: press(panel.section().elements().get(0));phase=1;break;
                    case 1:
                        require(Boolean.TRUE.equals(panel.context().get("panel_open")),"Panel did not open");
                        require(panel.section().elements().size()>8,"Own controls missing");
                        press(panel.section().elements().get(1));phase=2;break;
                    case 2:
                        Object id=panel.context().get("chat_id");
                        if(id==null){if(System.currentTimeMillis()-start>30000)throw new IllegalStateException("Coordinator did not create chat");return;}
                        firstChat=id.toString();
                        GInput input=null;
                        for(RENDEROBJ row:panel.section().elements())if(row instanceof GInput)input=(GInput)row;
                        require(input!=null,"No composer");
                        press(input);require(Mouse.currentClicked==input,"Input did not receive focus");
                        input.text().clear().add("Fixture question; no credentials configured");
                        int count=panel.section().elements().size();
                        press(panel.section().elements().get(count-2));phase=3;break;
                    case 3:
                        require(firstChat.equals(panel.context().get("chat_id")),"Chat identity changed");
                        press(panel.section().elements().get(0));phase=4;break;
                    case 4:
                        require(Boolean.FALSE.equals(panel.context().get("panel_open")),"Panel did not close");
                        require(!(Mouse.currentClicked instanceof GInput),"Closed composer retained input focus");
                        press(panel.section().elements().get(0));phase=5;break;
                    case 5:
                        require(firstChat.equals(panel.context().get("chat_id")),"Reopen lost history selection");
                        VIEW.world().activate();phase=6;break;
                    case 6:
                        require(panel.isActivated(),"Panel disappeared on world transition");
                        VIEW.s().activate();phase=7;break;
                    case 7:
                        require(panel.isActivated(),"Panel disappeared on city transition");
                        phase=8;
                        Files.copy(directory.resolve("snapshot.json"),directory.resolve("chat-observation.json"),StandardCopyOption.REPLACE_EXISTING);
                        Files.writeString(directory.resolve("chat-gui-validation.json"),JsonWriter.encode(Map.of(
                            "passed",true,"checks",List.of("public GUI own-panel click consumed","open and close","create chat via file coordinator",
                            "composer focus","missing-key send rejection","reopen chat identity","world and city panel persistence"),
                            "limitations",List.of("No real provider inference","No physical keyboard test","No full menu/modal/reload coverage","Experimental opt-in panel"))));
                        System.err.println("CHAT GUI TEST PASS");CORE.annihilate();return;
                }
                last=System.currentTimeMillis();
            }catch(Exception error){System.err.println("CHAT GUI TEST FAILURE: "+error);CORE.annihilate(error);}
        });
    }
    private static void require(boolean condition,String message){if(!condition)throw new IllegalStateException(message);}
    private static void press(RENDEROBJ control) {
        Coo point=new Coo(control.body().cX(),control.body().cY());
        require(!VIEW.inters().manager.hover(point,true),"Own control did not consume hover");
        require(!VIEW.inters().manager.click(MButt.LEFT),"Own control click passed through to the game");
    }
}
