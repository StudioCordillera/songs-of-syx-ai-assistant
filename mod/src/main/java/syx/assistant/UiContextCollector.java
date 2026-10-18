package syx.assistant;

import java.util.*;
import settlement.entity.humanoid.Humanoid;
import settlement.main.SETT;
import settlement.room.main.RoomBlueprint;
import view.main.VIEW;
import view.main.Interrupters;
import view.interrupter.Interrupter;
import static syx.assistant.StateCollector.object;

/** Fixed read-only mappings, checked against shipped source and the installed public API. */
public final class UiContextCollector {
    private UiContextCollector() { }
    private static void flag(Map<String,Object> flags,String name,Interrupter panel) {
        flags.put(name,panel.isActivated());
    }
    public static String activeView() {
        if(!VIEW.existTemp() || VIEW.current()==null)return "unavailable";
        if(VIEW.current() instanceof view.world.generator.WorldViewGenerator)return "world_generation";
        if(VIEW.s().isActive())return "settlement";
        if(VIEW.s().battle.isActive())return "settlement_battle";
        if(VIEW.world().isActive())return "world";
        if(VIEW.b().isActive())return "battle";
        if(VIEW.b().editor.isActive())return "battle_setup";
        if(VIEW.world().editor.isActive())return "world_editor";
        return "other";
    }
    public static Map<String,Object> scene() {
        world.WorldGen gen=world.WORLD.GEN();
        return object("active_view",activeView(),"settlement_exists",SETT.exists(),
            "settlement_scene_kind",!SETT.exists()?"unavailable":SETT.WORLD_AREA().isBattle?"battlefield":"city",
            "world_generation",object("has_generated_terrain",gen.hasGeneratedTerrain,"is_done",gen.isDone,"is_editing",gen.isEditing,
                "player_location_selected",gen.playerX>=0 && gen.playerY>=0,
                "flags_note","Workflow flags can persist after leaving an editor; use active_view for current UI mode"),
            "scope_note","Settlement getters refer to the currently instantiated scene, which can be a battlefield. Faction ledgers/technology/diplomacy refer to campaign/player resources.");
    }
    /** Known underlying world faction panels, never a topmost-selection or full-tab claim. */
    private static Map<String,Object> worldFactionPanels(String kind) {
        if(!kind.equals("world") || !world.WORLD.GEN().isDone)
            return object("coverage","unavailable","list_open",null,"detail_faction",null,
                "reason","Requires the active completed-world view; hidden panels are not current UI context.");
        var ui=VIEW.world().UI.factions;
        boolean listOpen=ui.openIs();
        int scanned=0,failed=0,matches=0;boolean truncated=false;Map<String,Object> detail=null;
        for(game.faction.Faction faction:game.faction.FACTIONS.active()) {
            if(scanned>=1000){truncated=true;break;}scanned++;
            try {
                if(ui.openIs(faction)) {
                    // Publish each matched identity/tab observation atomically or omit it.
                    Map<String,Object> row=object("faction_id",faction.index(),"diplomacy_tab",ui.diploIs(faction));
                    detail=row;matches++;
                }
            } catch(RuntimeException failure){failed++;}
        }
        if(matches!=1)detail=null;
        return object("coverage","partial","list_open",listOpen,"detail_faction",detail,
            "scanned_factions",scanned,"faction_limit",1000,"failed_factions",failed,"truncated",truncated,
            "matched_detail_factions",matches,"identity_search_complete",!truncated && failed==0,
            "scope","Underlying world faction list/detail panels; a modal or hidden UI may obscure them. Diplomacy tab is the stored switch state, not a proposed/accepted deal or every subtab.",
            "reason",matches>1?"Ambiguous detail identity; no single faction emitted":
                truncated || failed>0?"Incomplete identity search; missing detail is unknown":
                matches==0?"No active faction matched an open detail panel; this does not enumerate other world panels":null);
    }
    @SuppressWarnings("unchecked")
    public static Map<String,Object> collect() {
        Map<String,Object> result=object("coverage","partial","source","public game API; sampled from GAME.addAfterUpdate on the game update thread",
            "active_view",null,"selected_subject",null,"open_room_blueprints",new ArrayList<>(),
            "unsupported",object("selected_room_instance","No public selected-instance getter established",
                "tooltip_text","GBox has no established read-only text enumeration API",
                "full_screen_tab","IManager.current is private; manager.open() only reports presence",
                "arbitrary_panel_tree","InterManager's collection is private",
                "main_menu","SCRIPT instance does not run in the standalone main menu"));
        if(!VIEW.existTemp() || VIEW.current()==null) {
            result.put("available",false); result.put("reason","No initialized game view");return result;
        }
        result.put("available",true);
        result.put("assistant_chat",AssistantScript.chatContext());
        String kind=activeView();
        result.put("active_view",kind);
        try {result.put("world_faction_panels",worldFactionPanels(kind));}
        catch(RuntimeException failure){result.put("world_faction_panels",object("coverage","unavailable",
            "list_open",null,"detail_faction",null,"reason",failure.getClass().getSimpleName()));}
        result.put("world_generation_step",object("available",false,"reason","Wizard staging fields are private; WorldGen flags describe preparation, not the exact visible step"));
        if(kind.equals("battle")) {
            game.battle.state.BattleState battle=VIEW.b().state();
            result.put("battle_context",battle==null?object("available",false,"reason","No active BattleState"):
                object("available",true,"deploying",battle.deploying(),"throne_timer_seconds",battle.throneTimer(),
                    "phase_note","deploying is a logical BattleState flag; pinned start-overlay visibility is not publicly exposed and this flag alone does not prove active fighting",
                    "player_men",game.GAME.ARMIES().player().men(),"enemy_men",game.GAME.ARMIES().enemy().men(),
                    "deployment_bounds",object("unit","settlement_tiles","x1",battle.deploymentBounds().x1(),"x2",battle.deploymentBounds().x2(),
                        "y1",battle.deploymentBounds().y1(),"y2",battle.deploymentBounds().y2())));
        }
        result.put("view_class",VIEW.current().getClass().getName());
        result.put("ui_hidden",VIEW.hideUI());
        Interrupters i=VIEW.inters(); Map<String,Object> flags=new LinkedHashMap<>();
        flag(flags,"game_menu",i.menu);flag(flags,"text_input",i.input);flag(flags,"full_screen_prompt",i.fullScreen);
        flag(flags,"confirmation",i.yesNo);flags.put("popup",i.popup.showing());flags.put("popup_secondary",i.popup2.showing());
        flag(flags,"loading",i.load);flag(flags,"section",i.section);flag(flags,"debug",i.debugpanel);
        flag(flags,"encyclopedia",VIEW.UI().wiki);
        flags.put("management_screen",VIEW.UI().manager.open());
        result.put("known_overlays",flags);
        try {result.put("known_content",UiContentCollector.collect());}
        catch(RuntimeException failure){result.put("known_content",object("coverage","unavailable","reason",failure.getClass().getSimpleName()));}
        result.put("tooltip_present",!VIEW.hoverBox().emptyIs());
        boolean knownOverlay=flags.values().stream().anyMatch(Boolean.TRUE::equals);
        result.put("known_overlay_active",knownOverlay);
        boolean globalConsumed=VIEW.inters().manager.isHovered();
        result.put("input_capture",object("global_hover_consumed",globalConsumed,
            "active_view_hover_consumed",VIEW.current().uiManager.isHovered(),
            "global_hover_consumed_without_known_overlay_flag",globalConsumed && !knownOverlay,
            "scope","Latest public hover-dispatch consumption flags. Not a complete overlay inventory, current pointer target, stacking order or final rendered visibility."));
        if(kind.equals("battle"))((Map<String,Object>)result.get("unsupported")).put("battle_conclusion_overlay",
            "BattleState conclusion flag/result overlay are private; army counts and hover consumption alone do not identify a visible result dialog or outcome");
        result.put("overlay_order_known",false);
        result.put("reference_resolution","Selected objects describe underlying panels; a modal, management screen or hidden UI can obscure them. Do not assume the user's 'this' refers to a selected object.");
        if(kind.equals("settlement")) {
            Humanoid selected=VIEW.s().ui.subjects.current();
            if(selected!=null && !selected.isRemoved()) result.put("selected_subject",object(
                "entity_id",selected.id(),"race_id",selected.race().key,"tile_x",selected.tc().x(),"tile_y",selected.tc().y(),
                "scope","underlying settlement subject panel"));
            result.put("subject_list_open",VIEW.s().ui.subjects.listActive());
            result.put("room_list_open",VIEW.s().panels.added(VIEW.s().ui.rooms.main()));
            List<Object> rooms=new ArrayList<>();
            for(RoomBlueprint bp:SETT.ROOMS().all()) if(VIEW.s().ui.rooms.openIs(bp))
                rooms.add(object("blueprint_id",bp.key,"reference_id",
                    bp instanceof settlement.room.main.RoomBlueprintImp?"room:"+bp.key:null,"scope","room table and detail panels present; exact instance unavailable"));
            result.put("open_room_blueprints",rooms);
        }
        return result;
    }
}
