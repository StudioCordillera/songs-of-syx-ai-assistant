package syx.assistant.candidate;

import init.settings.S;
import java.util.*;
import static syx.assistant.StateCollector.object;

/** Developer-only fixed getters on an already initialized game settings object. */
public final class SettingsObservation {
    public static final List<String> IDS=List.of("audio_master","audio_effects","audio_music","audio_ambience","mute_unfocused",
        "shadows","particles","graphics_detail","gore","brightness","autosave_interval","autosave_files","edge_scroll","day_cycle","ui_day_cycle","visual_weather");
    private static final String[] MEMBERS={"volumeMaster","volumeSound","volumeMusic","volumeAmbience","muteUnfocused",
        "shadows","particles","graphics","gore","brightness","autoSaveInterval","autoSaveFiles","scroll","lightCycle","uilightCycle","downpour"};
    private static final int[] MIN={0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0};
    private static final int[] MAX={20,20,20,20,1,2,2,1,2,20,10,10,1,1,1,1};
    private SettingsObservation(){}
    private static final class UnexpectedRange extends IllegalArgumentException {}
    public static Map<String,Object> detachedRow(int index,int value,int minimum,int maximum){
        if(index<0 || index>=IDS.size() || minimum!=MIN[index] || maximum!=MAX[index] || value<minimum || value>maximum)
            throw new UnexpectedRange();
        return object("setting_id",IDS.get(index),"configured_steps",value,"minimum_steps",minimum,"maximum_steps",maximum,
            "source","init.settings.S."+MEMBERS[index]+".get()/min()/max()","unit","configured UI step");
    }
    public static Map<String,Object> collect(S initialized){
        if(initialized==null)return object("available",false,"coverage","unavailable","scope","already_initialized_game_settings",
            "data",null,"reason","No already initialized settings object supplied; observer does not initialize it");
        // Do not call S.get(): that accessor can lazily create settings/load files.
        S.Setting[] settings={initialized.volumeMaster,initialized.volumeSound,initialized.volumeMusic,initialized.volumeAmbience,
            initialized.muteUnfocused,initialized.shadows,initialized.particles,initialized.graphics,initialized.gore,initialized.brightness,
            initialized.autoSaveInterval,initialized.autoSaveFiles,initialized.scroll,initialized.lightCycle,initialized.uilightCycle,initialized.downpour};
        List<Map<String,Object>> rows=new ArrayList<>(),failures=new ArrayList<>();
        for(int i=0;i<settings.length;i++){
            try{S.Setting setting=settings[i];rows.add(detachedRow(i,setting.get(),setting.min(),setting.max()));}
            catch(UnexpectedRange failure){failures.add(object("setting_id",IDS.get(i),"failure_kind","value_or_range_mismatch","reason","Configured value/range differs from this source-pinned mapping"));}
            catch(RuntimeException failure){failures.add(object("setting_id",IDS.get(i),"failure_kind","getter_unavailable","reason","Configured setting getter unavailable"));}
        }
        if(rows.isEmpty())return object("available",false,"coverage","unavailable","scope","already_initialized_game_settings",
            "data",null,"requested_settings",16,"complete_fixed_selection",false,"failed_settings",failures,"reason","No configured setting reads succeeded");
        return object("available",true,"coverage","partial","scope","already_initialized_game_settings","data",
            object("rows",rows,"failed_settings",failures,"requested_settings",16,"complete_fixed_selection",failures.isEmpty(),
                "field_definitions",object("configured_steps",object("unit","configured UI step","meaning",
                    "Value returned by the public settings UI adapter, not necessarily the underlying launcher value. Audio/brightness use 20 truncated quantized steps, which can understate any underlying stored percentage. Zero steps do not prove zero mixer gain. Other fields have their own reported ranges."),
                    "scope",object("meaning","Configured game preferences only; not operating-system mute, physical loudness, focus state, effective rendering or time until next autosave.")),
                "limits","Fixed 16 game UI options, not all launcher/engine settings. No set/save/apply/getValue/make or lazy initialization calls. No current menu/selected tab inference."));
    }
}
