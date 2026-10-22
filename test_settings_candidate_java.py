"""Detached candidate validation with own stubs; licensed accessibility/native checks are separate."""
import os
from pathlib import Path
import subprocess
import pytest

ROOT=Path(__file__).resolve().parent


@pytest.mark.parametrize("production", [False,True])
def test_configured_settings_bounds_failure_isolation_and_no_lazy_accessor(tmp_path,production):
    settings=tmp_path/'init/settings/S.java';settings.parent.mkdir(parents=True)
    members=('volumeMaster','volumeSound','volumeMusic','volumeAmbience','muteUnfocused','shadows','particles','graphics','gore','brightness','autoSaveInterval','autoSaveFiles','scroll','lightCycle','uilightCycle','downpour')
    minima=[0]*16;minima[11]=1
    maxima=[20,20,20,20,1,2,2,1,2,20,10,10,1,1,1,1]
    # Deliberately no static S.get(), save/apply/make or settings setters.
    settings.write_text('package init.settings; public class S { public static class Setting { public int value,lo,hi; public boolean fail; public Setting(int a,int b){value=lo=a;hi=b;} public int get(){if(fail)throw new IllegalStateException();return value;} public int min(){return lo;} public int max(){return hi;} } '+''.join(f'public Setting {name}=new Setting({lo},{hi});' for name,lo,hi in zip(members,minima,maxima))+'}')
    collector=tmp_path/'syx/assistant/StateCollector.java';collector.parent.mkdir(parents=True)
    collector.write_text('package syx.assistant; import java.util.*; public class StateCollector { public static Map<String,Object> object(Object... a){Map<String,Object> r=new LinkedHashMap<>();for(int i=0;i<a.length;i+=2)r.put((String)a[i],a[i+1]);return r;} }')
    probe=tmp_path/'Probe.java'
    probe.write_text('''import java.util.*; import init.settings.S; import syx.assistant.candidate.SettingsObservation;
public class Probe {
 static void require(boolean b){if(!b)throw new AssertionError();}
 static Map data(S s){return (Map)SettingsObservation.collect(s).get("data");}
 static void rejected(int i,int v,int lo,int hi){try{SettingsObservation.detachedRow(i,v,lo,hi);throw new AssertionError();}catch(IllegalArgumentException expected){}}
 public static void main(String[] args){
  S s=new S();Map base=data(s);require(((List)base.get("rows")).size()==16&&Boolean.TRUE.equals(base.get("complete_fixed_selection")));
  require(Boolean.FALSE.equals(SettingsObservation.collect(null).get("available"))&&SettingsObservation.collect(null).get("data")==null);
  int[] lo={0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0},hi={20,20,20,20,1,2,2,1,2,20,10,10,1,1,1,1};
  for(int i=0;i<16;i++){require(SettingsObservation.detachedRow(i,lo[i],lo[i],hi[i]).get("configured_steps").equals(lo[i]));require(SettingsObservation.detachedRow(i,hi[i],lo[i],hi[i]).get("configured_steps").equals(hi[i]));rejected(i,lo[i]-1,lo[i],hi[i]);rejected(i,hi[i]+1,lo[i],hi[i]);rejected(i,lo[i],lo[i]-1,hi[i]);rejected(i,lo[i],lo[i],hi[i]+1);}
  rejected(-1,0,0,20);rejected(16,0,0,20);
  s.volumeMaster.fail=true;Map failed=data(s);require(((List)failed.get("rows")).size()==15&&((List)failed.get("failed_settings")).size()==1&&Boolean.FALSE.equals(failed.get("complete_fixed_selection")));
  Map f=(Map)((List)failed.get("failed_settings")).get(0);require(f.get("setting_id").equals("audio_master")&&f.get("failure_kind").equals("getter_unavailable")&&!f.containsKey("configured_steps"));
  s.volumeMaster.fail=false;s.scroll=null;require(((List)data(s).get("rows")).size()==15);
  s.scroll=new S.Setting(0,2);Map range=(Map)((List)data(s).get("failed_settings")).get(0);require(range.get("failure_kind").equals("value_or_range_mismatch"));
  s.volumeMaster=null;s.volumeSound=null;s.volumeMusic=null;s.volumeAmbience=null;s.muteUnfocused=null;s.shadows=null;s.particles=null;s.graphics=null;s.gore=null;s.brightness=null;s.autoSaveInterval=null;s.autoSaveFiles=null;s.scroll=null;s.lightCycle=null;s.uilightCycle=null;s.downpour=null;
  Map all=SettingsObservation.collect(s);require(Boolean.FALSE.equals(all.get("available"))&&all.get("data")==null&&((List)all.get("failed_settings")).size()==16);
  System.out.println("PASS 16 bounds, partial failures, unavailable and no lazy accessor");
 }
}''')
    candidate=ROOT/('mod/src/main/java/syx/assistant/SettingsObservation.java' if production else 'dev/candidates/settings/syx/assistant/candidate/SettingsObservation.java')
    if production:probe.write_text(probe.read_text().replace('syx.assistant.candidate.SettingsObservation','syx.assistant.SettingsObservation'))
    compiler=['java']
    if os.environ.get('SYX_JAVA_HOME'):compiler+=['-Djava.home='+os.environ['SYX_JAVA_HOME']]
    subprocess.run([*compiler,'-m','jdk.compiler/com.sun.tools.javac.Main','--release','16','-d',str(tmp_path),str(settings),str(collector),str(candidate),str(probe)],check=True,capture_output=True,timeout=30)
    result=subprocess.run(['java','-cp',str(tmp_path),'Probe'],check=True,capture_output=True,text=True,timeout=30)
    assert result.stdout.startswith('PASS 16 bounds, partial failures, unavailable and no lazy accessor')
