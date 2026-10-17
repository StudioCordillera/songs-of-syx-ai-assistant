package syx.assistant;

import snake2d.CORE;
import snake2d.SyxAssistantDriver;
import view.main.VIEW;
import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.net.URLDecoder;
import java.time.Instant;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicReference;
import static syx.assistant.StateCollector.object;

/** Bounded local mailbox: file I/O off-thread, input on game/GL threads. */
public final class ControlBridge {
    final ControlPolicy policy;
    private final Path dir;
    private final ScheduledExecutorService io;
    private final AtomicReference<Map<String,String>> incoming = new AtomicReference<>();
    private final SyxAssistantDriver driver;
    private Map<String,String> afterAction;
    private long settleUntil;
    private boolean stopped;
    ControlBridge(String session, Path stateDir, ScheduledExecutorService io, Runnable onDispose) {
        this.policy=new ControlPolicy(session); this.dir=stateDir.resolve("control"); this.io=io;
        try { Files.createDirectories(dir); } catch(Exception e) { throw new IllegalStateException(e); }
        driver=new SyxAssistantDriver(policy::stop, onDispose);
        new ControlPanel(policy);
        io.scheduleWithFixedDelay(this::receive,0,50,TimeUnit.MILLISECONDS);
    }
    private void receive() {
        if (stopped || incoming.get()!=null) return;
        try (DirectoryStream<Path> paths=Files.newDirectoryStream(dir,"*.req")) {
            for (Path p: paths) {
                String name=p.getFileName().toString();
                if (!name.matches("[a-f0-9-]{36}\\.req") || Files.isSymbolicLink(p)) continue;
                if (Files.size(p)>32768) { Files.deleteIfExists(p); continue; }
                String id=name.substring(0,36);
                if (Files.exists(dir.resolve(id+".json"))) { Files.deleteIfExists(p); continue; }
                Map<String,String> request=new HashMap<>();
                for(String line: Files.readAllLines(p,StandardCharsets.UTF_8)) {
                    int at=line.indexOf('=');
                    if(at>0) request.put(line.substring(0,at),URLDecoder.decode(line.substring(at+1),StandardCharsets.UTF_8));
                }
                request.put("id",id);
                // Persist claim BEFORE queueing: a crash cannot replay an uncertain UI action.
                if (Files.exists(dir.resolve(id+".claimed"))) {
                    write(id,object("ok",false,"error","Action outcome uncertain after restart; re-observe; do not replay"));
                    Files.deleteIfExists(p); continue;
                }
                Files.move(p,dir.resolve(id+".claimed"),StandardCopyOption.ATOMIC_MOVE);
                incoming.set(request); break;
            }
        } catch(Exception e) { System.err.println("Syx assistant control mailbox: "+e); }
    }
    void update() {
        if (stopped) return;
        if (!driver.focused() || !VIEW.s().isActive()) policy.stop();
        long now=System.currentTimeMillis();
        if(afterAction!=null) {
            if(now<settleUntil) return;
            Map<String,String> done=afterAction; afterAction=null;
            try { Map<String,Object> result=observe(done.get("id")); result.put("action_dispatched",true); reply(done,result); }
            catch(Exception e) { reply(done,object("ok",false,"action_dispatched",true,"error","Action was dispatched, but observation failed: "+e.getMessage())); }
            return;
        }
        Map<String,String> r=incoming.getAndSet(null);
        if(r==null) return;
        try {
            long deadline=Long.parseLong(r.getOrDefault("deadline","0"));
            if(now>deadline || deadline-now>30_000) throw new IllegalArgumentException("Expired request");
            String op=r.getOrDefault("operation","");
            if(op.equals("stop")) { policy.stop(); reply(r,status()); return; }
            if(op.equals("status")) { reply(r,status()); return; }
            if(!policy.session.equals(r.get("session_id"))) throw new IllegalArgumentException("Wrong game session");
            if(op.equals("observe")) { reply(r,observe(r.get("id"))); return; }
            if(op.equals("raw")) {
                Object data=new RawStateReader().execute(JsonReader.decode(r.getOrDefault("value","[]")));
                reply(r,object("ok",true,"session_id",policy.session,"tick",game.GAME.updateI(),
                    "game_version",game.VERSION.VERSION_STRING,"captured_at",Instant.now().toString(),"result",data)); return;
            }
            policy.validate(r.get("session_id"),r.get("grant_id"),r.get("frame_id"),now);
            if(!VIEW.s().isActive()) throw new IllegalStateException("Settlement view must be active");
            int x=Integer.parseInt(r.getOrDefault("x","0")),y=Integer.parseInt(r.getOrDefault("y","0"));
            String value=r.getOrDefault("value","");
            if(op.equals("click") || op.equals("hover") || op.equals("scroll")) policy.point(x,y);
            if(op.equals("click") && !value.equals("left") && !value.equals("right")) throw new IllegalArgumentException("Unknown mouse button");
            if(op.equals("scroll") && Math.abs(Integer.parseInt(value))>5) throw new IllegalArgumentException("Scroll at most five steps");
            // Never expose a synthetic click/key path to the local permission UI.
            if(op.equals("key") && value.equals("TAB")) throw new IllegalArgumentException("TAB navigation is not enabled in this prototype");
            driver.action(op,x,y,value, () -> policy.validate(r.get("session_id"),r.get("grant_id"),r.get("frame_id"),System.currentTimeMillis()));
            afterAction=r; settleUntil=now+200;
        } catch(Exception e) { reply(r,object("ok",false,"error",e.getMessage()==null?e.getClass().getSimpleName():e.getMessage())); }
    }
    private Map<String,Object> status() {
        return object("ok",true,"session_id",policy.session,"enabled",policy.enabled(System.currentTimeMillis()),
            "grant_id",policy.grant(System.currentTimeMillis()),"focused",driver.focused(),"settlement_view",VIEW.s().isActive(),
            "scope","settlement UI for up to 5 minutes; player may stop at any time");
    }
    private Map<String,Object> observe(String id) {
        String frame=UUID.randomUUID().toString();
        Path image=dir.resolve(id+".png"); driver.capture(image);
        policy.observe(frame,driver.width(),driver.height(),System.currentTimeMillis());
        Map<String,Object> result=status();
        result.putAll(object("frame_id",frame,"width",driver.width(),"height",driver.height(),
            "captured_at",Instant.now().toString(),"image",id+".png","coordinate_space","native game viewport pixels"));
        return result;
    }
    private void reply(Map<String,String> request,Map<String,Object> result) {
        String id=request.get("id"); result.put("action_id",id);
        io.execute(() -> { try { write(id,result); } catch(Exception e) { System.err.println("Syx assistant receipt: "+e); } });
    }
    private void write(String id,Map<String,Object> result) throws Exception {
        String json=JsonWriter.encode(result);
        if(json.getBytes(StandardCharsets.UTF_8).length>65536)
            json=JsonWriter.encode(object("ok",false,"action_id",id,"error","Result exceeds 64 KiB; select fewer fields or reduce limit/depth"));
        Path temp=dir.resolve(id+".tmp"); Files.writeString(temp,json);
        Files.move(temp,dir.resolve(id+".json"),StandardCopyOption.ATOMIC_MOVE,StandardCopyOption.REPLACE_EXISTING);
    }
    void close() { stopped=true; policy.stop(); }
}
