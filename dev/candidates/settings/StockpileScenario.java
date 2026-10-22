import syx.assistant.StateCollector;
import syx.assistant.JsonWriter;

import game.GAME;
import init.settings.S;
import snake2d.CORE;
import view.main.VIEW;
import java.nio.file.*;
import java.util.*;
import syx.assistant.candidate.SettingsObservation;

/** Fixed read-only settings checks; own fixture view changes only in copied game. */
public final class StockpileScenario {
    private static void require(boolean value,String message){if(!value)throw new IllegalStateException(message);}
    public static void install(Path directory){
        GAME.SPEED.speedSet(0);VIEW.s().activate();
        final int[] phase={0};final long start=System.nanoTime();
        List<Map<String,Object>> checks=new ArrayList<>();
        GAME.addAfterUpdate(()->{
            try{
                require(System.nanoTime()-start<90_000_000_000L,"Settings fixture timeout");
                if(phase[0]==3){
                    if(!Files.exists(directory.resolve("verifier.done")))return;
                    Files.writeString(directory.resolve("settings-clean-exit.json"),"{\"passed\":true,\"verified_phases\":3}");CORE.annihilate();phase[0]=4;return;
                }
                if(phase[0]>2 || System.nanoTime()-start<4_000_000_000L)return;
                // LiveSmoke already called S.get().make() before CORE creation.
                require(phase[0]==1?VIEW.world().isActive():VIEW.s().isActive(),"Requested own view not active");
                S initialized=S.get();var observed=SettingsObservation.collect(initialized);
                require(Boolean.TRUE.equals(observed.get("available")),"Settings unavailable");
                Map<?,?> data=(Map<?,?>)observed.get("data");
                require(Boolean.TRUE.equals(data.get("complete_fixed_selection")),"Settings read incomplete");
                List<?> rows=(List<?>)data.get("rows");require(rows.size()==16,"Fixed settings rows");
                S.Setting[] direct={initialized.volumeMaster,initialized.volumeSound,initialized.volumeMusic,initialized.volumeAmbience,
                    initialized.muteUnfocused,initialized.shadows,initialized.particles,initialized.graphics,initialized.gore,initialized.brightness,
                    initialized.autoSaveInterval,initialized.autoSaveFiles,initialized.scroll,initialized.lightCycle,initialized.uilightCycle,initialized.downpour};
                for(int i=0;i<16;i++){
                    Map<?,?> row=(Map<?,?>)rows.get(i);
                    require(row.get("configured_steps").equals(direct[i].get())&&row.get("minimum_steps").equals(direct[i].min())&&row.get("maximum_steps").equals(direct[i].max()),"Direct setting getter mismatch");
                }
                require(Boolean.FALSE.equals(SettingsObservation.collect(null).get("available")),"Null settings must be unavailable");
                checks.add(StateCollector.object("phase",phase[0]==0?"city":phase[0]==1?"world":"city_return","active_view",phase[0]==1?"world":"settlement","getter_comparisons",48,"passed",true));
                if(phase[0]==0){
                    var snapshot=StateCollector.collect(UUID.randomUUID().toString(),1);
                    Map domains=(Map)snapshot.get("domains");Map settings=(Map)domains.get("settings");Map values=(Map)settings.get("data");
                    values.put("configured_options",observed);
                    settings.put("reason","Clock/speed plus developer-only fixed configured UI settings; not production settings coverage");
                    Files.writeString(directory.resolve("settings-observation.json"),JsonWriter.encode(snapshot));VIEW.world().activate();phase[0]=1;
                }else if(phase[0]==1){VIEW.s().activate();phase[0]=2;}
                else{
                    Files.writeString(directory.resolve("stockpile-fixture.json"),JsonWriter.encode(StateCollector.object("passed",true,"checks",checks,"fixed_settings",16,"explicit_settings_mutations",0,"lazy_initialization_by_reader",false,"expected_rows",rows)));
                    phase[0]=3;
                }
            }catch(Exception failure){System.err.println("SMOKE_FIXTURE_FAILURE: "+failure);CORE.annihilate(failure);}
        });
    }
}
