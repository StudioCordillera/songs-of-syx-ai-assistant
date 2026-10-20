package syx.assistant.candidate;

import java.util.*;

/** Developer-only conservative display policy; caller must establish the native visibility gate.
 * One paint must cover every segment of an issued reply. Scrolling/repainting does not accumulate
 * read evidence. This deliberately leaves oversized/partly visible answers unread.
 */
public final class DisplayCoverage {
    public enum Gate { VISIBLE, CLOSED, HIDDEN, OTHER_CHAT, OBSCURED, UNKNOWN }
    private DisplayFrame frame;
    private String layout;
    private boolean painting;
    private final Map<String,Integer> segments=new HashMap<>();
    private final Map<String,BitSet> painted=new HashMap<>();

    /** Exact wrapped layout supplied by detached own-text layout, never by model-generated metadata. */
    public void layout(DisplayFrame next,String revision,Map<String,Integer> counts) {
        clear();frame=null;layout=null;segments.clear();
        if(next==null||revision==null||revision.isBlank()||revision.length()>128||counts==null||counts.size()>100)
            throw new IllegalArgumentException("Bounded frame/layout required");
        Map<String,DisplayFrame.Reply> issued=new HashMap<>();
        for(DisplayFrame.Reply reply:next.replies.values())issued.put(reply.event(),reply);
        int total=0;
        for(Map.Entry<String,Integer> entry:counts.entrySet()) {
            Integer count=entry.getValue();
            if(!issued.containsKey(entry.getKey())||count==null||count<1||count>4096||(total+=count)>4096)
                throw new IllegalArgumentException("Only bounded issued reply segments allowed");
        }
        segments.putAll(counts);frame=next;layout=revision;
    }

    public void beginPaint(String epoch,String nonce,String revision,String selectedChat,String activeRuntime,Gate gate) {
        clear();
        painting=frame!=null&&gate==Gate.VISIBLE&&frame.total!=null&&frame.chat!=null&&frame.runtime!=null
            &&frame.epoch.equals(epoch)&&frame.frame.equals(nonce)&&layout.equals(revision)
            &&frame.chat.equals(selectedChat)&&frame.runtime.equals(activeRuntime);
    }

    /** Called only for a fully clipped-in, unobscured segment actually rendered in this paint. */
    public void segment(String event,int index) {
        if(!painting)return;
        Integer count=segments.get(event);
        if(count==null||index<0||index>=count) {clear();throw new IllegalArgumentException("Segment outside issued layout");}
        painted.computeIfAbsent(event,key->new BitSet(count)).set(index);
    }

    /** End current paint; returned IDs are candidates, not receipts or persisted read state. */
    public List<String> finishPaint() {
        List<String> complete=new ArrayList<>();
        if(painting)for(Map.Entry<String,BitSet> entry:painted.entrySet())
            if(entry.getValue().cardinality()==segments.get(entry.getKey()))complete.add(entry.getKey());
        Collections.sort(complete);clear();return List.copyOf(complete);
    }
    public void cancel() {clear();}
    private void clear() {painting=false;painted.clear();}
}
