package syx.assistant;

import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.util.*;
import java.util.function.Consumer;
import java.util.concurrent.atomic.AtomicLong;
import init.sprite.UI.UI;
import snake2d.MButt;
import snake2d.CORE;
import snake2d.util.datatypes.COORDINATE;
import snake2d.util.gui.clickable.CLICKABLE;
import syx.assistant.candidate.GestureReducer;
import syx.assistant.candidate.PanelPreferences;
import syx.assistant.candidate.PanelTheme;
import snake2d.Mouse;
import snake2d.SPRITE_RENDERER;
import snake2d.util.color.COLOR;
import snake2d.util.color.ColorImp;
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

/** DEVELOPER ONLY: actual simple chat with own bounded layout/gesture adapter. No game actions or receipts. */
final class ChatPanel extends InterGuisection {
    private final GestureReducer gesture=new GestureReducer();
    private GestureReducer.Rect panelRect=new GestureReducer.Rect(24,40,840,640);
    private GestureReducer.Rect launcherRect=new GestureReducer.Rect(8,80,112,36);
    private Object gestureScene;
    private int textWidth=804;
    private int layoutWidth,layoutHeight;
    private Path preferencesDirectory;
    private String layoutNotice="";
    private PanelTheme theme=PanelTheme.preset("Forest");
    private final ColorImp panelColor=new ColorImp(),accentColor=new ColorImp(),bodyInk=new ColorImp(),accentInk=new ColorImp();
    private final GInput accentInput;
    private boolean appearanceOpen;
    private String appearanceNotice="";
    private String lastSubmitted="";
    private final AtomicLong candidateDraws=new AtomicLong();
    private final EnumMap<GestureReducer.Target,CLICKABLE> handles=new EnumMap<>(GestureReducer.Target.class);
    private final boolean advanced=Boolean.getBoolean("syx.assistant.chat.advanced");
    private final String session;
    private final Consumer<String> submit;
    private final GInput composer;
    private final StringBuilder draft=new StringBuilder();
    private String attachedSession="";
    private String chat="", notice="Start the local chat coordinator to connect.";
    private String acknowledged="", waiting="", lastState="";
    private boolean opened,running,deleteArmed;
    private boolean currentOnly=true;
    private int protocol;
    private String currentListSession="";
    private long lastSync;
    private long heartbeat;
    private String connection="Coordinator not connected",provider="deepseek",route="api",model="deepseek-v4-pro";
    private long lastRefresh;
    private final List<String[]> chats=new ArrayList<>();
    private final List<String[]> currentChats=new ArrayList<>();
    private final LinkedHashMap<String,String[]> drafts=new LinkedHashMap<>();
    private final List<String> transcript=new ArrayList<>();
    private GScrollRows history;
    private final Map<String,CLICKABLE> candidateButtons=new HashMap<>();

