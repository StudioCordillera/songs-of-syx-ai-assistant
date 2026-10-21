package syx.assistant.candidate;

/** Detached, game-independent gesture policy. No input polling, focus or game visibility claim. */
public final class GestureReducer {
    public static final double HOLD_MS=350, SLOP=6, MAX_MS=5000;
    public enum Target {launcher,header,chrome,resize}
    public static final class Rect {
        public final double x,y,width,height;
        public Rect(double x,double y,double width,double height){
            finite(x);finite(y);positive(width);positive(height);
            this.x=x;this.y=y;this.width=width;this.height=height;
        }
        public Rect fit(double vw,double vh){
            positive(vw);positive(vh);double w=Math.min(width,vw),h=Math.min(height,vh);
            return new Rect(clamp(x,0,vw-w),clamp(y,0,vh-h),w,h);
        }
    }
    public static final class Result {
        public final String status;public final Rect rect;
        private Result(String status,Rect rect){this.status=status;this.rect=rect;}
    }
    private static final class Capture {
        final Target target;final double x,y,at,vw,vh;final Rect rect;
        double last;boolean moved,drag,early,engaged;
        Capture(Target target,double x,double y,double at,Rect rect,double vw,double vh){
            this.target=target;this.x=x;this.y=y;this.at=at;this.last=at;this.rect=rect;this.vw=vw;this.vh=vh;
        }
    }
    private Capture capture;
    private static void finite(double v){if(!Double.isFinite(v))throw new IllegalArgumentException("Finite value required");}
    private static void positive(double v){finite(v);if(v<=0)throw new IllegalArgumentException("Positive dimension required");}
    private static double clamp(double v,double lo,double hi){return Math.max(lo,Math.min(v,hi));}
    public boolean isCapturing(){return capture!=null;}
    public Rect begin(Target target,double x,double y,double at,Rect rect,double vw,double vh){
        if(capture!=null)throw new IllegalArgumentException("Existing capture");
        if(target==null || rect==null)throw new IllegalArgumentException("Own surface/layout required");
        finite(x);finite(y);finite(at);positive(vw);positive(vh);Rect bounded=rect.fit(vw,vh);
        if(x<bounded.x || x>bounded.x+bounded.width || y<bounded.y || y>bounded.y+bounded.height)
            throw new IllegalArgumentException("Press outside own bounds");
        capture=new Capture(target,x,y,at,bounded,vw,vh);return bounded;
    }
    public Result cancel(){capture=null;return new Result("cancelled",null);}
    public Result sample(double x,double y,double at,boolean held,boolean surfaceActive,double vw,double vh){
        finite(x);finite(y);finite(at);
        if(capture==null)return new Result("idle",null);
        Capture c=capture;
        if(at<c.last)throw new IllegalArgumentException("Backwards time");
        // Validate dimensions before changing any capture state.
        positive(vw);positive(vh);c.last=at;
        if(!surfaceActive || vw!=c.vw || vh!=c.vh || at-c.at>=MAX_MS || x<0 || x>vw || y<0 || y>vh)return cancel();
        double dx=x-c.x,dy=y-c.y,distance=Math.hypot(dx,dy),elapsed=at-c.at;
        c.moved|=distance>SLOP;
        if(c.target==Target.launcher){
            if(!c.engaged && elapsed<HOLD_MS && distance>SLOP)c.early=true;
            if(elapsed>=HOLD_MS && !c.early)c.engaged=true;
            if(held && c.engaged && c.moved)c.drag=true;
        }else if(held && distance>0)c.drag=true;
        Rect rect=c.rect;
        if(c.drag){
            if(c.target==Target.resize){
                double w=Math.max(Math.min(480,vw-rect.x),Math.min(vw-rect.x,rect.width+dx));
                double h=Math.max(Math.min(320,vh-rect.y),Math.min(vh-rect.y,rect.height+dy));
                rect=new Rect(rect.x,rect.y,w,h).fit(vw,vh);
            }else rect=new Rect(rect.x+dx,rect.y+dy,rect.width,rect.height).fit(vw,vh);
        }
        if(held)return new Result(c.drag?"dragging":c.early?"blocked":c.engaged?"armed":"holding",rect);
        capture=null;
        if(c.drag)return new Result("dropped",rect);
        return new Result(c.target==Target.launcher && !c.moved && !c.engaged && !c.early?"toggle":"released",rect);
    }
}
