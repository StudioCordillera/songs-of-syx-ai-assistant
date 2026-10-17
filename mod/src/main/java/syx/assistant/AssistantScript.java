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
    public static Path stateDirectory() {
        String configured = System.getProperty("syx.assistant.stateDir", System.getenv("SYX_STATE_DIR"));
        if (configured != null && !configured.isBlank()) return Paths.get(configured).toAbsolutePath();
        return Paths.get(System.getProperty("user.home"), ".local", "share", "syx-assistant");
    }
    static final class Instance implements SCRIPT_INSTANCE {
        final String session = UUID.randomUUID().toString();
        final Path dir = stateDirectory();
        final AtomicReference<Map<String,Object>> pending = new AtomicReference<>();
        final ScheduledExecutorService io;
        long sequence = 0, lastCapture = 0;
        volatile boolean closed;
        final ControlBridge control;
        Instance() {
            try {
                Files.createDirectories(dir);
                try { Files.setPosixFilePermissions(dir, PosixFilePermissions.fromString("rwx------")); }
                catch (UnsupportedOperationException ignored) { }
            } catch (IOException e) { throw new IllegalStateException("Cannot create assistant runtime directory", e); }
            io = Executors.newSingleThreadScheduledExecutor(r -> { Thread t = new Thread(r, "syx-assistant-export"); t.setDaemon(true); return t; });
            control = new ControlBridge(session, dir, io, this::close);
            io.scheduleWithFixedDelay(this::flush, 0, 100, TimeUnit.MILLISECONDS);
            Runtime.getRuntime().addShutdownHook(new Thread(this::close, "syx-assistant-close"));
        }
        public void update(double ds) {
            if (closed) return;
            control.update();
            long now = System.nanoTime();
            if (now-lastCapture < 2_000_000_000L) return;
            lastCapture = now;
            pending.set(StateCollector.collect(session, ++sequence));
        }
        private synchronized void flush() {
            Map<String,Object> dto = pending.getAndSet(null);
            if (dto == null) return;
            try {
                byte[] bytes = JsonWriter.encode(dto).getBytes(StandardCharsets.UTF_8);
                if (bytes.length > 16*1024*1024) throw new IOException("Snapshot exceeds 16 MiB");
                Path tmp = dir.resolve("snapshot-"+session+".tmp");
                Files.write(tmp, bytes);
                Files.move(tmp, dir.resolve("snapshot.json"), StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING);
            } catch (Exception e) { System.err.println("Syx assistant export: "+e); }
        }
        synchronized void close() {
            if (closed) return;
            closed = true;
            if (control != null) control.close();
            pending.set(StateCollector.envelope(session, ++sequence, false));
            flush(); io.shutdown();
        }
        public void save(FilePutter file) { /* No persistent save data or account credentials. */ }
        public void load(FileGetter file) throws IOException { /* Session IDs are never restored from saves. */ }
    }
}
