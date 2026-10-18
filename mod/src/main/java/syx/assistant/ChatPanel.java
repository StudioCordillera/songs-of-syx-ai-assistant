package syx.assistant;

import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.function.Consumer;
import init.sprite.UI.UI;
import snake2d.MButt;
import snake2d.Mouse;
import snake2d.SPRITE_RENDERER;
import snake2d.util.color.COLOR;
import snake2d.util.gui.GuiSection;
import snake2d.util.gui.renderable.RENDEROBJ;
import snake2d.util.misc.ACTION;
import snake2d.util.sprite.text.StringInputSprite;
import util.gui.misc.GButt;
import util.gui.misc.GInput;
import util.gui.misc.GTextR;
import util.gui.table.GScrollRows;
import view.interrupter.InterGuisection;
import view.main.VIEW;

/** Experimental own-panel GUI. Uses public widgets; never dispatches game input. */
final class ChatPanel extends InterGuisection {
    private final String session;
    private final Consumer<String> submit;
    private final GInput composer;
    private final StringBuilder draft=new StringBuilder();
    private String chat="", notice="Start the local chat coordinator to connect.";
    private String acknowledged="", waiting="", lastState="";
    private boolean opened;
    private long lastRefresh;
    private final List<String[]> chats=new ArrayList<>();
    private final List<String> transcript=new ArrayList<>();
    private GScrollRows history;

