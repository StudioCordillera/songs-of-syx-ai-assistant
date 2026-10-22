package syx.assistant;

import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import game.GAME;
import snake2d.CORE;
import snake2d.MButt;
import snake2d.Mouse;
import snake2d.util.sprite.text.StringInputSprite;
import init.sprite.UI.UI;
import snake2d.util.datatypes.Coo;
import snake2d.util.gui.clickable.CLICKABLE;
import snake2d.util.gui.renderable.RENDEROBJ;
import syx.assistant.candidate.GestureReducer;
import syx.assistant.candidate.PanelPreferences;
import util.gui.misc.GInput;
import view.main.VIEW;
import static syx.assistant.StateCollector.object;

/** TEST ONLY: overlay our actual ChatPanel; synthetic protocol data and owned gesture primitives. */
public final class ChatLayoutProbe {
    private static final String STATUS="Connection remains unavailable. ".repeat(4)+"Earlier Send outcome unknown; no automatic retry. Earlier reply interrupted; no automatic retry.";
    private static void require(boolean yes,String why){if(!yes)throw new IllegalStateException(why);}
    private static String b64(String value){return Base64.getEncoder().encodeToString(value.getBytes(StandardCharsets.UTF_8));}
    private static String field(String request,String key){for(String row:request.split("\n"))if(row.startsWith(key+"="))return row.substring(key.length()+1);throw new IllegalStateException("Missing own request field");}
    private static void press(CLICKABLE widget){
        require(widget!=null,"Missing own button");
        require(!VIEW.inters().manager.hover(new Coo(widget.body().cX(),widget.body().cY()),true),"Own hover escaped");
        require(!VIEW.inters().manager.click(MButt.LEFT),"Own button click escaped");
    }
    private static void bounds(ChatPanel p){bounds(p,CORE.getGraphics().nativeWidth,CORE.getGraphics().nativeHeight);}
    private static void bounds(ChatPanel p,int width,int height){
        var r=p.candidateLayout();var b=p.section().body();
        require(b.x1()==r.x&&b.y1()==r.y&&b.width()==r.width&&b.height()==r.height,"Own rectangle/body mismatch");
        require(b.x1()>=0&&b.y1()>=0&&b.x2()<=width&&b.y2()<=height,"Own surface outside viewport");
        for(RENDEROBJ child:p.section().elements())require(child.body().x1()>=b.x1()&&child.body().y1()>=b.y1()&&child.body().x2()<=b.x2()&&child.body().y2()<=b.y2(),"Own control outside panel: "+child.getClass().getSimpleName());
        if(Boolean.TRUE.equals(p.context().get("panel_open")))require(p.candidateComposer().body().width()==r.width-24,"Composer width not responsive");
    }
    private static void shortOpen(ChatPanel p,double t){
        var h=p.candidateHandle(GestureReducer.Target.launcher);
        require(h!=null&&p.beginGesture(GestureReducer.Target.launcher,h.body().cX(),h.body().cY(),t),"Begin own launcher");
        require(p.sampleGesture(h.body().cX(),h.body().cY(),t+1,false).equals("toggle"),"Short click must toggle");
        require(Boolean.TRUE.equals(p.context().get("panel_open")),"Panel did not open");bounds(p);
    }
    private static String frame(String session,String chat,String ack,boolean running,boolean answer){
        return "protocol=2\nupdated_at="+(System.currentTimeMillis()/1000.0)+"\nrequest_id="+ack+"\nchat_id="+chat+"\nsession_id="+session+"\ncurrent_chat_session="+session
            +"\nchat="+chat+"|"+b64("Fixture chat")+"\ncurrent_chat="+chat+"|"+b64("Fixture chat")+"\nprovider=deepseek\nroute=api\nmodel=deepseek-v4-pro\nrunning="+running
            +"\nnotice="+b64(STATUS)+"\nconnection_status="+b64("SIMULATED fixture helper")+"\nline="+b64("User: fixture layout question")
            +"\nline="+b64(answer?"Assistant: SIMULATED fixture answer; no real provider called.":"Assistant: original layout reference is synthetic fixture text, not a game observation.")+"\n";
    }
    public static void install(Path directory){
        VIEW.s().activate();GAME.SPEED.speedSet(0);
        int[] phase={0};long[] stamp={System.nanoTime()},draws={0};long start=System.nanoTime();String[] session={null},chat={UUID.randomUUID().toString()},ack={""};
        GInput[] input={null};List<String> checks=new ArrayList<>();String draft="Preserve this draft through drag and resize";
        GAME.addAfterUpdate(()->{
            try{
                if(System.nanoTime()-start>65_000_000_000L)throw new IllegalStateException("Chat layout fixture timeout");
                ChatPanel p=AssistantScript.currentChatPanel();if(p==null)return;
                switch(phase[0]){
                case 0:
                    require(Boolean.TRUE.equals(p.context().get("candidate_layout")),"Production class loaded instead of candidate overlay");
                    require(p.configureCandidatePreferences(directory),"Configure own preference directory");
                    session[0]=p.context().get("runtime_session_id").toString();p.refresh(frame(session[0],chat[0],ack[0],false,false));
                    shortOpen(p,0);ack[0]=field(p.candidateLastSubmitted(),"request_id");require(field(p.candidateLastSubmitted(),"action").equals("sync"),"Normal automatic connection request");
                    stamp[0]=System.nanoTime();phase[0]=1;return;
                case 1:
                    if(System.nanoTime()-stamp[0]<1_100_000_000L)return;
                    p.refresh(frame(session[0],chat[0],ack[0],false,false));require(Boolean.FALSE.equals(p.context().get("action_pending")),"Sync acknowledgement not applied");
                    input[0]=p.candidateComposer();input[0].text().clear().add(draft);
                    press(p.candidateButton("This load"));require(p.context().get("history_filter").equals("all"),"History filter failed");bounds(p);
                    require(p.candidateComposer()==input[0]&&input[0].text().toString().equals(draft),"Filter lost composer/draft");
                    stamp[0]=System.nanoTime();phase[0]=2;return;
                case 2:{
                    if(System.nanoTime()-stamp[0]<1_100_000_000L)return;
                    var h=p.candidateHandle(GestureReducer.Target.header);double x=h.body().x1()+20,y=h.body().y1()+10;
                    require(p.beginGesture(GestureReducer.Target.header,x,y,100),"Begin header");
                    p.refresh(frame(session[0],chat[0],ack[0],false,false));require(p.candidateCapturing(),"Heartbeat-only refresh cancelled capture");
                    require(p.sampleGesture(x+80,y+20,101,true).equals("dragging"),"Immediate header drag");p.sampleGesture(x+80,y+20,102,false);bounds(p);
                    require(p.candidateLayout().x==104&&p.candidateLayout().y==60,"Header displacement");checks.add("header_drag_and_heartbeat_stability");
                    var grip=p.candidateHandle(GestureReducer.Target.resize);x=grip.body().cX();y=grip.body().cY();
                    require(p.beginGesture(GestureReducer.Target.resize,x,y,200),"Begin grow");p.sampleGesture(x+60,y+40,201,true);p.sampleGesture(x+60,y+40,202,false);bounds(p);
                    require(p.candidateLayout().width==900&&p.candidateLayout().height==680,"Responsive grow");
                    grip=p.candidateHandle(GestureReducer.Target.resize);x=grip.body().cX();y=grip.body().cY();
                    require(p.beginGesture(GestureReducer.Target.resize,x,y,300),"Begin shrink");p.sampleGesture(x-600,y-400,301,true);p.sampleGesture(x-600,y-400,302,false);bounds(p);
                    require(p.candidateLayout().width==640&&p.candidateLayout().height==560,"Measured simple-control minimum");
                    require(input[0]==p.candidateComposer()&&input[0].text().toString().equals(draft),"Resize lost composer/draft");checks.add("responsive_minimum_controls_and_draft");
                    require(!p.beginGesture(GestureReducer.Target.chrome,120,200,400),"Content must not start a drag");checks.add("content_refuses_capture");
                    require(String.join("",p.candidateStatusRows()).equals(STATUS),"Status silently shortened at minimum");
                    require(p.candidateStatusRows().size()>1&&p.candidateStatusHistory().target.max()>0,"Long status must wrap and scroll");
                    p.candidateStatusHistory().target.set(p.candidateStatusHistory().target.max());bounds(p);
                    require(input[0]==p.candidateComposer()&&input[0].text().toString().equals(draft),"Status scrolling lost draft");
                    checks.add("wrapped_status_minimum_bounds_and_scroll");
                    String savedGeometry=Files.readString(directory.resolve("chat-layout.preferences"));
                    press(p.candidateButton("Style"));require(p.candidateAppearanceOpen(),"Style form did not open");
                    for(String preset:List.of("Forest","Parchment","Night")){
                        press(p.candidateButton(preset));bounds(p);require(p.candidateTheme().name.equals(preset),"Preset not applied");
                        List<CLICKABLE> form=List.of(p.candidateButton("Forest"),p.candidateButton("Parchment"),p.candidateButton("Night"),p.candidateAccentInput(),p.candidateButton("Apply accent"));
                        for(int i=0;i<form.size();i++){
                            var a=form.get(i).body();require(a.y2()<=p.section().body().y1()+250,"Style control overlaps transcript");
                            for(int j=i+1;j<form.size();j++){var b=form.get(j).body();require(a.x2()<=b.x1()||b.x2()<=a.x1()||a.y2()<=b.y1()||b.y2()<=a.y1(),"Style controls overlap");}
                        }
                        require(input[0]==p.candidateComposer()&&input[0].text().toString().equals(draft),"Style lost question draft");
                    }
                    checks.add("appearance_presets_minimum_bounds_and_draft");
                    var accent=p.candidateAccentInput();int previousAccent=p.candidateTheme().accent;String beforeInvalid=Files.readString(directory.resolve("chat-layout.preferences"));
                    accent.text().clear().add("ZZZZZZ");press(p.candidateButton("Apply accent"));require(p.candidateTheme().accent==previousAccent&&Files.readString(directory.resolve("chat-layout.preferences")).equals(beforeInvalid),"Invalid accent changed palette/file");
                    accent.text().clear().add("#abcdef");press(p.candidateButton("Apply accent"));bounds(p);
                    require(p.candidateTheme().accentHex().equals("#ABCDEF"),"Custom accent not applied");
                    var styled=PanelPreferences.load(directory);var previous=PanelPreferences.decode(savedGeometry.getBytes(StandardCharsets.US_ASCII));
                    require(new PanelPreferences(styled.panel,styled.launcher).encode().equals(new PanelPreferences(previous.panel,previous.launcher).encode()),"Style changed saved geometry");
                    require(styled.theme!=null&&styled.theme.name.equals("Night")&&styled.theme.accentHex().equals("#ABCDEF"),"Style did not persist");
                    accent.listen();press(p.candidateButton("Style"));require(!p.candidateAppearanceOpen()&&Mouse.currentClicked!=accent,"Closing Style retained own color focus");
                    require(input[0].text().toString().equals(draft),"Color input consumed question draft");checks.add("custom_accent_validation_and_focus_ownership");
                    ChatPanel restored=new ChatPanel(session[0],ignored->{});
                    try{
                        require(restored.candidateTheme().name.equals("Forest"),"Fresh panel default changed");
                        require(restored.configureCandidatePreferences(directory),"Fresh panel preference load failed");shortOpen(restored,450);
                        require(restored.candidateTheme().name.equals("Night")&&restored.candidateTheme().accentHex().equals("#ABCDEF"),"Fresh panel lost saved style");
                        require(restored.candidateLayout().width==640&&restored.candidateLayout().height==560&&restored.candidateComposer().text().length()==0,"Fresh panel geometry or nonpersisted draft policy");
                    }finally{restored.close();}
                    require(p.configureCandidatePreferences(directory)&&input[0].text().toString().equals(draft),"Restoring original panel lost draft");
                    checks.add("explicit_style_persistence_and_fresh_panel_reload");
                    draws[0]=p.candidateDraws();press(p.candidateButton("Send"));String request=p.candidateLastSubmitted();
                    require(field(request,"action").equals("send")&&new String(Base64.getDecoder().decode(field(request,"text")),StandardCharsets.UTF_8).equals(draft),"Normal Send framing/draft");
                    require(field(request,"chat_id").equals(chat[0])&&input[0].text().length()==0,"Send chat/draft acknowledgement policy");ack[0]=field(request,"request_id");checks.add("normal_send_protocol");
                    stamp[0]=System.nanoTime();phase[0]=3;return;}
                case 3:
                    if(System.nanoTime()-stamp[0]<1_100_000_000L)return;
                    require(p.candidateDraws()>draws[0],"Resized handles did not render across frames");
                    p.refresh(frame(session[0],chat[0],ack[0],true,false));press(p.candidateButton("Stop"));
                    require(field(p.candidateLastSubmitted(),"action").equals("stop"),"Normal Stop framing");ack[0]=field(p.candidateLastSubmitted(),"request_id");checks.add("normal_stop_protocol");
                    press(p.candidateButton("Close"));require(Boolean.FALSE.equals(p.context().get("panel_open")),"Close failed");bounds(p);
                    stamp[0]=System.nanoTime();phase[0]=4;return;
                case 4:
                    if(System.nanoTime()-stamp[0]<1_100_000_000L)return;
                    p.refresh(frame(session[0],chat[0],ack[0],false,true));shortOpen(p,500);ack[0]=field(p.candidateLastSubmitted(),"request_id");
                    require(p.context().get("chat_id").equals(chat[0])&&p.candidateTranscript().stream().anyMatch(t->t.contains("SIMULATED fixture answer")),"Reopen lost synthetic transcript/chat");checks.add("reopen_retains_transcript_and_chat");
                    press(p.candidateButton("Reset layout"));bounds(p);require(p.candidateLayout().width==840&&p.candidateLayout().height==640,"Reset failed");checks.add("explicit_layout_reset");
                    stamp[0]=System.nanoTime();phase[0]=5;return;
                case 5:{
                    if(System.nanoTime()-stamp[0]<1_100_000_000L)return;
                    p.refresh(frame(session[0],chat[0],ack[0],false,true));
                    input[0].text().clear().add(draft);
                    var saved=PanelPreferences.load(directory);require(saved!=null&&saved.panel.width==840&&saved.panel.height==640,"Explicit reset did not persist");
                    String bytes=Files.readString(directory.resolve("chat-layout.preferences"));
                    p.reconcileViewport(700,600);require(Files.readString(directory.resolve("chat-layout.preferences")).equals(bytes),"Automatic viewport clamp wrote preferences");
                    p.reconcileViewport(CORE.getGraphics().nativeWidth,CORE.getGraphics().nativeHeight);
                    require(p.configureCandidatePreferences(directory)&&p.candidateLayout().width==840&&p.candidateLayout().height==640,"Preference reload lost saved size");
                    require(input[0]==p.candidateComposer()&&input[0].text().toString().equals(draft),"Preference reload lost composer/draft");checks.add("explicit_preferences_save_reload");checks.add("automatic_clamp_does_not_write_preferences");
                    var before=p.candidateLayout();Files.writeString(directory.resolve("chat-layout.preferences"),"version=999\n");
                    require(!p.configureCandidatePreferences(directory)&&p.candidateLayout().width==before.width&&p.candidateLayout().height==before.height&&input[0].text().toString().equals(draft),"Malformed preferences changed layout/draft");
                    require(Files.readString(directory.resolve("chat-layout.preferences")).equals("version=999\n"),"Malformed input silently rewritten");
                    p.resetCandidateLayout();require(PanelPreferences.load(directory).panel.width==840,"Explicit reset failed to replace malformed own preferences");checks.add("malformed_preferences_preserve_layout_and_explicit_reset");
                    var currentPreferences=PanelPreferences.load(directory);
                    String legacy=new PanelPreferences(currentPreferences.panel,currentPreferences.launcher).encode();
                    Files.writeString(directory.resolve("chat-layout.preferences"),legacy);int retainedAccent=p.candidateTheme().accent;
                    require(p.configureCandidatePreferences(directory)&&p.candidateTheme().accent==retainedAccent,"Legacy geometry load changed this-run style");
                    require(Files.readString(directory.resolve("chat-layout.preferences")).equals(legacy),"Legacy load rewrote file");
                    press(p.candidateButton("Style"));press(p.candidateButton("Forest"));press(p.candidateButton("Style"));
                    require(PanelPreferences.load(directory).theme.name.equals("Forest")&&input[0].text().toString().equals(draft),"Explicit style did not upgrade legacy preferences safely");
                    checks.add("legacy_geometry_no_rewrite_until_explicit_style");
                    // Supplied layout dimensions only: never resize the engine/window or inject input.
                    int nativeW=CORE.getGraphics().nativeWidth,nativeH=CORE.getGraphics().nativeHeight;
                    input[0].text().clear().add(draft);
                    require(p.reconcileViewport(700,600),"Idle viewport change not reconciled");bounds(p,700,600);
                    require(p.candidateLayout().width==700&&p.candidateLayout().height==600,"Idle panel did not shrink to bounds");
                    var same=p.section();require(!p.reconcileViewport(700,600)&&p.section()==same,"Unchanged viewport rebuilt controls");
                    require(!p.reconcileViewport(0,600)&&p.section()==same,"Invalid viewport changed accepted layout");
                    require(input[0]==p.candidateComposer()&&input[0].text().toString().equals(draft),"Idle viewport lost draft");checks.add("idle_viewport_reflow_and_draft");
                    var h=p.candidateHandle(GestureReducer.Target.header);double x=h.body().cX(),y=h.body().cY();
                    require(p.beginGesture(GestureReducer.Target.header,x,y,550),"Begin viewport-change capture");
                    require(p.reconcileViewport(680,580)&&!p.candidateCapturing(),"Viewport transition did not cancel capture");bounds(p,680,580);checks.add("viewport_change_cancels_capture");
                    input[0].listen();require(Mouse.currentClicked==input[0],"Own composer focus setup");
                    require(p.reconcileViewport(600,500),"Undersized transition ignored");bounds(p,600,500);
                    require(Boolean.FALSE.equals(p.context().get("panel_open"))&&Mouse.currentClicked!=input[0],"Undersized panel retained own composer focus");
                    require(input[0].text().toString().equals(draft),"Undersized fallback lost draft");checks.add("undersized_viewport_closes_and_releases_own_focus");
                    require(p.reconcileViewport(100,60),"Closed launcher shrink ignored");bounds(p,100,60);
                    require(p.reconcileViewport(nativeW,nativeH),"Native dimensions recovery failed");bounds(p);
                    require(Boolean.FALSE.equals(p.context().get("panel_open")),"Recovery unexpectedly reopened panel");
                    shortOpen(p,560);require(input[0].text().toString().equals(draft),"Recovery lost draft");
                    GInput other=new GInput(new StringInputSprite(16,UI.FONT().S));other.listen();
                    p.reconcileViewport(600,500);require(Mouse.currentClicked==other,"Fallback cleared unrelated own-widget focus");
                    p.reconcileViewport(nativeW,nativeH);shortOpen(p,570);Mouse.currentClicked=null;
                    checks.add("viewport_recovery_and_closed_launcher_bounds");
                    h=p.candidateHandle(GestureReducer.Target.header);x=h.body().cX();y=h.body().cY();
                    require(p.beginGesture(GestureReducer.Target.header,x,y,600),"Begin manager-close capture");input[0].listen();p.close();require(!p.candidateCapturing()&&Mouse.currentClicked!=input[0],"Manager removal failed to release own capture/focus");p.resetCandidateLayout();checks.add("manager_deactivation_cancel");
                    h=p.candidateHandle(GestureReducer.Target.header);x=h.body().cX();y=h.body().cY();require(p.beginGesture(GestureReducer.Target.header,x,y,700),"Begin scene capture");VIEW.world().activate();require(p.sampleGesture(x,y,701,true).equals("cancelled"),"Scene changed without cancel");VIEW.s().activate();checks.add("scene_change_cancel");
                    p.resetCandidateLayout();h=p.candidateHandle(GestureReducer.Target.header);x=h.body().cX();y=h.body().cY();require(p.beginGesture(GestureReducer.Target.header,x,y,800),"Begin hidden capture");VIEW.hide();require(p.sampleGesture(x,y,801,true).equals("cancelled"),"Hidden UI failed to cancel");checks.add("hidden_ui_cancel");
                    Files.writeString(directory.resolve("stockpile-fixture.json"),JsonWriter.encode(object("passed",true,"checks",checks,"native_width",CORE.getGraphics().nativeWidth,"native_height",CORE.getGraphics().nativeHeight,"composer_capacity",input[0].text().length()+input[0].text().spaceLeft(),"handle_render_callbacks",p.candidateDraws(),"synthetic_protocol_frames",true,"supplied_layout_viewports",List.of(List.of(700,600),List.of(680,580),List.of(600,500),List.of(100,60)),"engine_viewport_changed",false,"provider_calls",0)));
                    Files.writeString(directory.resolve("chat-layout-clean-exit.json"),"{\"passed\":true}");CORE.annihilate();phase[0]=6;return;}
                }
            }catch(Exception error){System.err.println("SMOKE_FIXTURE_FAILURE: "+error);CORE.annihilate(error);}
        });
    }
}
