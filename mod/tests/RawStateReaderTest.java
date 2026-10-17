package game.fixture;
import syx.assistant.*;
import java.util.*;
import java.util.function.Supplier;

public final class RawStateReaderTest {
    private static int failures;
    static class Node { private int amount=7; private String label="grain"; private Node self=this; private int[] values={2,4,6}; }
    private static void reject(Runnable r) { try {r.run();} catch(IllegalArgumentException e){failures++;return;} throw new AssertionError("Expected rejection"); }
    public static void main(String[] args) {
        Map<String,Supplier<Object>> roots=new LinkedHashMap<>(); roots.put("fixture",Node::new);
        RawStateReader reader=new RawStateReader(roots);
        String result=JsonWriter.encode(reader.execute(JsonReader.decode("[{\"root\":\"fixture\",\"fields\":{\"amount\":\"/amount\",\"item\":\"/values/1\",\"size\":\"/values/@size\"}}]")));
        if(!result.contains("\"amount\":7")||!result.contains("\"item\":4")||!result.contains("\"size\":3"))throw new AssertionError(result);
        String cycle=JsonWriter.encode(reader.execute(JsonReader.decode("[{\"root\":\"fixture\",\"depth\":3}]")));
        if(!cycle.contains("$cycle"))throw new AssertionError(cycle);
        reject(()->reader.execute(JsonReader.decode("[{\"root\":\"fixture\",\"path\":\"/values/99\"}]")));
        reject(()->reader.execute(JsonReader.decode("[{\"root\":\"fixture\",\"path\":\"/label/value\"}]")));
        reject(()->reader.execute(JsonReader.decode("[{\"root\":\"fixture\",\"depth\":5}]")));
        reject(()->JsonReader.decode("{\"a\":1,\"a\":2}")); reject(()->JsonReader.decode("[1,]"));
        reject(()->JsonReader.decode("1e999")); reject(()->JsonReader.decode("{} trailing"));
        Object escaped=JsonReader.decode("\"a\\n\\u0062\""); if(!escaped.equals("a\nb"))throw new AssertionError();
        System.out.println("Raw state/parser checks passed; rejected "+failures+" invalid requests");
    }
}
