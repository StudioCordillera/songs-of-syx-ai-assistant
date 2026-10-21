package syx.assistant.candidate;

import init.sprite.UI.UI;
import java.util.concurrent.atomic.AtomicLong;
import snake2d.CORE;
import snake2d.MButt;
import snake2d.SPRITE_RENDERER;
import snake2d.util.datatypes.COORDINATE;
import snake2d.util.gui.GuiSection;
import snake2d.util.gui.clickable.CLICKABLE;
import util.gui.misc.GTextR;
import view.interrupter.InterGuisection;
import view.main.VIEW;

/** Developer-only mod-owned surface adapter. No chat, game action, input setter or visibility receipt. */
public final class NativeGestureSurface extends InterGuisection {
    private final GestureReducer gesture=new GestureReducer();
    private final Object scene;
    private GestureReducer.Rect launcher=new GestureReducer.Rect(8,80,112,36);
    private GestureReducer.Rect panel=new GestureReducer.Rect(24,80,640,480);
    private boolean opened;
    private int generations;
    private final AtomicLong rendered=new AtomicLong();
    private String last="idle";

    public NativeGestureSurface(){
        super(VIEW.inters().manager);scene=VIEW.current();pin();persistantSet();rebuild();
    }
    private int vw(){return CORE.getGraphics().nativeWidth;}
    private int vh(){return CORE.getGraphics().nativeHeight;}
    private boolean available(){return isActivated() && !VIEW.hideUI() && VIEW.current()==scene;}
    private GestureReducer.Rect rectangle(){return opened?panel:launcher;}
    private void store(GestureReducer.Rect r){if(opened)panel=r;else launcher=r;}
    private static int unit(double n){return Math.max(1,(int)Math.floor(n));}

    private final class Handle extends CLICKABLE.ClickableAbs {
        private final GestureReducer.Target target;
        private final GTextR label;
        Handle(GestureReducer.Target target,String text,int w,int h){
            this.target=target;label=new GTextR(UI.FONT().S,text);body.setWidth(w).setHeight(h);
        }
        @Override protected void clickA(){
            COORDINATE p=CORE.getInput().getMouse().getCoo();
            // Own widget routing chose this handle. Copy engine-owned primitives immediately.
            beginOwned(target,p.x(),p.y(),System.nanoTime()/1_000_000.0);
        }
        @Override protected void render(SPRITE_RENDERER r,float ds,boolean active,boolean selected,boolean hovered){
            rendered.incrementAndGet();label.body().moveX1Y1(body);label.render(r,ds);
        }
    }
    private void rebuild(){
        store(rectangle().fit(vw(),vh()));GestureReducer.Rect r=rectangle();
        int w=unit(r.width),h=unit(r.height);
        GuiSection section=new GuiSection();
        if(!opened)section.add(new Handle(GestureReducer.Target.launcher,"AI review",w,h),0,0);
        else {
            section.add(new Handle(GestureReducer.Target.header,"Drag review panel",w,28),0,0);
            section.add(new GTextR(UI.FONT().S,"Developer surface; no chat or read receipts"),8,40);
            section.add(new Handle(GestureReducer.Target.resize,"+",Math.min(24,w),Math.min(24,h)),Math.max(0,w-24),Math.max(0,h-24));
        }
        section.body().setWidth(w).setHeight(h).moveX1Y1((int)Math.floor(r.x),(int)Math.floor(r.y));
        activate(section);generations++;
    }
    /** Own adapter seam for supplied-primitives fixture checks, not a gameplay or MCP entry point. */
    public boolean beginOwned(GestureReducer.Target target,double x,double y,double at){
        if(!available() || gesture.isCapturing())return false;
        if(opened?target!=GestureReducer.Target.header && target!=GestureReducer.Target.resize:target!=GestureReducer.Target.launcher)return false;
        // Refuse labels that do not correspond to an actual current own handle.
        GestureReducer.Rect r=rectangle();
        if(!Double.isFinite(x) || !Double.isFinite(y) || !Double.isFinite(at) || x<r.x || x>=r.x+r.width || y<r.y || y>=r.y+r.height)return false;
        if(target==GestureReducer.Target.header && !(x>=r.x && x<r.x+r.width && y>=r.y && y<r.y+28))return false;
        if(target==GestureReducer.Target.resize && !(x>=r.x+r.width-24 && x<r.x+r.width && y>=r.y+r.height-24 && y<r.y+r.height))return false;
        gesture.begin(target,x,y,at,r,vw(),vh());last="began";return true;
    }
    public String sampleOwned(double x,double y,double at,boolean held){
        GestureReducer.Result result=gesture.sample(x,y,at,held,available(),vw(),vh());last=result.status;
        if(result.rect!=null){
            GestureReducer.Rect before=rectangle();store(result.rect);
            if(before.width!=result.rect.width || before.height!=result.rect.height)rebuild();
            else if(current()!=null)current().body().moveX1Y1((int)Math.floor(result.rect.x),(int)Math.floor(result.rect.y));
        }
        if(result.status.equals("toggle")){opened=!opened;rebuild();}
        return last;
    }
    public void resetLayout(){gesture.cancel();launcher=new GestureReducer.Rect(8,80,112,36);panel=new GestureReducer.Rect(24,80,640,480);rebuild();last="reset";}
    public void closePanel(){gesture.cancel();opened=false;rebuild();last="closed";}
    @Override protected void deactivateAction(){gesture.cancel();last="cancelled";super.deactivateAction();}
    @Override protected boolean back(){return false;}
    @Override protected boolean otherClick(MButt button){return false;}
    @Override protected boolean update(float ds){
        if(gesture.isCapturing()){
            COORDINATE p=CORE.getInput().getMouse().getCoo();
            sampleOwned(p.x(),p.y(),System.nanoTime()/1_000_000.0,MButt.LEFT.isDown());
        }
        return true;
    }
    public boolean opened(){return opened;}
    public boolean capturing(){return gesture.isCapturing();}
    public int generations(){return generations;}
    public long renderCallbacks(){return rendered.get();}
    public GestureReducer.Rect layout(){return rectangle();}
    public String status(){return last;}
}
