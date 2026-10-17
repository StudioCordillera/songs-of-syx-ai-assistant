import syx.assistant.JsonWriter;
import java.util.*;
public final class JsonWriterTest {
    public static void main(String[] args) {
        String json=JsonWriter.encode(Map.of("text","line\n\"quote\"\\slash😀","items",Arrays.asList(1,null,true)));
        if(!json.contains("\\n")||!json.contains("\\ud83d")) throw new AssertionError("Invalid escaping");
        try { JsonWriter.encode(Double.NaN); throw new AssertionError("Accepted NaN"); }
        catch(IllegalArgumentException expected) { }
        System.out.println("Detached JSON serialization checks passed");
    }
}
