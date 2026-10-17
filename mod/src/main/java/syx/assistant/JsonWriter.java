package syx.assistant;

import java.util.Map;

/** Small JSON encoder for immutable export DTOs; no game objects accepted. */
public final class JsonWriter {
    private JsonWriter() {}
    public static String encode(Object value) {
        StringBuilder out = new StringBuilder(); append(out, value); return out.toString();
    }
    private static void append(StringBuilder out, Object value) {
        if (value == null) { out.append("null"); return; }
        if (value instanceof CharSequence) { quote(out, value.toString()); return; }
        if (value instanceof Boolean) { out.append(value); return; }
        if (value instanceof Number) {
            double n = ((Number)value).doubleValue();
            if (!Double.isFinite(n)) throw new IllegalArgumentException("Non-finite JSON value");
            out.append(value); return;
        }
        if (value instanceof Map<?,?>) {
            out.append('{'); boolean first = true;
            for (Map.Entry<?,?> e : ((Map<?,?>)value).entrySet()) {
                if (!first) out.append(','); first = false;
                quote(out, (String)e.getKey()); out.append(':'); append(out, e.getValue());
            }
            out.append('}'); return;
        }
        if (value instanceof Iterable<?>) {
            out.append('['); boolean first = true;
            for (Object e : (Iterable<?>)value) {
                if (!first) out.append(','); first = false; append(out, e);
            }
            out.append(']'); return;
        }
        throw new IllegalArgumentException("Unsupported DTO: " + value.getClass());
    }
    private static void quote(StringBuilder out, String value) {
        out.append('"');
        for (int i = 0; i < value.length(); i++) {
            char c = value.charAt(i);
            switch(c) {
                case '"': out.append("\\\""); break;
                case '\\': out.append("\\\\"); break;
                case '\n': out.append("\\n"); break;
                case '\r': out.append("\\r"); break;
                case '\t': out.append("\\t"); break;
                default:
                    if (c < 32 || Character.isSurrogate(c)) out.append(String.format("\\u%04x", (int)c));
                    else out.append(c);
            }
        }
        out.append('"');
    }
}
