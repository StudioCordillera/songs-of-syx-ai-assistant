import java.nio.file.*;
import java.util.*;
import game.GAME;
import snake2d.CORE;
import syx.assistant.JsonWriter;
import syx.assistant.candidate.GestureReducer;
import syx.assistant.candidate.NativeGestureSurface;
import static syx.assistant.StateCollector.object;

/** TEST ONLY: native own surface with supplied gesture primitives, no engine input injection. */
public final class StockpileScenario {
    private static void require(boolean yes,String message){if(!yes)throw new IllegalStateException(message);}
    private static void bounds(NativeGestureSurface panel){
        var r=panel.layout();var b=panel.current().body();
        require(b.x1()==r.x && b.y1()==r.y && b.width()==r.width && b.height()==r.height,"Native body and detached rectangle differ");
        require(b.x1()>=0 && b.y1()>=0 && b.x2()<=CORE.getGraphics().nativeWidth && b.y2()<=CORE.getGraphics().nativeHeight,"Own body escaped internal bounds");
    }
    public static void install(Path directory){
        view.main.VIEW.s().activate();GAME.SPEED.speedSet(0);
        NativeGestureSurface panel=new NativeGestureSurface();
        long began=System.nanoTime();boolean[] written={false},finished={false};long[] afterDraw={0},afterOpen={0},openCallbacks={0};
        GAME.addAfterUpdate(()->{
            if(finished[0])return;
            try{
                if(System.nanoTime()-began>100_000_000_000L)throw new IllegalStateException("Gesture native timeout");
                if(written[0]){
                    if(Files.exists(directory.resolve("verifier.done"))){
                        panel.deactivate();Files.writeString(directory.resolve("gesture-surface-clean-exit.json"),JsonWriter.encode(object("passed",true)));
                        finished[0]=true;CORE.annihilate();
                    }return;
                }
                if(System.nanoTime()-began<5_000_000_000L || panel.renderCallbacks()<3)return;
                if(afterDraw[0]>0){
                    if(panel.renderCallbacks()-afterDraw[0]<3)return;
                    bounds(panel);
                    // VIEW.hide is one-way through the reviewed public route; test it last.
                    require(panel.beginOwned(GestureReducer.Target.launcher,10,85,2000),"Begin hidden cancellation");
                    view.main.VIEW.hide();require(panel.sampleOwned(10,85,2001,true).equals("cancelled") && !panel.capturing(),"Hidden UI cancellation");
                    Files.writeString(directory.resolve("stockpile-fixture.json"),JsonWriter.encode(object("passed",true,
                        "native_width",CORE.getGraphics().nativeWidth,"native_height",CORE.getGraphics().nativeHeight,
                        "resized_panel_handle_callbacks",openCallbacks[0],"render_callbacks",panel.renderCallbacks(),"post_rebuild_callbacks",panel.renderCallbacks()-afterDraw[0],
                        "own_section_generations",panel.generations(),"checks",List.of("short_launcher_toggle","immediate_header_drag","resize_rebuild","reject_wrong_surface_and_content",
                        "hidden_ui_cancel","deactivation_cancel","scene_change_cancel","reset_layout","close_cancels_and_reopens_launcher","native_body_bounds","held_launcher_drag_clamps_without_opening","stationary_launcher_hold_suppresses_open"))));written[0]=true;return;
                }
                if(afterOpen[0]==0){
                require(panel.beginOwned(GestureReducer.Target.launcher,10,85,100),"Begin launcher");
                require(panel.sampleOwned(10,85,150,false).equals("toggle") && panel.opened(),"Short click toggle");bounds(panel);
                require(!panel.beginOwned(GestureReducer.Target.launcher,30,85,200),"Reject wrong surface");
                require(!panel.beginOwned(GestureReducer.Target.header,40,200,200),"Reject transcript header label");
                require(!panel.beginOwned(GestureReducer.Target.resize,40,200,200),"Reject transcript resize label");
                require(panel.beginOwned(GestureReducer.Target.header,30,85,200),"Begin header");
                require(panel.sampleOwned(40,95,201,true).equals("dragging"),"Immediate header drag");
                require(panel.sampleOwned(50,115,202,false).equals("dropped"),"Header drop");bounds(panel);
                require(panel.layout().x==44 && panel.layout().y==110,"Header original rectangle deltas");
                var r=panel.layout();double x=r.x+r.width-5,y=r.y+r.height-5;int old=panel.generations();
                require(panel.beginOwned(GestureReducer.Target.resize,x,y,300),"Begin resize");
                require(panel.sampleOwned(x+100,y+60,301,true).equals("dragging"),"Resize");
                require(panel.sampleOwned(x+100,y+60,302,false).equals("dropped"),"Resize drop");bounds(panel);
                require(panel.generations()>old && panel.layout().width==740 && panel.layout().height==540,"Resize section rebuild");
                afterOpen[0]=panel.renderCallbacks();return;
                }
                if(panel.renderCallbacks()-afterOpen[0]<6)return;
                openCallbacks[0]=panel.renderCallbacks()-afterOpen[0];bounds(panel);
                require(panel.opened() && panel.layout().width==740 && panel.layout().height==540,"Resized native panel retained across draws");
                require(panel.beginOwned(GestureReducer.Target.header,50,115,500),"Begin deactivate cancellation");
                panel.close();require(!panel.capturing() && !panel.isActivated(),"Deactivation cancels");panel.resetLayout();
                require(panel.beginOwned(GestureReducer.Target.header,30,85,600),"Begin scene cancellation");
                view.main.VIEW.world().activate();require(panel.sampleOwned(30,85,601,true).equals("cancelled"),"Scene cancellation");view.main.VIEW.s().activate();
                panel.resetLayout();bounds(panel);require(panel.layout().width==640 && panel.layout().height==480,"Reset dimensions");
                require(panel.beginOwned(GestureReducer.Target.header,30,85,700),"Begin close cancellation");
                panel.closePanel();require(!panel.capturing() && !panel.opened(),"Closing cancels");bounds(panel);
                require(panel.beginOwned(GestureReducer.Target.launcher,10,85,800),"Begin held launcher");
                require(panel.sampleOwned(10,85,1150,true).equals("armed"),"Launcher hold arms");
                int edgeX=CORE.getGraphics().nativeWidth,edgeY=CORE.getGraphics().nativeHeight;
                require(panel.sampleOwned(edgeX,edgeY,1160,true).equals("dragging"),"Held launcher drag");bounds(panel);
                require(panel.sampleOwned(edgeX,edgeY,1170,false).equals("dropped") && !panel.opened(),"Launcher drop does not open");
                require(panel.layout().x==edgeX-112 && panel.layout().y==edgeY-36,"Launcher edge clamp");panel.resetLayout();
                require(panel.beginOwned(GestureReducer.Target.launcher,10,85,1200),"Begin stationary hold");
                require(panel.sampleOwned(10,85,1550,true).equals("armed"),"Stationary hold arms");
                require(panel.sampleOwned(10,85,1560,false).equals("released") && !panel.opened(),"Stationary engaged hold does not open");
                bounds(panel);afterDraw[0]=panel.renderCallbacks();
            }catch(Exception failure){finished[0]=true;System.err.println("SMOKE_FIXTURE_FAILURE: "+failure);CORE.annihilate(failure);}
        });
    }
}
