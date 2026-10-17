package syx.assistant;

import snake2d.MButt;
import snake2d.Renderer;
import snake2d.util.datatypes.COORDINATE;
import util.gui.misc.GBox;
import util.gui.misc.GButt;
import view.interrupter.Interrupter;
import view.main.VIEW;

/** Player-only local consent control, kept outside the assistant's clickable area. */
public final class ControlPanel extends Interrupter {
    private final GButt.Panel allow, stop;
    public ControlPanel(ControlPolicy policy) {
        super(true, true, false);
        allow = new GButt.Panel("Allow AI control (5 min)") {
            @Override protected void clickA() { policy.enableFromPlayer(System.currentTimeMillis()); }
            @Override protected void renAction() { selectedSet(policy.enabled(System.currentTimeMillis())); }
        };
        stop = new GButt.Panel("Stop") { @Override protected void clickA() { policy.stop(); } };
        allow.body().moveX1(8).moveY1(64); stop.body().moveX1(allow.body().x2()+8).moveY1(64);
        policy.blockControls(8,64,stop.body().x2()+8,stop.body().y2()+8);
        show(VIEW.s().uiManager);
    }
    protected boolean hover(COORDINATE c, boolean moved) { boolean a=allow.hover(c), b=stop.hover(c); return a||b; }
    protected void mouseClick(MButt b) { if (b==MButt.LEFT) { allow.click(); stop.click(); } }
    protected void hoverTimer(GBox text) { text.text("Allow AI input for five minutes. Any physical key, click or scroll stops control. Screenshots and selected game data may be sent to your AI provider."); }
    protected boolean render(Renderer r,float ds) { snake2d.util.color.COLOR.BLACK.render(r, 8, stop.body().x2()+8, 64, stop.body().y2()+8); allow.render(r,ds); stop.render(r,ds); return true; }
    protected boolean update(float ds) { return true; }
}
