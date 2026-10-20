package syx.assistant.candidate;

import java.nio.ByteBuffer;
import java.nio.charset.*;
import java.util.*;

/** Unshipped detached protocol model. No game API, native input, rendering or file I/O. */
public final class DisplayFrame {
    public record Reply(int row,String event,String turn,String observedSession,String payloadHash) {}
    public final String epoch,frame,chat,runtime;
    public final Integer total,unreadChats;
    public final boolean allChatCounts,omitted;
    public final List<String> lines;
    public final Map<Integer,Reply> replies;
    public final Map<String,Integer> perChat;
    private static final Set<String> SCALARS=Set.of("protocol","epoch","frame","chat","runtime","counts","unread_total","chat_counts_complete","unread_chat_count","omitted");

    private DisplayFrame(Map<String,String> fields,List<String> text,List<String> rawReplies,Map<String,Integer> chatCounts) {
        require("3".equals(fields.get("protocol")),"Paired display protocol 3 required");
        epoch=uuid(fields.get("epoch"));frame=uuid(fields.get("frame"));
        chat=fields.containsKey("chat")?uuid(fields.get("chat")):null;
        runtime=fields.containsKey("runtime")?uuid(fields.get("runtime")):null;
        String state=fields.get("counts");require("ready".equals(state)||"unavailable".equals(state),"Explicit count availability required");
        if(state.equals("ready")) {
            total=integer(fields.get("unread_total"),10000);unreadChats=integer(fields.get("unread_chat_count"),10000);
            allChatCounts=bool(fields.get("chat_counts_complete"));
            int sum=0,positive=0;
            for(Map.Entry<String,Integer> entry:chatCounts.entrySet()) {
                int count=entry.getValue();sum+=count;if(count>0)positive++;
                else require(entry.getKey().equals(chat),"Only selected chat may have an explicit zero count");
            }
            require(positive<=unreadChats&&sum<=total,"Count metadata exceeds complete totals");
            if(allChatCounts)require(positive==unreadChats&&sum==total,"Complete count metadata disagrees with totals");
            else require(positive<unreadChats&&sum<total,"Partial metadata must disclose missing positive chat counts");
            if(chat!=null)require(chatCounts.containsKey(chat),"Selected chat count required");
        } else {
            total=null;unreadChats=null;allChatCounts=false;
            require(!fields.containsKey("unread_total")&&!fields.containsKey("unread_chat_count")&&!fields.containsKey("chat_counts_complete")&&chatCounts.isEmpty()&&rawReplies.isEmpty(),"Unknown is not zero or receipt eligibility");
        }
        omitted=fields.containsKey("omitted");if(omitted)require("true".equals(fields.get("omitted")),"Invalid omission marker");
        Map<Integer,Reply> parsed=new LinkedHashMap<>();Set<String> events=new HashSet<>();
        for(String row:rawReplies) {
            require(total!=null&&chat!=null&&runtime!=null,"Receipt needs selected chat and runtime");
            String[] parts=row.split("\\|",-1);require(parts.length==5,"Invalid reply provenance");
            int index=integer(parts[0],100);require(index<text.size(),"Reply index outside preview");
            Reply reply=new Reply(index,uuid(parts[1]),uuid(parts[2]),uuid(parts[3]),parts[4]);
            require(parts[4].matches("[0-9a-f]{64}"),"Issued payload fingerprint required");
            require(events.add(reply.event())&&parsed.putIfAbsent(index,reply)==null,"Duplicate reply row/event");
        }
        lines=List.copyOf(text);replies=Map.copyOf(parsed);perChat=Map.copyOf(chatCounts);
    }

