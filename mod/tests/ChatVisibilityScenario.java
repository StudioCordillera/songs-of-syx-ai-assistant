package syx.assistant;

import game.GAME;
import init.sprite.UI.UI;
import snake2d.CORE;
import snake2d.MButt;
import snake2d.Renderer;
import snake2d.SPRITE_RENDERER;
import snake2d.util.datatypes.COORDINATE;
import snake2d.util.gui.GuiSection;
import snake2d.util.gui.renderable.RENDEROBJ;
import util.gui.misc.GBox;
import util.gui.misc.GTextR;
import view.interrupter.InterGuisection;
import view.main.VIEW;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.atomic.AtomicLong;

/** TEST ONLY: own render callbacks/public UI getters, no pixels/input/provider/save writes. */
public final class ChatVisibilityScenario {
    private static final class Label extends RENDEROBJ.RenderImp {
        final GTextR text;final AtomicLong counter;
        Label(String text,AtomicLong counter){super(220,28);this.text=new GTextR(UI.FONT().S,text);this.counter=counter;}
        @Override public void render(SPRITE_RENDERER r,float ds) {
            counter.incrementAndGet();text.body().moveX1Y1(body());text.render(r,ds);
        }
    }
    private static final class ProbePanel extends InterGuisection {
        final AtomicLong tooltips=new AtomicLong(),rows=new AtomicLong(),pairedEmpty=new AtomicLong();
        final Label tooltip=new Label("Fixture tooltip marker",tooltips),row=new Label("Fixture reply marker",rows);
        volatile boolean fillTooltip=true;
        private long lastTooltip;
        ProbePanel(){
            super(VIEW.inters().manager);pin();persistantSet();
            GuiSection content=new GuiSection();content.add(row,40,40);content.body().setWidth(840).setHeight(700);activate(content);
        }
        @Override protected boolean hover(COORDINATE p,boolean moved){return true;}
        @Override protected void hoverTimer(GBox box){if(fillTooltip){box.clear();box.add(tooltip);}}
        @Override protected void mouseClick(MButt b){}
        @Override protected boolean otherClick(MButt b){return false;}
        @Override protected boolean update(float ds){return true;}
        @Override protected boolean render(Renderer r,float ds){
            long now=tooltips.get();
            if(fillTooltip&&now>lastTooltip&&VIEW.inters().mouseMessage.get().emptyIs())pairedEmpty.incrementAndGet();
            lastTooltip=now;return super.render(r,ds);
        }
    }
    private static void write(Path directory,String phase,Map<String,Object> values)throws Exception {
        Map<String,Object> body=new LinkedHashMap<>(values);body.put("phase",phase);body.put("passed",true);
        Path temporary=directory.resolve("visibility-phase.tmp");Files.writeString(temporary,JsonWriter.encode(body));
        Files.move(temporary,directory.resolve("visibility-phase.json"),StandardCopyOption.REPLACE_EXISTING,StandardCopyOption.ATOMIC_MOVE);
    }
    public static void install(Path directory) {
        VIEW.s().activate();GAME.SPEED.speedSet(0);
        ProbePanel panel=new ProbePanel();AtomicLong popupDraws=new AtomicLong();
        GuiSection popup=new GuiSection();popup.add(new Label("Fixture popup marker",popupDraws),0,0);
        final long began=System.nanoTime();final int[] phase={0},stable={0},updates={0};
        final long[] previousRows={0},previousPopup={0},hiddenAt={0},hiddenRows={0},lastSample={0};
        GAME.addAfterUpdate(()->{
            try {
                if(System.nanoTime()-began>100_000_000_000L)throw new IllegalStateException("Visibility probe timeout");
                updates[0]++;
                if(phase[0]==0) {
                    if(panel.pairedEmpty.get()<3||panel.rows.get()<3)return;
                    write(directory,"tooltip_empty_after_render",StateCollector.object("tooltip_draw_callbacks",panel.tooltips.get(),"reply_draw_callbacks",panel.rows.get(),"paired_empty_public_box_callbacks",panel.pairedEmpty.get(),"panel_activated",panel.isActivated()));
                    phase[0]=1;
                } else if(phase[0]==1) {
                    if(!Files.exists(directory.resolve("tooltip_empty_after_render.done")))return;
                    panel.fillTooltip=false;VIEW.inters().popup.show(popup,null);
                    panel.row.body().moveC(popup.body().cX(),popup.body().cY());
                    previousRows[0]=panel.rows.get();previousPopup[0]=popupDraws.get();phase[0]=2;
                } else if(phase[0]==2) {
                    if(panel.rows.get()-previousRows[0]<3||popupDraws.get()-previousPopup[0]<3)return;
                    boolean overlap=panel.row.body().x1()<popup.body().x2()&&panel.row.body().x2()>popup.body().x1()&&panel.row.body().y1()<popup.body().y2()&&panel.row.body().y2()>popup.body().y1();
                    if(!VIEW.inters().popup.showing()||!overlap)throw new IllegalStateException("Expected public popup overlap");
                    write(directory,"popup_and_reply_callbacks",StateCollector.object("popup_draw_callbacks",popupDraws.get()-previousPopup[0],"reply_draw_callbacks",panel.rows.get()-previousRows[0],"public_popup_showing",true,"own_widget_bounds_overlap",overlap,"panel_activated",panel.isActivated()));phase[0]=3;
                } else if(phase[0]==3) {
                    if(!Files.exists(directory.resolve("popup_and_reply_callbacks.done")))return;
                    VIEW.inters().popup.close();VIEW.hide();hiddenAt[0]=System.nanoTime();hiddenRows[0]=panel.rows.get();lastSample[0]=hiddenAt[0];phase[0]=4;
                } else if(phase[0]==4) {
                    long now=System.nanoTime();if(now-lastSample[0]<200_000_000L)return;lastSample[0]=now;
                    long rows=panel.rows.get();if(rows==hiddenRows[0])stable[0]++;else {stable[0]=0;hiddenRows[0]=rows;}
                    if(stable[0]<5)return;
                    if(!VIEW.hideUI()||!panel.isActivated())throw new IllegalStateException("Expected active panel with hidden global UI");
                    write(directory,"hidden_active_without_callbacks",StateCollector.object("ui_hidden",true,"panel_activated",true,"stable_reply_callback_samples",stable[0],"updates_observed",updates[0],"hidden_elapsed_ms",(now-hiddenAt[0])/1_000_000L));phase[0]=5;
                } else if(phase[0]==5) {
                    if(!Files.exists(directory.resolve("verifier.done")))return;
                    Files.writeString(directory.resolve("chat-visibility-clean-exit.json"),"{\"passed\":true,\"verified_phases\":3}");phase[0]=6;CORE.annihilate();
                }
            } catch(Exception error) {
                System.err.println("SMOKE_FIXTURE_FAILURE: "+error);
                try{Files.writeString(directory.resolve("chat-visibility-fixture-failure.json"),error.toString());}catch(Exception ignored){}
                CORE.annihilate(error);
            }
        });
    }
}
