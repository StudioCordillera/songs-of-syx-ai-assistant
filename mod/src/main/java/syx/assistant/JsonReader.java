package syx.assistant;

import java.util.*;

/** Strict small JSON decoder for bounded query specifications. */
public final class JsonReader {
    private final String text; private int at;
    private JsonReader(String text) { this.text=text; }
    public static Object decode(String text) {
        if(text.length()>8192) throw new IllegalArgumentException("Query exceeds 8 KiB");
        JsonReader parser=new JsonReader(text); Object result=parser.value(0); parser.space();
        if(parser.at!=text.length()) throw new IllegalArgumentException("Trailing JSON input");
        return result;
    }
    private void space() { while(at<text.length() && " \r\n\t".indexOf(text.charAt(at))>=0) at++; }
    private char take() { if(at>=text.length()) throw new IllegalArgumentException("Unexpected end of JSON"); return text.charAt(at++); }
    private Object value(int depth) {
        if(depth>16) throw new IllegalArgumentException("Query nesting exceeds 16"); space(); char c=take();
        if(c=='"') return string();
        if(c=='{') {
            Map<String,Object> result=new LinkedHashMap<>(); space();
            if(at<text.length() && text.charAt(at)=='}') { at++; return result; }
            while(true) {
                space(); if(take()!='"') throw new IllegalArgumentException("Expected JSON object key");
                String key=string();space();if(take()!=':') throw new IllegalArgumentException("Expected colon");
                if(result.containsKey(key)) throw new IllegalArgumentException("Duplicate JSON key");
                result.put(key,value(depth+1)); if(result.size()>100) throw new IllegalArgumentException("Too many object keys");
                space();char next=take();if(next=='}') return result;if(next!=',') throw new IllegalArgumentException("Expected comma");
            }
        }
        if(c=='[') {
            List<Object> result=new ArrayList<>();space();
            if(at<text.length() && text.charAt(at)==']') { at++;return result; }
            while(true) {
                result.add(value(depth+1));if(result.size()>100) throw new IllegalArgumentException("Too many array items");
                space();char next=take();if(next==']') return result;if(next!=',') throw new IllegalArgumentException("Expected comma");
            }
        }
        at--;int start=at;
        while(at<text.length() && ",]} \t\n\r".indexOf(text.charAt(at))<0) at++;
        String literal=text.substring(start,at);
        if(literal.equals("null")) return null;if(literal.equals("true")) return true;if(literal.equals("false")) return false;
        if(!literal.matches("-?(0|[1-9][0-9]*)(\\.[0-9]+)?([eE][+-]?[0-9]+)?")) throw new IllegalArgumentException("Invalid JSON literal");
        double number=Double.parseDouble(literal); if(!Double.isFinite(number)) throw new IllegalArgumentException("Non-finite number");
        if(!literal.contains(".") && !literal.contains("e") && !literal.contains("E")) return Long.parseLong(literal);
        return number;
    }
    private String string() {
        StringBuilder out=new StringBuilder();
        while(true) {
            char c=take();if(c=='"') return out.toString();if(c<32) throw new IllegalArgumentException("Unescaped control character");
            if(c=='\\') {
                c=take();switch(c) {
                    case '"': case '\\': case '/': out.append(c);break;
                    case 'b':out.append('\b');break;case 'f':out.append('\f');break;
                    case 'n':out.append('\n');break;case 'r':out.append('\r');break;case 't':out.append('\t');break;
                    case 'u':
                        if(at+4>text.length()) throw new IllegalArgumentException("Incomplete Unicode escape");
                        out.append((char)Integer.parseInt(text.substring(at,at+4),16));at+=4;break;
                    default:throw new IllegalArgumentException("Invalid JSON escape");
                }
            } else out.append(c);
        }
    }
}
