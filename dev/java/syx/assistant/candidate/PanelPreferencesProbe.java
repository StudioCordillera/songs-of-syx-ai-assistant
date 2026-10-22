package syx.assistant.candidate;
import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.attribute.PosixFilePermissions;

/** Standalone offline filesystem/format probe; no game dependencies or real settings. */
public final class PanelPreferencesProbe {
    private static void require(boolean b){if(!b)throw new AssertionError();}
    private static void rejected(String raw){try{PanelPreferences.decode(raw.getBytes(StandardCharsets.UTF_8));throw new AssertionError("Accepted malformed input");}catch(IllegalArgumentException expected){}}
    private static void ok(String name){System.out.println(name);}
    public static void main(String[] args)throws Exception{
        Path root=Path.of(args[0]),file=root.resolve("chat-layout.preferences");
        if(args.length>1){
            if(args[1].equals("write-v2"))new PanelPreferences(new GestureReducer.Rect(128,85,900,680),new GestureReducer.Rect(12,24,112,36),PanelTheme.preset("Night").withAccent("#123456")).save(root);
            else if(args[1].equals("read-v2")){
                var loaded=PanelPreferences.load(root);require(loaded.panel.x==128&&loaded.panel.y==85&&loaded.panel.width==900&&loaded.panel.height==680);
                require(loaded.launcher.x==12&&loaded.launcher.y==24&&loaded.theme.name.equals("Night")&&loaded.theme.accentHex().equals("#123456"));
            }else throw new AssertionError("Unknown fixed probe mode");
            System.out.println("PASS "+args[1]);return;
        }
        var value=new PanelPreferences(new GestureReducer.Rect(24,40,840,640),new GestureReducer.Rect(8,80,112,36));
        String encoded="version=1\npanel_x=24\npanel_y=40\npanel_width=840\npanel_height=640\nlauncher_x=8\nlauncher_y=80\nlauncher_width=112\nlauncher_height=36\n";
        require(value.encode().equals(encoded));require(PanelPreferences.decode(encoded.getBytes(StandardCharsets.US_ASCII)).encode().equals(encoded));ok("exact_roundtrip");
        rejected(encoded.replace("version=1","version=99"));ok("unknown_version");
        rejected(encoded.replace("panel_x=24","panel_x=24\npanel_x=24"));ok("duplicate_fields");
        rejected(encoded.replace("panel_x=24","unknown=24"));ok("unknown_fields");
        rejected(encoded.replace("panel_x=24\n",""));ok("missing_fields");
        for(String v:new String[]{"-1","+1","01","1.0","NaN","999999999999"," 1","8193"})rejected(encoded.replace("panel_x=24","panel_x="+v));ok("invalid_bounded_integers");
        rejected(encoded.replace("panel_width=840","panel_width=0"));ok("zero_dimensions");
        rejected(encoded+"\n");rejected(encoded.replace("\n","\r\n"));rejected(encoded.replace("version","vérsion"));rejected("x".repeat(513));ok("ascii_lines_and_byte_bound");
        String v2=encoded.replace("version=1","version=2")+"preset=Night\naccent=#ABCDEF\n";
        var styled=new PanelPreferences(value.panel,value.launcher,PanelTheme.preset("Night").withAccent("#abcdef"));
        require(styled.encode().equals(v2)&&PanelPreferences.decode(v2.getBytes(StandardCharsets.US_ASCII)).encode().equals(v2));ok("version_two_roundtrip");
        for(String bad:new String[]{v2.replace("preset=Night","preset=unknown"),v2.replace("accent=#ABCDEF","accent=#abcdef"),v2.replace("accent=#ABCDEF\n",""),v2+"accent=#000000\n",v2.replace("version=2","version=1")})rejected(bad);ok("version_two_style_refusal");
        value.save(root);require(PanelPreferences.load(root).theme==null&&Files.readString(file).equals(encoded));Files.delete(file);ok("legacy_load_no_rewrite");
        require(PanelPreferences.load(root)==null);ok("missing_file_defaults");
        value.save(root);require(Files.readString(file).equals(encoded));require(Files.getPosixFilePermissions(file).equals(PosixFilePermissions.fromString("rw-------")));ok("private_atomic_save");
        var moved=new PanelPreferences(new GestureReducer.Rect(100,70,900,680),value.launcher);moved.save(root);require(PanelPreferences.load(root).panel.width==900);ok("replace_and_fresh_load");
        Files.writeString(file,"x".repeat(513));try{PanelPreferences.load(root);throw new AssertionError();}catch(IllegalArgumentException expected){}require(Files.size(file)==513);ok("oversized_file_preserved");
        Files.delete(file);Files.createDirectory(file);try{PanelPreferences.load(root);throw new AssertionError();}catch(java.io.IOException expected){}Files.delete(file);ok("directory_file_refused");
        Path outside=root.resolve("unrelated");Files.writeString(outside,"preserve unrelated data");Files.createSymbolicLink(file,outside);
        try{PanelPreferences.load(root);throw new AssertionError();}catch(java.io.IOException expected){}
        try{value.save(root);throw new AssertionError();}catch(java.io.IOException expected){}
        require(Files.readString(outside).equals("preserve unrelated data"));Files.delete(file);ok("symlink_load_save_refused");
        Path link=root.resolve("directory-link");Files.createSymbolicLink(link,root);
        try{PanelPreferences.load(link);throw new AssertionError();}catch(java.io.IOException expected){}ok("symlink_directory_refused");
        Files.createLink(file,outside);value.save(root);require(Files.readString(outside).equals("preserve unrelated data"));require(Files.readString(file).equals(encoded));ok("atomic_replace_preserves_other_hardlink");
        try(var entries=Files.list(root)){require(entries.noneMatch(p->p.getFileName().toString().startsWith(".chat-layout-")));}ok("no_temporary_files_left");
    }
}