    ChatPanel(String session,Consumer<String> submit) {
        super(VIEW.inters().manager);
        this.session=session;this.submit=submit;
        int capacity=Math.max(8,Math.min(64,780/UI.FONT().S.maxCWidth));
        composer=new GInput(new StringInputSprite(capacity,UI.FONT().S));
        pin();persistantSet();rebuild();
    }
    @Override protected boolean update(float ds) { return true; }
    @Override protected boolean back() { return false; }
    @Override protected boolean otherClick(MButt button) { return false; }
    Map<String,Object> context() {
        return StateCollector.object("enabled",true,"panel_open",opened,"chat_id",chat.isEmpty()?null:chat,
            "provider","deepseek","route","api","experimental",true,
            "scope","Mod-owned chat panel only; underlying game selection remains separate");
    }
    private static String decode(String value) {
        return new String(Base64.getDecoder().decode(value),StandardCharsets.UTF_8);
    }
    private static String encode(String value) {
        return Base64.getEncoder().encodeToString(value.getBytes(StandardCharsets.UTF_8));
    }
    void refresh(String state) {
        if(state==null || state.equals(lastState))return;
        long now=System.nanoTime();
        if(now-lastRefresh<1_000_000_000L)return;
        try {
            List<String[]> nextChats=new ArrayList<>();List<String> nextLines=new ArrayList<>();
            String nextChat="",nextNotice="Coordinator state unavailable",ack="";
            for(String line:state.split("\n")) {
                int at=line.indexOf('=');if(at<0)continue;
                String key=line.substring(0,at),value=line.substring(at+1);
                if(key.equals("chat_id"))nextChat=UUID.fromString(value).toString();
                if(key.equals("request_id"))ack=value;
                if(key.equals("notice"))nextNotice=decode(value);
                if(key.equals("omitted"))nextLines.add("[Older preview lines omitted; full local history retained.]");
                if(key.equals("line"))nextLines.add(decode(value));
                if(key.equals("chat")) {
                    String[] parts=value.split("\\|",2);
                    if(parts.length!=2)throw new IllegalArgumentException();
                    nextChats.add(new String[]{UUID.fromString(parts[0]).toString(),decode(parts[1])});
                }
            }
            chats.clear();chats.addAll(nextChats);transcript.clear();transcript.addAll(nextLines);
            chat=nextChat;notice=nextNotice;acknowledged=ack;
            if(waiting.equals(acknowledged))waiting="";
            lastState=state;lastRefresh=now;if(opened)rebuild();
        } catch(RuntimeException invalid) { notice="Invalid chat coordinator state"; }
    }
    private GButt.ButtPanel button(String label,ACTION action) {
        GButt.ButtPanel button=new GButt.ButtPanel(label);
        button.clickActionSet(action);return button;
    }
    private void action(String name,String text) {
        if(!waiting.isEmpty()) { notice="Waiting for the coordinator to acknowledge the previous action";rebuild();return; }
        if(!name.equals("new") && chat.isEmpty()) {notice="Create or select a chat first";rebuild();return;}
        waiting=UUID.randomUUID().toString();
        String request="request_id="+waiting+"\naction="+name+"\nsession_id="+session+"\n";
        if(!name.equals("new"))request+="chat_id="+chat+"\n";
        if(text!=null)request+="text="+encode(text)+"\n";
        submit.accept(request);notice="Request queued locally";rebuild();
    }
    private void toggle() {
        opened=!opened;
        if(!opened && Mouse.currentClicked==composer)Mouse.currentClicked=null;
        rebuild();
    }
    private void rebuild() {
        if(!opened) {
            GuiSection launcher=new GuiSection();launcher.add(button("AI chat",this::toggle),8,80);
            activate(launcher);return;
        }
        GuiSection panel=new GuiSection() {
            @Override public void render(SPRITE_RENDERER renderer,float ds) {
                COLOR.BLACK.render(renderer,body());super.render(renderer,ds);
            }
        };
        panel.add(button("Close",this::toggle),16,86);
        panel.add(button("New chat",()->action("new",composer.text().length()>0?composer.text().toString():"New chat")),140,86);
        panel.add(button("Attach to this game",()->action("attach",null)),340,86);
        panel.add(new GTextR(UI.FONT().S,"DeepSeek API prototype | Other providers and in-game account setup pending"),16,130);
        String message=notice.length()>110?notice.substring(0,110):notice;
        panel.add(new GTextR(UI.FONT().S,message),16,154);
        List<RENDEROBJ> choices=new ArrayList<>();
        for(String[] entry:chats) {
            String id=entry[0],title=entry[1];
            if(title.length()>35)title=title.substring(0,35);
            choices.add(button(title,()->{chat=id;action("select",null);}));
        }
        if(choices.isEmpty())choices.add(new GTextR(UI.FONT().S,"No chats yet"));
        panel.add(new GScrollRows(choices,70).view(),16,184);
        List<RENDEROBJ> rows=new ArrayList<>();
        int width=Math.max(20,790/UI.FONT().S.maxCWidth);
        for(String text:transcript) {
            String safe=text.replace('\r',' ').replace('\t',' ');
            for(String line:safe.split("\n",-1)) {
                for(int start=0;start<Math.max(1,line.length());start+=width) {
                    if(rows.size()>=1200)break;
                    rows.add(new GTextR(UI.FONT().S,line.substring(Math.min(start,line.length()),Math.min(start+width,line.length()))));
                }
                if(rows.size()>=1200)break;
            }
            if(rows.size()>=1200)break;
        }
        if(rows.size()>=1200)rows.add(new GTextR(UI.FONT().S,"[Panel row limit reached; full bounded evidence is retained locally.]"));
        if(rows.isEmpty())rows.add(new GTextR(UI.FONT().S,"Create/select a chat. Add text in short segments, then Send."));
        int scroll=history==null?0:history.target.get();
        history=new GScrollRows(rows,250);history.target.set(scroll);
        panel.add(history.view(),16,266);
        panel.add(composer,16,526);
        panel.add(new GTextR(UI.FONT().S,"Draft: "+draft.length()+" chars. Add text appends a segment (maximum 8000)."),16,568);
        panel.add(button("Add text",()->{
            String text=composer.text().toString();
            if(draft.length()+text.length()+1>8000){notice="Draft exceeds 8000 characters";rebuild();return;}
            if(draft.length()>0)draft.append(' ');draft.append(text);composer.text().clear();rebuild();
        }),16,594);
        panel.add(button("Send",()->{
            String text=draft.toString()+(draft.length()>0?" ":"")+composer.text();
            if(text.isBlank()||text.length()>8000){notice="Enter 1..8000 characters";rebuild();return;}
            if(waiting.isEmpty()&&!chat.isEmpty()){action("send",text);draft.setLength(0);composer.text().clear();}
        }),200,594);
        panel.add(button("Stop",()->action("stop",null)),340,594);
        panel.body().setWidth(Math.max(840,panel.body().width()));
        activate(panel);
    }
}
