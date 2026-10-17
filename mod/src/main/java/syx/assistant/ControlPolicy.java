package syx.assistant;

import java.util.UUID;

/** Pure control gate, tested without a game/graphics context. */
public final class ControlPolicy {
    public final String session;
    private String grant = "";
    private long expires;
    private String frame = "";
    private long observed;
    private int width, height;
    private int bx1=8, by1=64, bx2=340, by2=110;
    public synchronized void blockControls(int x1,int y1,int x2,int y2) { bx1=x1;by1=y1;bx2=x2;by2=y2; }
    public ControlPolicy(String session) { this.session = session; }
    public synchronized void enableFromPlayer(long now) { grant = UUID.randomUUID().toString(); expires = now+300_000; }
    public synchronized void stop() { grant = ""; expires = 0; }
    public synchronized boolean enabled(long now) { return !grant.isEmpty() && now < expires; }
    public synchronized String grant(long now) { return enabled(now) ? grant : ""; }
    public synchronized void observe(String id, int w, int h, long now) { frame=id; width=w; height=h; observed=now; }
    public synchronized void validate(String requestedSession, String requestedGrant, String requestedFrame, long now) {
        if (!session.equals(requestedSession)) throw new IllegalArgumentException("Wrong game session");
        if (!enabled(now) || !grant.equals(requestedGrant)) throw new IllegalArgumentException("Player has not enabled control, or the grant expired");
        if (!frame.equals(requestedFrame) || frame.isEmpty() || now-observed>5000 || now<observed)
            throw new IllegalArgumentException("Observe the game again; frame is stale");
    }
    public synchronized void point(int x, int y) {
        if (x<0 || y<0 || x>=width || y>=height) throw new IllegalArgumentException("Point outside game viewport");
        if (x>=bx1 && x<bx2 && y>=by1 && y<by2) throw new IllegalArgumentException("Assistant may not operate its own permission controls");
    }
}