    ChatPanel(String session,Consumer<String> submit) {
        super(VIEW.inters().manager);
        if(advanced)throw new IllegalArgumentException("Developer layout supports only the simple player interface");
        this.session=session;this.submit=message->{lastSubmitted=message;submit.accept(message);};
        int capacity=Math.max(8,Math.min(64,780/UI.FONT().S.maxCWidth));
        StringInputSprite input=advanced?new StringInputSprite(capacity,UI.FONT().S):new StringInputSprite(241,UI.FONT().S) {
            @Override public int width(){return textWidth;}
            @Override public int height(){return UI.FONT().S.height()*4;}
            @Override public void render(SPRITE_RENDERER renderer,int x1,int x2,int y1,int y2) {
                String text=text().toString();
                int cursor=Math.max(0,Math.min(marker,text.length()));
                if(listening())text=text.substring(0,cursor)+"|"+text.substring(cursor);
                UI.FONT().S.render(renderer,text,x1,y1,textWidth,1.0);
            }
        };
        composer=new GInput(input);
        accentInput=new GInput(new StringInputSprite(8,UI.FONT().S));accentInput.text().add(theme.accentHex());
        refreshColors();
        if(!advanced)((snake2d.util.datatypes.Rec)composer.body()).setWidth(792);
        layoutWidth=CORE.getGraphics().nativeWidth;layoutHeight=CORE.getGraphics().nativeHeight;
        pin();persistantSet();rebuild();
        // Developer-only startup seam; the fixed runner supplies a private runtime directory.
        String candidateDirectory=System.getProperty("syx.assistant.candidate.preferencesDirectory");
        if(candidateDirectory!=null)configureCandidatePreferences(Path.of(candidateDirectory));
    }
    @Override protected boolean update(float ds) {
        reconcileViewport(CORE.getGraphics().nativeWidth,CORE.getGraphics().nativeHeight);
        if(gesture.isCapturing()) {
            COORDINATE p=CORE.getInput().getMouse().getCoo();
            sampleGesture(p.x(),p.y(),System.nanoTime()/1_000_000.0,MButt.LEFT.isDown());
        }
        return true;
    }
    private void releaseOwnComposer(){if(Mouse.currentClicked==composer||Mouse.currentClicked==accentInput)Mouse.currentClicked=null;}
    @Override protected void deactivateAction(){gesture.cancel();releaseOwnComposer();super.deactivateAction();}
    private int vw(){return layoutWidth;}
    private int vh(){return layoutHeight;}
    // Owned layout transition; update supplies public internal dimensions. Fixtures may supply dimensions,
    // without changing engine graphics/window state. Invalid/minimized geometry is not accepted.
    boolean reconcileViewport(int width,int height){
        if(width<=0||height<=0){gesture.cancel();return false;}
        if(width==layoutWidth&&height==layoutHeight)return false;
        gesture.cancel();layoutWidth=width;layoutHeight=height;rebuild();return true;
    }
    private GestureReducer.Rect fitPanel(GestureReducer.Rect r){
        return new GestureReducer.Rect(r.x,r.y,Math.max(640,r.width),Math.max(560,r.height)).fit(vw(),vh());
    }
    private boolean surfaceAvailable(){return isActivated()&&!VIEW.hideUI()&&vw()>=640&&vh()>=560;}
    private final class Handle extends CLICKABLE.ClickableAbs {
        private final GestureReducer.Target target;private final GTextR label;
        Handle(GestureReducer.Target target,String text,int width,int height){
            this.target=target;label=new GTextR(UI.FONT().S,text);body.setWidth(width).setHeight(height);handles.put(target,this);
        }
        @Override protected void clickA(){
            COORDINATE p=CORE.getInput().getMouse().getCoo();
            beginGesture(target,p.x(),p.y(),System.nanoTime()/1_000_000.0);
        }
        @Override protected void render(SPRITE_RENDERER r,float ds,boolean active,boolean selected,boolean hovered){
            candidateDraws.incrementAndGet();accentColor.render(r,body);label.text().color(accentInk);label.body().moveX1Y1(body);label.render(r,ds);
        }
    }
    // Own supplied-primitives seam for fixed copied-game fixtures, never an MCP/game action.
    boolean beginGesture(GestureReducer.Target target,double x,double y,double at){
        CLICKABLE handle=handles.get(target);
        if(!surfaceAvailable()||gesture.isCapturing()||handle==null||!Double.isFinite(x)||!Double.isFinite(y)||!Double.isFinite(at))return false;
        if(x<handle.body().x1()||x>=handle.body().x2()||y<handle.body().y1()||y>=handle.body().y2())return false;
        if(opened?target!=GestureReducer.Target.header&&target!=GestureReducer.Target.resize:target!=GestureReducer.Target.launcher)return false;
        gestureScene=VIEW.current();gesture.begin(target,x,y,at,opened?panelRect:launcherRect,vw(),vh());return true;
    }
    String sampleGesture(double x,double y,double at,boolean held){
        GestureReducer.Result r=gesture.sample(x,y,at,held,surfaceAvailable()&&VIEW.current()==gestureScene,vw(),vh());
        if(r.rect!=null){
            if(opened){
                GestureReducer.Rect before=panelRect;panelRect=fitPanel(r.rect);
                if(before.width!=panelRect.width||before.height!=panelRect.height)rebuild(true);
                else current().body().moveX1Y1((int)panelRect.x,(int)panelRect.y);
            }else{launcherRect=r.rect;current().body().moveX1Y1((int)r.rect.x,(int)r.rect.y);}
        }
        if(r.status.equals("dropped")&&preferencesDirectory!=null){saveCandidatePreferences();rebuild();}
        if(r.status.equals("toggle"))toggle();
        return r.status;
    }
    void resetCandidateLayout(){gesture.cancel();panelRect=fitPanel(new GestureReducer.Rect(24,40,840,640));launcherRect=new GestureReducer.Rect(8,80,112,36).fit(vw(),vh());saveCandidatePreferences();rebuild();}
    // Explicit caller-owned candidate directory; no default player path or history migration.
    boolean configureCandidatePreferences(Path directory){
        try{
            PanelPreferences saved=PanelPreferences.load(directory);
            preferencesDirectory=directory;
            if(saved!=null){
                gesture.cancel();panelRect=fitPanel(saved.panel);launcherRect=saved.launcher.fit(vw(),vh());
                if(saved.theme!=null){theme=saved.theme;accentInput.text().clear().add(theme.accentHex());refreshColors();}
            }
            layoutNotice="";appearanceNotice="";rebuild();return true;
        }catch(Exception error){layoutNotice="Layout preferences unavailable; current layout retained";rebuild();return false;}
    }
    private boolean saveCandidatePreferences(){
        if(preferencesDirectory==null)return false;
        try{new PanelPreferences(panelRect,launcherRect,theme).save(preferencesDirectory);layoutNotice="";return true;}
        catch(Exception error){layoutNotice="Layout or style changed for this run; preferences could not be saved";return false;}
    }
    private static void color(ColorImp out,int rgb){out.set(PanelTheme.engineChannel((rgb>>16)&255),PanelTheme.engineChannel((rgb>>8)&255),PanelTheme.engineChannel(rgb&255));}
    private void refreshColors(){color(panelColor,theme.background);color(accentColor,theme.accent);color(bodyInk,theme.bodyText);color(accentInk,theme.accentText);}
    private GTextR label(String text){GTextR result=new GTextR(UI.FONT().S,text);result.text().color(bodyInk);return result;}
    private void addWrappedLabels(List<RENDEROBJ> rows,String text,int chars){
        for(int start=0;start<text.length();start+=chars)rows.add(label(text.substring(start,Math.min(start+chars,text.length()))));
    }
    private void chooseTheme(String name){theme=PanelTheme.preset(name);accentInput.text().clear().add(theme.accentHex());refreshColors();appearanceNotice=saveCandidatePreferences()?"Style saved":"Style changed for this run";rebuild();}
    private void applyAccent(){
        try{theme=theme.withAccent(accentInput.text().toString());refreshColors();appearanceNotice=saveCandidatePreferences()?"Style saved":"Style changed for this run";}
        catch(IllegalArgumentException error){appearanceNotice="Accent needs six hex digits, such as #87A68D";}
        rebuild();
    }
    PanelTheme candidateTheme(){return theme;}
    GInput candidateAccentInput(){return accentInput;}
    boolean candidateAppearanceOpen(){return appearanceOpen;}
    boolean candidatePreferencesConfigured(){return preferencesDirectory!=null;}
    GestureReducer.Rect candidatePanelLayout(){return panelRect;}
    boolean candidateCapturing(){return gesture.isCapturing();}
    GestureReducer.Rect candidateLayout(){return opened?panelRect:launcherRect;}
    CLICKABLE candidateHandle(GestureReducer.Target target){return handles.get(target);}
    String candidateLastSubmitted(){return lastSubmitted;}
    GInput candidateComposer(){return composer;}
    CLICKABLE candidateButton(String label){return candidateButtons.get(label);}
    List<String> candidateTranscript(){return List.copyOf(transcript);}
    long candidateDraws(){return candidateDraws.get();}
    @Override protected boolean back() { return false; }
    @Override protected boolean otherClick(MButt button) { return false; }
    Map<String,Object> context() {
        return StateCollector.object("candidate_layout",true,"enabled",true,"panel_open",opened,"chat_id",chat.isEmpty()?null:chat,
            "generating",running,"runtime_session_id",session,"attached_session_id",attachedSession.isEmpty()?null:attachedSession,
            "attachment_required",advanced&&!chat.isEmpty()&&!session.equals(attachedSession),
            "reconnect_on_send",!advanced&&!chat.isEmpty()&&!session.equals(attachedSession),
            "automatic_connection",!advanced,"coordinator_protocol",protocol,
            "action_pending",!waiting.isEmpty(),"all_listed_chat_count",chats.size(),
            "history_filter",!advanced&&currentOnly?"current_load":"all",
            "listed_chat_count",!advanced&&currentOnly?(session.equals(currentListSession)?currentChats.size():0):chats.size(),
            "provider",provider,"route",route,"model",model,"interface",advanced?"advanced":"simple","experimental",true,
            "scope","Mod-owned chat panel only; underlying game selection remains separate");
    }
    private static String decode(String value) {
        return new String(Base64.getDecoder().decode(value),StandardCharsets.UTF_8);
    }
    private static String encode(String value) {
        return Base64.getEncoder().encodeToString(value.getBytes(StandardCharsets.UTF_8));
    }
    void refresh(String state) {
        if(state==null)return;
        long now=System.nanoTime();
        if(now-lastRefresh<1_000_000_000L)return;
        if(state.equals(lastState)) {
            lastRefresh=now;
            if(heartbeat>0 && System.currentTimeMillis()-heartbeat>5000 && !connection.equals("Coordinator unavailable")) {
                connection="Coordinator unavailable";notice="Pending action status may be unknown; reconnect and inspect history before retrying";
                if(opened)rebuild();
            }
            return;
        }
        try {
            List<String[]> nextChats=new ArrayList<>(),nextCurrent=new ArrayList<>();List<String> nextLines=new ArrayList<>();
            String nextChat="",nextNotice="Coordinator state unavailable",ack="";
            String nextProvider=provider,nextModel=model,nextRoute=route,nextAttached="",nextConnection=connection,nextListSession="";
            boolean nextRunning=false;long nextHeartbeat=0;int nextProtocol=0;
            for(String line:state.split("\n")) {
                int at=line.indexOf('=');if(at<0)continue;
                String key=line.substring(0,at),value=line.substring(at+1);
                if(key.equals("protocol"))nextProtocol=Integer.parseInt(value);
                if(key.equals("provider"))nextProvider=value;
                if(key.equals("model"))nextModel=value;
                if(key.equals("route"))nextRoute=value;
                if(key.equals("session_id"))nextAttached=UUID.fromString(value).toString();
                if(key.equals("current_chat_session"))nextListSession=UUID.fromString(value).toString();
                if(key.equals("running")) {if(!value.equals("true")&&!value.equals("false"))throw new IllegalArgumentException();nextRunning=value.equals("true");}
                if(key.equals("updated_at")) {
                    double stamp=Double.parseDouble(value);if(!Double.isFinite(stamp)||stamp<=0||stamp>Long.MAX_VALUE/1000.0)throw new IllegalArgumentException();
                    nextHeartbeat=(long)(stamp*1000);
                }
                if(key.equals("connection_status"))nextConnection=decode(value);
                if(key.equals("chat_id"))nextChat=UUID.fromString(value).toString();
                if(key.equals("request_id"))ack=value;
                if(key.equals("notice"))nextNotice=decode(value);
                if(key.equals("omitted"))nextLines.add("[Older preview lines omitted; full local history retained.]");
                if(key.equals("line"))nextLines.add(decode(value));
                if(key.equals("chat")||key.equals("current_chat")) {
                    String[] parts=value.split("\\|",2);
                    if(parts.length!=2)throw new IllegalArgumentException();
                    (key.equals("chat")?nextChats:nextCurrent).add(new String[]{UUID.fromString(parts[0]).toString(),decode(parts[1])});
                }
            }
            if(nextChats.size()>100||nextCurrent.size()>100||nextLines.size()>1000||nextHeartbeat==0)throw new IllegalArgumentException();
            if(nextProtocol!=1&&nextProtocol!=2)throw new IllegalArgumentException();
            if(nextProtocol!=2&&!advanced) {
                protocol=nextProtocol;notice="Update the mod and chat helper together to connect automatically";
                lastRefresh=now;if(opened)rebuild();return;
            }
            boolean contentChanged=!chat.equals(nextChat)||!notice.equals(nextNotice)||!connection.equals(nextConnection)||running!=nextRunning||protocol!=nextProtocol
                ||!provider.equals(nextProvider)||!model.equals(nextModel)||!route.equals(nextRoute)||!attachedSession.equals(nextAttached)||!currentListSession.equals(nextListSession)
                ||!Arrays.deepEquals(chats.toArray(),nextChats.toArray())||!Arrays.deepEquals(currentChats.toArray(),nextCurrent.toArray())||!transcript.equals(nextLines);
            chats.clear();chats.addAll(nextChats);currentChats.clear();currentChats.addAll(nextCurrent);transcript.clear();transcript.addAll(nextLines);
            if(!chat.equals(nextChat)) {
                String[] initial=chat.isEmpty()?new String[]{draft.toString(),composer.text().toString()}:null;
                if(!chat.isEmpty())drafts.put(chat,new String[]{draft.toString(),composer.text().toString()});
                while(drafts.size()>100)drafts.remove(drafts.keySet().iterator().next());
                history=null;deleteArmed=false;draft.setLength(0);composer.text().clear();
                String[] saved=drafts.get(nextChat);if(saved==null)saved=initial;
                if(saved!=null){draft.append(saved[0]);composer.text().add(saved[1]);}
            }
            protocol=nextProtocol;provider=nextProvider;model=nextModel;route=nextRoute;attachedSession=nextAttached;
            connection=nextConnection;heartbeat=nextHeartbeat;running=nextRunning;currentListSession=nextListSession;
            chat=nextChat;notice=nextNotice;acknowledged=ack;
            if(waiting.equals(acknowledged))waiting="";
            lastState=state;lastRefresh=now;if(opened&&contentChanged)rebuild();
            if(opened&&!advanced&&chat.isEmpty()&&waiting.isEmpty()&&now-lastSync>5_000_000_000L)sync();
        } catch(RuntimeException invalid) { notice="Invalid chat coordinator state"; }
    }
    private GButt.ButtPanel button(String label,ACTION action) {
        GButt.ButtPanel button=new GButt.ButtPanel(label);
        button.clickActionSet(action);candidateButtons.put(label,button);return button;
    }
    private boolean action(String name,String text) {return action(name,text,null,null,null);}
    private boolean action(String name,String text,String selectedProvider,String selectedRoute,String selectedModel) {return action(name,text,selectedProvider,selectedRoute,selectedModel,null);}
    private boolean action(String name,String text,String selectedProvider,String selectedRoute,String selectedModel,String targetChat) {
        if(!advanced&&protocol!=2){notice=protocol==0?"Start the local chat helper to connect.":"Update the mod and chat helper together";rebuild();return false;}
        long age=System.currentTimeMillis()-heartbeat;
        if(heartbeat==0 || age>5000 || age< -5000) {notice="Coordinator unavailable; reconnect before sending an action";rebuild();return false;}
        if(!waiting.isEmpty()) { notice="Waiting for the coordinator to acknowledge the previous action";rebuild();return false; }
        String target=targetChat==null?chat:targetChat;
        if(!name.equals("new")&&!name.equals("sync") && target.isEmpty()) {notice="Connecting to this game; please wait";rebuild();return false;}
        waiting=UUID.randomUUID().toString();
        String request="request_id="+waiting+"\naction="+name+"\nsession_id="+session+"\n";
        if(!advanced)request+="protocol=2\n";
        if(!name.equals("new")&&!name.equals("sync"))request+="chat_id="+target+"\n";
        if(selectedProvider!=null)request+="provider="+selectedProvider+"\nroute="+selectedRoute+"\nmodel="+selectedModel+"\n";
        if(text!=null)request+="text="+encode(text)+"\n";
        submit.accept(request);notice="Request queued locally";rebuild();return true;
    }
    private void sync(){lastSync=System.nanoTime();action("sync",null);}
    private void toggle() {
        gesture.cancel();opened=!opened;
        if(!opened)releaseOwnComposer();
        rebuild();
        if(opened&&!advanced&&waiting.isEmpty())sync();
    }
    private void rebuild(){rebuild(false);}
    private void rebuild(boolean preserveCapture) {
        if(!preserveCapture)gesture.cancel();
        candidateButtons.clear();handles.clear();launcherRect=launcherRect.fit(vw(),vh());panelRect=fitPanel(panelRect);
        if(!opened||vw()<640||vh()<560) {
            opened=false;releaseOwnComposer();
            GuiSection launcher=new GuiSection();
            launcher.add(new Handle(GestureReducer.Target.launcher,"AI chat",(int)launcherRect.width,(int)launcherRect.height),0,0);
            launcher.body().setWidth((int)launcherRect.width).setHeight((int)launcherRect.height).moveX1Y1((int)launcherRect.x,(int)launcherRect.y);
            activate(launcher);return;
        }
        int w=(int)panelRect.width,h=(int)panelRect.height;
        textWidth=w-36;((snake2d.util.datatypes.Rec)composer.body()).setWidth(textWidth+12);
        int composerY=h-48-(UI.FONT().S.height()+8)-composer.body().height();
        GuiSection panel=new GuiSection() {
            @Override public void render(SPRITE_RENDERER renderer,float ds) {
                panelColor.render(renderer,body());super.render(renderer,ds);
            }
        };
        panel.add(new Handle(GestureReducer.Target.header,"AI chat — drag header",w,28),0,0);
        panel.add(button("Close",this::toggle),12,40);
        panel.add(button("Reset layout",this::resetCandidateLayout),410,40);
        panel.add(button(advanced?"New DeepSeek":"New chat",()->action("new","New chat","deepseek","api","deepseek-v4-pro")),132,40);
        if(advanced)panel.add(button("Use with this game",()->action("attach",null)),340,86);
        if(!advanced)panel.add(button(currentOnly?"This load":"All chats",()->{currentOnly=!currentOnly;rebuild();}),280,40);
        if(advanced)panel.add(button("Evidence",()->action("evidence",null)),650,86);
        panel.add(button("Style",()->{appearanceOpen=!appearanceOpen;if(!appearanceOpen&&Mouse.currentClicked==accentInput)Mouse.currentClicked=null;rebuild();}),12,80);
        panel.add(label(advanced?connection+" | "+model:"DeepSeek Pro"+(running?" — Thinking…":"")),140,84);
        boolean reconnectHint=notice.equals("Connected to this game; ask a question")||notice.equals("History loaded; your next question uses the loaded game");
        String hint=!advanced&&protocol==2&&reconnectHint&&!chat.isEmpty()&&!attachedSession.equals(session)?"Your next question connects this chat to the loaded game. Earlier messages stay historical.":notice;
        if(appearanceOpen&&!appearanceNotice.isEmpty())hint=appearanceNotice;
        if(!layoutNotice.isEmpty())hint=layoutNotice;
        int hintChars=Math.max(1,textWidth/UI.FONT().S.maxCWidth);
        String message=hint.length()>hintChars?hint.substring(0,hintChars):hint;
        panel.add(label(message),12,112);
        List<RENDEROBJ> choices=new ArrayList<>();
        for(String[] entry:!advanced&&currentOnly?(session.equals(currentListSession)?currentChats:Collections.<String[]>emptyList()):chats) {
            String id=entry[0],title=entry[1];
            if(title.length()>35)title=title.substring(0,35);
            choices.add(button(title,()->action("select",null,null,null,null,id)));
        }
        if(choices.isEmpty())choices.add(label("No chats yet"));
        if(appearanceOpen){
            panel.add(button("Forest",()->chooseTheme("Forest")),12,142);
            panel.add(button("Parchment",()->chooseTheme("Parchment")),150,142);
            panel.add(button("Night",()->chooseTheme("Night")),320,142);
            panel.add(accentInput,12,180);panel.add(button("Apply accent",this::applyAccent),160,180);
            panel.add(label(preferencesDirectory==null?"#RRGGBB · this run":"#RRGGBB · local"),350,184);
        }else panel.add(new GScrollRows(choices,70).view(),12,142);
        List<RENDEROBJ> rows=new ArrayList<>();
        int width=Math.max(20,textWidth/UI.FONT().S.maxCWidth);
        for(String text:transcript) {
            String safe=text.replace('\r',' ').replace('\t',' ');
            for(String line:safe.split("\n",-1)) {
                for(int start=0;start<Math.max(1,line.length());start+=width) {
                    if(rows.size()>=1200)break;
                    rows.add(label(line.substring(Math.min(start,line.length()),Math.min(start+width,line.length()))));
                }
                if(rows.size()>=1200)break;
            }
            if(rows.size()>=1200)break;
        }
        if(rows.size()>=1200)addWrappedLabels(rows,"[Panel row limit reached; full bounded evidence is retained locally.]",width);
        if(rows.isEmpty())addWrappedLabels(rows,advanced?"Create/select a chat. Add text in short segments, then Send.":"Ask a question about your game. The connection is handled automatically.",width);
        boolean follow=history==null || history.target.get()>=history.target.max();
        int scroll=follow?Integer.MAX_VALUE:history.target.get();
        history=new GScrollRows(rows,Math.max(20,composerY-12-220));history.target.set(scroll);
        panel.add(history.view(),12,220);
        panel.add(composer,12,composerY);
        if(advanced) {
        panel.add(new GTextR(UI.FONT().S,"Draft: "+draft.length()+" chars. Add text appends a segment (maximum 8000)."),16,568);
        panel.add(button("Rename",()->action("rename",composer.text().toString())),16,640);
        panel.add(button("Export",()->action("export",null)),200,640);
        panel.add(button(deleteArmed?"Confirm delete":"Delete chat",()->{
            if(!deleteArmed){deleteArmed=true;notice="Click Confirm delete to remove this chat. Exported files are retained.";rebuild();}
            else {action("delete",null);deleteArmed=false;}
        }),340,640);
        panel.add(button("New Claude API",()->action("new",composer.text().length()>0?composer.text().toString():"Claude API chat","claude","api","haiku")),650,594);
        panel.add(button("New Claude plan",()->action("new",composer.text().length()>0?composer.text().toString():"Claude chat","claude","subscription","haiku")),650,640);
        panel.add(button("Add text",()->{
            String text=composer.text().toString();
            if(draft.length()+text.length()+1>8000){notice="Draft exceeds 8000 characters";rebuild();return;}
            if(draft.length()>0)draft.append(' ');draft.append(text);composer.text().clear();rebuild();
        }),16,594);
        } else panel.add(label("240 characters · Send / Stop"),12,composerY+composer.body().height()+4);
        panel.add(button("Send",()->{
            if(advanced&&!attachedSession.equals(session)){notice="Use with this game before sending in the advanced interface.";rebuild();return;}
            if(running){notice="Stop or wait for the current reply before sending another message";rebuild();return;}
            String text=draft.toString()+(draft.length()>0?" ":"")+composer.text();
            if(text.isBlank()||text.length()>8000){notice="Enter 1..8000 characters";rebuild();return;}
            if(waiting.isEmpty()&&!chat.isEmpty()&&action("send",text)){draft.setLength(0);composer.text().clear();drafts.remove(chat);}
        }),132,h-40);
        panel.add(button("Stop",()->action("stop",null)),272,h-40);
        panel.add(new Handle(GestureReducer.Target.resize,"+",24,24),w-24,h-24);
        panel.body().setWidth(w).setHeight(h).moveX1Y1((int)panelRect.x,(int)panelRect.y);
        activate(panel);
    }
}