    public static DisplayFrame parse(byte[] bytes) {
        require(bytes!=null&&bytes.length>0&&bytes.length<=240000,"Display frame exceeds bounds");
        for(byte b:bytes)require(b>=0&&b!=13,"ASCII LF framing required");
        require(bytes[bytes.length-1]==10,"Final newline required");
        String[] raw=new String(bytes,StandardCharsets.US_ASCII).split("\n",-1);
        Map<String,String> fields=new HashMap<>();List<String> text=new ArrayList<>(),reply=new ArrayList<>();Map<String,Integer> counts=new LinkedHashMap<>();
        for(int i=0;i<raw.length-1;i++) {
            int at=raw[i].indexOf('=');require(at>0,"Invalid display field");
            String key=raw[i].substring(0,at),value=raw[i].substring(at+1);
            if(key.equals("line")) {
                require(text.size()<101,"Preview row cap exceeded");
                byte[] decoded;
                try {decoded=Base64.getDecoder().decode(value);}catch(IllegalArgumentException bad){throw invalid("Invalid base64 preview");}
                require(Base64.getEncoder().encodeToString(decoded).equals(value),"Canonical base64 required");
                try {text.add(StandardCharsets.UTF_8.newDecoder().onMalformedInput(CodingErrorAction.REPORT).onUnmappableCharacter(CodingErrorAction.REPORT).decode(ByteBuffer.wrap(decoded)).toString());}
                catch(CharacterCodingException bad){throw invalid("Invalid UTF-8 preview");}
            } else if(key.equals("reply")) {require(reply.size()<100,"Reply cap exceeded");reply.add(value);}
            else if(key.equals("chat_unread")) {
                String[] parts=value.split("\\|",-1);require(parts.length==2&&counts.size()<100,"Chat metadata cap/shape invalid");
                require(counts.putIfAbsent(uuid(parts[0]),integer(parts[1],10000))==null,"Duplicate chat count");
            } else {
                require(SCALARS.contains(key)&&fields.putIfAbsent(key,value)==null,"Unknown/duplicate display field");
            }
        }
        return new DisplayFrame(fields,text,reply,counts);
    }

    public String badge() {return total==null?"?":total==0?"":total>99?"99+":total.toString();}

    /** Caller supplies ONLY events proven displayed by a separately reviewed native adapter. */
    public byte[] receipt(List<String> events,String observedSession,String request) {
        require(chat!=null&&runtime!=null&&events!=null&&events.size()>=1&&events.size()<=100,"Receipt needs 1..100 explicit displayed events");
        uuid(observedSession);uuid(request);
        Map<String,Reply> issued=new HashMap<>();for(Reply reply:replies.values())issued.put(reply.event(),reply);
        StringBuilder body=new StringBuilder("protocol=3\nepoch=").append(epoch).append("\nframe=").append(frame)
            .append("\nruntime=").append(runtime).append("\nchat=").append(chat).append("\nrequest=").append(request)
            .append("\nobserved_session=").append(observedSession).append('\n');
        for(String event:events) {
            Reply reply=issued.get(uuid(event));require(reply!=null&&reply.observedSession().equals(observedSession),"Event not issued in this observed session");
            body.append("event=").append(event).append('\n');
        }
        byte[] raw=body.toString().getBytes(StandardCharsets.US_ASCII);require(raw.length<=16384,"Receipt budget exceeded");return raw;
    }

    private static String uuid(String value) {
        try {require(value!=null&&UUID.fromString(value).toString().equals(value),"Canonical UUID required");}
        catch(IllegalArgumentException bad){throw invalid("Canonical UUID required");}
        return value;
    }
    private static int integer(String value,int maximum) {
        require(value!=null&&value.matches("0|[1-9][0-9]{0,4}"),"Canonical bounded count/index required");
        int number=Integer.parseInt(value);require(number<=maximum,"Count/index exceeds bounds");return number;
    }
    private static boolean bool(String value) {require("true".equals(value)||"false".equals(value),"Explicit boolean required");return value.equals("true");}
    private static void require(boolean ok,String message) {if(!ok)throw invalid(message);}
    private static IllegalArgumentException invalid(String message) {return new IllegalArgumentException(message);}
}
