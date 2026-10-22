package syx.assistant.candidate;

import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.channels.SeekableByteChannel;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.nio.file.attribute.PosixFilePermissions;
import java.util.*;

/** Detached developer geometry preferences. No game identity, transcript, key or global UI state. */
public final class PanelPreferences {
    public static final int MAX_BYTES=512,MAX_DIMENSION=8192;
    private static final String NAME="chat-layout.preferences";
    private static final List<String> KEYS=List.of("version","panel_x","panel_y","panel_width","panel_height","launcher_x","launcher_y","launcher_width","launcher_height");
    public final GestureReducer.Rect panel,launcher;
    public PanelPreferences(GestureReducer.Rect panel,GestureReducer.Rect launcher){
        this.panel=checked(panel);this.launcher=checked(launcher);
    }
    private static GestureReducer.Rect checked(GestureReducer.Rect r){
        if(r==null)throw new IllegalArgumentException("Missing layout");
        for(double v:new double[]{r.x,r.y,r.width,r.height})if(!Double.isFinite(v)||v!=Math.rint(v)||v<0||v>MAX_DIMENSION)throw new IllegalArgumentException("Bounded integer layout required");
        if(r.width<1||r.height<1)throw new IllegalArgumentException("Positive layout required");
        return r;
    }
    public String encode(){
        double[] v={1,panel.x,panel.y,panel.width,panel.height,launcher.x,launcher.y,launcher.width,launcher.height};
        StringBuilder out=new StringBuilder();for(int i=0;i<KEYS.size();i++)out.append(KEYS.get(i)).append('=').append((int)v[i]).append('\n');return out.toString();
    }
    public static PanelPreferences decode(byte[] bytes){
        if(bytes.length>MAX_BYTES)throw new IllegalArgumentException("Preferences exceed bound");
        for(byte b:bytes)if(b<0||b=='\r')throw new IllegalArgumentException("ASCII preferences required");
        String[] rows=new String(bytes,StandardCharsets.US_ASCII).split("\n",-1);
        int count=rows.length-(rows.length>0&&rows[rows.length-1].isEmpty()?1:0);
        if(count!=KEYS.size())throw new IllegalArgumentException("Invalid preference fields");
        Map<String,Integer> fields=new HashMap<>();
        for(int i=0;i<count;i++){
            String[] pair=rows[i].split("=",-1);
            if(pair.length!=2||!KEYS.contains(pair[0])||!pair[1].matches("0|[1-9][0-9]{0,3}")||fields.put(pair[0],Integer.parseInt(pair[1]))!=null)throw new IllegalArgumentException("Invalid preference field");
        }
        if(fields.size()!=KEYS.size()||fields.get("version")!=1)throw new IllegalArgumentException("Unsupported preferences");
        return new PanelPreferences(new GestureReducer.Rect(fields.get("panel_x"),fields.get("panel_y"),fields.get("panel_width"),fields.get("panel_height")),
            new GestureReducer.Rect(fields.get("launcher_x"),fields.get("launcher_y"),fields.get("launcher_width"),fields.get("launcher_height")));
    }
    private static Path target(Path directory)throws IOException{
        Path root=directory.toAbsolutePath().normalize();
        if(!Files.isDirectory(root,LinkOption.NOFOLLOW_LINKS)||!root.toRealPath().equals(root))throw new IOException("Regular existing preference directory required");
        Path file=root.resolve(NAME);if(Files.isSymbolicLink(file))throw new IOException("Preference link refused");return file;
    }
    public static PanelPreferences load(Path directory)throws IOException{
        Path file=target(directory);if(!Files.exists(file,LinkOption.NOFOLLOW_LINKS))return null;
        if(!Files.isRegularFile(file,LinkOption.NOFOLLOW_LINKS))throw new IOException("Regular preference file required");
        try(SeekableByteChannel channel=Files.newByteChannel(file,Set.of(StandardOpenOption.READ,LinkOption.NOFOLLOW_LINKS))){
            ByteBuffer buffer=ByteBuffer.allocate(MAX_BYTES+1);while(buffer.hasRemaining()&&channel.read(buffer)!=-1){}
            return decode(Arrays.copyOf(buffer.array(),buffer.position()));
        }
    }
    public void save(Path directory)throws IOException{
        Path file=target(directory),temp=Files.createTempFile(file.getParent(),".chat-layout-",".tmp");
        try{
            // Linux candidate: explicit private permissions; unsupported filesystems refuse.
            Files.setPosixFilePermissions(temp,PosixFilePermissions.fromString("rw-------"));
            Files.writeString(temp,encode(),StandardCharsets.US_ASCII,StandardOpenOption.TRUNCATE_EXISTING);
            target(directory); // Refuse an existing link; replacement itself never follows it.
            Files.move(temp,file,StandardCopyOption.ATOMIC_MOVE,StandardCopyOption.REPLACE_EXISTING);
        }finally{Files.deleteIfExists(temp);}
    }
}
