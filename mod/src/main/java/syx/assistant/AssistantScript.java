package syx.assistant;

import game.GAME;
import game.VERSION;
import game.GameDisposable;
import script.SCRIPT;
import snake2d.util.file.FileGetter;
import snake2d.util.file.FilePutter;
import java.io.IOException;
import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.attribute.PosixFilePermissions;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicReference;

/** Version-scoped script. No proprietary source or game classes are bundled. */
public final class AssistantScript implements SCRIPT {
    private static Instance active;
    private static final GameDisposable LIFECYCLE = new GameDisposable() {
        @Override protected void dispose() { if (active != null) { active.close(); active = null; } }
    };
    public CharSequence name() { return "Syx AI Assistant"; }
    public CharSequence desc() { return "Exports game state locally for your AI assistant."; }
    public boolean isSelectable() { return false; }
    public boolean forceInit() { return true; }
    public SCRIPT_INSTANCE createInstance() {
        if (active != null) active.close();
        if (!"0.71.44".equals(VERSION.VERSION_STRING))
            throw new IllegalStateException("Syx assistant targets exactly 0.71.44; rebuild and validate before changing this guard.");
        StateCollector.clearReferenceCache();
        active = new Instance(); return active;
    }
    static ChatPanel currentChatPanel() { return active==null?null:active.chatPanel; }
    static Map<String,Object> chatContext() {
        return active!=null && active.chatPanel!=null?active.chatPanel.context():StateCollector.object("enabled",false);
    }
    public static Path stateDirectory() {
        String configured = System.getProperty("syx.assistant.stateDir", System.getenv("SYX_STATE_DIR"));
        if (configured != null && !configured.isBlank()) return Paths.get(configured).toAbsolutePath();
        return Paths.get(System.getProperty("user.home"), ".local", "share", "syx-assistant");
    }
    static final class Instance implements SCRIPT_INSTANCE {
        final String session = UUID.randomUUID().toString();
        final Path dir = stateDirectory();
        final AtomicReference<Map<String,Object>> pending = new AtomicReference<>();
        final AtomicReference<EntityReadRequest> readRequest = new AtomicReference<>();
        final AtomicReference<Map<String,Object>> readResponse = new AtomicReference<>();
        final AtomicReference<TileReadRequest> tileRequest = new AtomicReference<>();
        final AtomicReference<Map<String,Object>> tileResponse = new AtomicReference<>();
        String lastTileRequestText;
        String lastRequestText;
        final ScheduledExecutorService io;
        final AtomicReference<String> chatState=new AtomicReference<>();
        final AtomicReference<String> chatAction=new AtomicReference<>();
        ChatPanel chatPanel;
        long sequence = 0, lastCapture = 0;
        volatile boolean closed;
        Instance() {
            try {
                Files.createDirectories(dir);
                try { Files.setPosixFilePermissions(dir, PosixFilePermissions.fromString("rwx------")); }
                catch (UnsupportedOperationException ignored) { }
            } catch (IOException e) { throw new IllegalStateException("Cannot create assistant runtime directory", e); }
            io = Executors.newSingleThreadScheduledExecutor(r -> { Thread t = new Thread(r, "syx-assistant-export"); t.setDaemon(true); return t; });
            io.scheduleWithFixedDelay(this::flush, 0, 100, TimeUnit.MILLISECONDS);
            Runtime.getRuntime().addShutdownHook(new Thread(this::close, "syx-assistant-close"));
            GAME.addAfterUpdate(this::sample);
        }
        public void update(double ds) { /* GAME.addAfterUpdate also runs when UI pauses skip resource updates. */ }
        private void sample() {
            if (closed) return;
            if(Boolean.getBoolean("syx.assistant.chat")) {
                if(chatPanel==null)chatPanel=new ChatPanel(session,chatAction::set);
                chatPanel.refresh(chatState.get());
            }
            EntityReadRequest request=readRequest.getAndSet(null);
            if(request!=null) readResponse.set(request.collect(session));
            TileReadRequest tiles=tileRequest.getAndSet(null);
            if(tiles!=null)tileResponse.set(tiles.collect(session));
            long now = System.nanoTime();
            if (now-lastCapture < 2_000_000_000L) return;
            lastCapture = now;
            pending.set(StateCollector.collect(session, ++sequence));
        }
        private void writeDto(String name,Map<String,Object> dto,int cap) throws IOException {
            byte[] bytes=JsonWriter.encode(dto).getBytes(StandardCharsets.UTF_8);
            if(bytes.length>cap)throw new IOException("Export exceeds size limit");
            Path tmp=dir.resolve(name+"-"+session+".tmp");
            Files.write(tmp,bytes);
            Files.move(tmp,dir.resolve(name+".json"),StandardCopyOption.ATOMIC_MOVE,StandardCopyOption.REPLACE_EXISTING);
        }
        private void pollReadRequest() {
            Path file=dir.resolve("entity-request.txt");
            try {
                if(!Files.isRegularFile(file,LinkOption.NOFOLLOW_LINKS))return;
                byte[] raw;
                try(java.io.InputStream input=Files.newInputStream(file)){raw=input.readNBytes(8193);}
                if(raw.length>8192)throw new IOException("Read request exceeds 8 KiB");
                String text=new String(raw,StandardCharsets.UTF_8);
                if(text.equals(lastRequestText))return;
                lastRequestText=text;
                readRequest.set(EntityReadRequest.parse(text));
            } catch(Exception error) { System.err.println("Syx assistant read request: "+error); }
        }
        private void pollTileRequest() {
            Path file=dir.resolve("tile-request.txt");
            try {
                if(!Files.isRegularFile(file,LinkOption.NOFOLLOW_LINKS))return;
                byte[] raw;
                try(java.io.InputStream input=Files.newInputStream(file)){raw=input.readNBytes(8193);}
                if(raw.length>8192)throw new IOException("Tile request exceeds 8 KiB");
                String text=new String(raw,StandardCharsets.UTF_8);
                if(text.equals(lastTileRequestText))return;
                lastTileRequestText=text;tileRequest.set(TileReadRequest.parse(text));
            } catch(Exception error){System.err.println("Syx assistant tile request: "+error);}
        }
        private void pollChat() {
            try {
                Path file=dir.resolve("chat-ui.txt");
                if(Files.isRegularFile(file,LinkOption.NOFOLLOW_LINKS)) {
                    byte[] raw;
                    try(java.io.InputStream input=Files.newInputStream(file)){raw=input.readNBytes(262145);}
                    if(raw.length<=262144)chatState.set(new String(raw,StandardCharsets.UTF_8));
                }
                String action=chatAction.getAndSet(null);
                if(action!=null) {
                    Path tmp=dir.resolve("chat-action-"+session+".tmp");
                    Files.writeString(tmp,action,StandardCharsets.US_ASCII);
                    Files.move(tmp,dir.resolve("chat-action.txt"),StandardCopyOption.ATOMIC_MOVE,StandardCopyOption.REPLACE_EXISTING);
                }
            }catch(Exception error){System.err.println("Syx assistant chat IPC failed");}
        }
        private synchronized void flush() {
            if(!closed){pollReadRequest();pollTileRequest();if(Boolean.getBoolean("syx.assistant.chat"))pollChat();}
            Map<String,Object> tiles=tileResponse.getAndSet(null);
            if(tiles!=null)try {
                if(JsonWriter.encode(tiles).getBytes(StandardCharsets.UTF_8).length>65536)
                    tiles=StateCollector.object("request_id",tiles.get("request_id"),"session_id",session,"game_version",VERSION.VERSION_STRING,
                        "captured_at",java.time.Instant.now().toString(),"available",false,"reason","Tile response exceeds 64 KiB; select fewer fields or rows","data",null);
                writeDto("tile-response",tiles,65536);
            } catch(Exception error){System.err.println("Syx assistant tile response: "+error);}
            Map<String,Object> response=readResponse.getAndSet(null);
            if(response!=null)try {
                int cap="capture".equals(response.get("read_mode"))?2*1024*1024:65536;
                if(JsonWriter.encode(response).getBytes(StandardCharsets.UTF_8).length>cap)
                    response=StateCollector.object("request_id",response.get("request_id"),"session_id",session,"game_version",VERSION.VERSION_STRING,
                        "captured_at",java.time.Instant.now().toString(),"available",false,"reason","Response exceeds the read mode byte budget; select fewer fields, stats or rows","data",null);
                writeDto("entity-response",response,cap);
            } catch(Exception error) {System.err.println("Syx assistant read response: "+error);}
            Map<String,Object> dto = pending.getAndSet(null);
            if (dto == null) return;
            try { writeDto("snapshot",dto,16*1024*1024); }
            catch (Exception e) { System.err.println("Syx assistant export: "+e); }
        }
        synchronized void close() {
            if (closed) return;
            closed = true;
            readRequest.set(null);readResponse.set(null);tileRequest.set(null);tileResponse.set(null);
            pending.set(StateCollector.envelope(session, ++sequence, false));
            flush(); io.shutdown();
        }
        public void save(FilePutter file) { /* No persistent save data or account credentials. */ }
        public void load(FileGetter file) throws IOException { /* Session IDs are never restored from saves. */ }
    }
}
