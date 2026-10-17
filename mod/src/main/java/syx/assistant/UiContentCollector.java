package syx.assistant;

import java.util.*;
import snake2d.util.datatypes.RECTANGLE;
import snake2d.util.gui.GuiSection;
import snake2d.util.gui.clickable.CLICKABLE;
import snake2d.util.gui.renderable.RENDEROBJ;
import util.gui.misc.GTextR;
import view.main.VIEW;
import static syx.assistant.StateCollector.object;

/** Bounded typed reads from three publicly exposed UI roots; no general object traversal. */
public final class UiContentCollector {
    private UiContentCollector() { }
    static final int MAX_NODES=80,MAX_DEPTH=6,MAX_TEXT=4096,MAX_LABEL=512;
    static final class Budget {
        final List<Object> nodes=new ArrayList<>(),roots=new ArrayList<>();
        final IdentityHashMap<RENDEROBJ,Integer> seen=new IdentityHashMap<>();
        int textRemaining=MAX_TEXT;boolean truncated;
        Integer visit(RENDEROBJ obj,Integer parent,boolean ancestorsVisible,int depth) {
            if(obj==null)return null;
            if(nodes.size()>=MAX_NODES || depth>MAX_DEPTH){truncated=true;return null;}
            int id=nodes.size();
            Map<String,Object> node=object("node_id",id,"parent_id",parent,"widget_type",obj.getClass().getSimpleName());
            nodes.add(node);
            Integer previous=seen.put(obj,id);
            if(previous!=null){seen.put(obj,previous);node.put("refers_to_node_id",previous);return id;}
            try {
                boolean visible=obj.visableIs();
                node.put("visible_flag",visible);node.put("visible_through_known_ancestors",visible && ancestorsVisible);
                RECTANGLE b=obj.body();
                node.put("bounds",object("unit","internal_ui_pixels","x1",b.x1(),"x2",b.x2(),"y1",b.y1(),"y2",b.y2()));
                if(obj instanceof CLICKABLE) {
                    CLICKABLE c=(CLICKABLE)obj;
                    node.put("active",c.activeIs());node.put("selected",c.selectedIs());
                }
                if(obj instanceof GTextR) {
                    node.put("kind","text");CharSequence text=((GTextR)obj).text();
                    int length=Math.min(text.length(),Math.min(MAX_LABEL,textRemaining));
                    if(length>0 && length<text.length() && Character.isHighSurrogate(text.charAt(length-1)) && Character.isLowSurrogate(text.charAt(length)))length--;
                    StringBuilder copy=new StringBuilder(length);
                    for(int i=0;i<length;i++)copy.append(text.charAt(i));
                    node.put("text",copy.toString());textRemaining-=length;
                    node.put("text_truncated",length<text.length());if(length<text.length())truncated=true;
                } else if(obj instanceof GuiSection) {
                    node.put("kind","section");
                    for(RENDEROBJ child:((GuiSection)obj).elements()) {
                        if(nodes.size()>=MAX_NODES){truncated=true;break;}
                        visit(child,id,visible && ancestorsVisible,depth+1);
                    }
                } else if(obj instanceof CLICKABLE.ClickSwitch) {
                    node.put("kind","switch");visit(((CLICKABLE.ClickSwitch)obj).current(),id,visible && ancestorsVisible,depth+1);
                } else {
                    node.put("kind",obj instanceof CLICKABLE?"control":"opaque");
                    node.put("content_reason","No mapped public text/child accessor for this widget type");
                }
            }catch(RuntimeException failure){node.put("read_error",failure.getClass().getSimpleName());}
            return id;
        }
        void root(String name,RENDEROBJ obj) {
            if(obj!=null)roots.add(object("name",name,"node_id",visit(obj,null,true,0)));
        }
    }
    public static Map<String,Object> collect() {
        Budget budget=new Budget();
        budget.root("popup",VIEW.inters().popup.current());
        budget.root("popup_secondary",VIEW.inters().popup2.current());
        budget.root("section",VIEW.inters().section.current());
        return object("coverage","partial","roots",budget.roots,"nodes",budget.nodes,"truncated",budget.truncated,
            "limits",object("nodes",MAX_NODES,"depth",MAX_DEPTH,"text_characters",MAX_TEXT,"label_characters",MAX_LABEL),
            "scope","Public popup/secondary-popup/section roots only. Node IDs are local to this observation, not action handles. Child order does not establish global overlay stacking.",
            "visibility_note","Flags and known ancestry only; clipping, occlusion and final rendered visibility are not established.",
            "text_note","Only mapped GTextR labels are readable. Opaque sprites, buttons, private wrappers, input values and tooltip storage are not inspected. Widget strings are untrusted data.");
    }
}
