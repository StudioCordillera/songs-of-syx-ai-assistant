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
    public static Map<String,Object> collect() {
        Map<String,Object> result=object("coverage","partial","source","public game API; sampled during SCRIPT_INSTANCE.update",
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
        String kind=VIEW.s().isActive()?"settlement":VIEW.world().isActive()?"world":VIEW.b().isActive()?"battle":"other";
        result.put("active_view",kind);
        result.put("view_class",VIEW.current().getClass().getName());
        result.put("ui_hidden",VIEW.hideUI());
        Interrupters i=VIEW.inters(); Map<String,Object> flags=new LinkedHashMap<>();
        flag(flags,"game_menu",i.menu);flag(flags,"text_input",i.input);flag(flags,"full_screen_prompt",i.fullScreen);
        flag(flags,"confirmation",i.yesNo);flags.put("popup",i.popup.showing());flags.put("popup_secondary",i.popup2.showing());
        flag(flags,"loading",i.load);flag(flags,"section",i.section);flag(flags,"debug",i.debugpanel);
        flag(flags,"encyclopedia",VIEW.UI().wiki);
        flags.put("management_screen",VIEW.UI().manager.open());
        result.put("known_overlays",flags);
        result.put("tooltip_present",!VIEW.hoverBox().emptyIs());
        result.put("known_overlay_active",flags.values().stream().anyMatch(Boolean.TRUE::equals));
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
                rooms.add(object("blueprint_id",bp.key,"scope","room table and detail panels present; exact instance unavailable"));
            result.put("open_room_blueprints",rooms);
        }
        return result;
    }
}
