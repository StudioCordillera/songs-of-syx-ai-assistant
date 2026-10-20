package syx.assistant;

import java.nio.charset.StandardCharsets;
import java.util.*;

/** No engine initialization: exercises only detached request parsing and integer predicates. */
public final class StockpileProtocolCheck {
    static int rejected=0,accepted=0;
    static String encoded(String text){return Base64.getUrlEncoder().withoutPadding().encodeToString(text.getBytes(StandardCharsets.UTF_8));}
    static String frame(){return "protocol=1\nrequest_id=12345678-1234-4234-8234-123456789abc\nsession=87654321-4321-4321-8321-123456789abc\nexpires="+(System.currentTimeMillis()+8000)+"\nrooms=\nresources="+encoded("grain")+"\nfields=stored_raw,capacity_raw\nfilters=\nactive=\ncursor=0\nscan_limit=4096\nlimit=25\n";}
    static String with(String key,String value){return frame().replaceAll("(?m)^"+key+"=.*$",java.util.regex.Matcher.quoteReplacement(key+"="+value));}
    static StockpileReadRequest accept(String text){StockpileReadRequest r=StockpileReadRequest.parse(text);accepted++;return r;}
    static void reject(String text){try{StockpileReadRequest.parse(text);}catch(IllegalArgumentException expected){rejected++;return;}throw new AssertionError("Accepted invalid frame");}
    static void require(boolean value){if(!value)throw new AssertionError("Detached codec assertion");}
    public static void main(String[] args){
        StockpileReadRequest r=accept(frame());require(r.roomIds.isEmpty() && r.cursor==0 && r.scanLimit==4096 && r.limit==25 && r.active==null);
        require(accept(with("rooms","0,2147483647")).roomIds.equals(List.of(0,2147483647)));
        String key="粮\nlimit=100 😀";require(accept(with("resources",encoded(key))).resources.equals(List.of(key)));
        require(accept(with("active","false")).active.equals(false));
        require(accept(with("filters","stored_raw:gte:-2147483648,capacity_raw:lte:2147483647")).filters.size()==2);
        accept(with("resources",encoded("😀".repeat(50))));
        accept(frame().stripTrailing());
        for(String s:new String[]{"-0","00","+1","1.0","2147483648","-1"," 1","1 "})reject(with("cursor",s));
        reject(with("rooms","1,1"));reject(with("rooms","1,"));reject(with("rooms","-1"));
        reject(with("resources",""));reject(with("resources","Z3JhaW4="));reject(with("resources","_w"));
        reject(with("resources",encoded("grain")+","+encoded("grain")));reject(with("resources",encoded("😀".repeat(51))));
        reject(with("resources",String.join(",",java.util.stream.IntStream.range(0,101).mapToObj(i->encoded("r"+i)).toList())));
        reject(with("rooms",String.join(",",java.util.stream.IntStream.range(0,101).mapToObj(String::valueOf).toList())));
        reject(with("fields","stored_raw,stored_raw"));reject(with("fields",""));reject(with("fields","invoke"));
        reject(with("filters","stored_raw:execute:1"));reject(with("filters","private:eq:1"));reject(with("filters","stored_raw:eq:2147483648"));
        reject(with("filters",String.join(",",Collections.nCopies(5,"stored_raw:eq:0"))));
        reject(with("active","True"));reject(with("limit","0"));reject(with("limit","101"));reject(with("scan_limit","4097"));
        reject(with("protocol","2"));reject(with("session","1-1-1-1-1"));reject(with("request_id","12345678-1234-4234-8234-123456789ABC"));
        reject(with("expires",Long.toString(System.currentTimeMillis()+60000)));reject(with("expires","1"));
        reject(frame()+"limit=1\n");reject(frame()+"method=deposit\n");reject(frame()+"\n");reject(frame().replace("\n","\r\n"));
        reject(frame().replace("protocol=1","protocol=１"));reject(frame().replace("active=\n",""));reject("x".repeat(8193));
        int predicates=0;
        int[] samples={Integer.MIN_VALUE,-1,0,1,Integer.MAX_VALUE};
        for(String op:StockpileReadRequest.OPS)for(int n:samples)for(int v:samples){
            boolean expected=switch(op){case "eq"->n==v;case "ne"->n!=v;case "lt"->n<v;case "lte"->n<=v;case "gt"->n>v;case "gte"->n>=v;default->false;};
            require(new StockpileReadRequest.Filter("stored_raw",op,v).matches(n)==expected);predicates++;
        }
        System.out.println("{\"accepted_frames\":"+accepted+",\"rejected_frames\":"+rejected+",\"predicate_checks\":"+predicates+",\"engine_initialized\":false}");
    }
}
