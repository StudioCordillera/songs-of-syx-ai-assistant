import syx.assistant.ControlPolicy;
import syx.assistant.JsonWriter;
import java.util.*;

public final class ControlPolicyTest {
    private static int checked;
    private static void reject(Runnable r) {
        try { r.run(); } catch (IllegalArgumentException expected) { checked++; return; }
        throw new AssertionError("Expected rejection");
    }
    public static void main(String[] args) {
        ControlPolicy p=new ControlPolicy("save-A");
        p.observe("frame-1",1024,768,1000);
        reject(() -> p.validate("save-A","","frame-1",1001));
        p.enableFromPlayer(1000); String grant=p.grant(1000);
        p.validate("save-A",grant,"frame-1",1001);
        reject(() -> p.validate("save-B",grant,"frame-1",1001));
        reject(() -> p.validate("save-A",grant,"frame-other",1001));
        reject(() -> p.validate("save-A",grant,"frame-1",7000));
        reject(() -> p.point(-1,100)); reject(() -> p.point(1024,100)); reject(() -> p.point(10,70));
        p.point(500,500); p.stop();
        reject(() -> p.validate("save-A",grant,"frame-1",1001));
        p.enableFromPlayer(1000);
        if(p.enabled(301000)) throw new AssertionError("Expired grant remained enabled");
        String json=JsonWriter.encode(Map.of("text","line\n\"quote\"\\slash😀","items",Arrays.asList(1,null,true)));
        if(!json.contains("\\n") || !json.contains("\\ud83d")) throw new AssertionError("Invalid JSON escaping");
        reject(() -> JsonWriter.encode(Double.NaN));
        System.out.println("Control policy/JSON checks passed: "+checked+" rejection cases");
    }
}
