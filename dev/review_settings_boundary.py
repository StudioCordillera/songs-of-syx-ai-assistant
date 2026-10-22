"""Finite public configured-settings review against licensed source/binary files."""
import argparse
from datetime import datetime,timezone
import hashlib,json
from pathlib import Path
import sys,tempfile,zipfile
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'dev'))
from review_ui_lifecycle_boundary import compile_probe,reader,require
from verify_bytecode import disassemble,method,fingerprint

MEMBERS=('volumeMaster','volumeSound','volumeMusic','volumeAmbience','muteUnfocused','shadows','particles','graphics','gore','brightness','autoSaveInterval','autoSaveFiles','scroll','lightCycle','uilightCycle','downpour')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def review(game,jdk):
    jar=game/'SongsOfSyx.jar';archive=game/'info/SongsOfSyx-sources.jar';audit=json.loads((ROOT/'api-audit.json').read_text())
    if sha(jar)!=audit['game_jar_sha256'] or sha(archive)!=audit['source_archive_sha256']:raise ValueError('Game/source differs from pinned API audit')
    java=['java','-Djava.home='+str(jdk.resolve())];records=[]
    with zipfile.ZipFile(archive) as z:
        for owner,signature,markers in (
            ('init.settings.S$Setting','public int get();',['LSettingInt.get:','min:','max:','CLAMP.i:']),
            ('init.settings.S$Setting','public int min();',['iconst_0','ireturn']),
            ('init.settings.S$SettingPerc','public int get();',['LSettingInt.getD:','max:','dmul','d2i']),
            ('init.settings.S$SettingPerc','public int min();',['iconst_0','ireturn']),
            ('init.settings.S$SettingPerc','public int max();',['bipush        20','ireturn']),
            ('launcher.LSettings$LSettingInt','public int get();',['Field v:','max:','CLAMP.i:']),
            ('launcher.LSettings$LSettingInt','public int max();',['getfield','ireturn'])):
            body=method(disassemble(java,jar,owner),signature);reader(body,markers)
            records.append({'owner':owner,'signature':signature,'normalized_disassembly_sha256':fingerprint(body),'direct_reader_check':True})
        lazy=method(disassemble(java,jar,'init.settings.S'),'public static init.settings.S get();')
        require(lazy,['new','putstatic'])
        raw=z.read('init/settings/S.java');text=raw.decode();lines=text.splitlines()
        for member in MEMBERS:require(text,['public final Setting '+member+';'])
        bootstrap=method(disassemble(java,jar,'menu.Menu'),'public static void start();')
        require(bootstrap,['init/settings/S.get:','init/settings/S.make:','snake2d/CORE.create:'])
        if not bootstrap.index('init/settings/S.get:') < bootstrap.index('snake2d/CORE.create:'):raise ValueError('Settings bootstrap ordering changed')
        source_paths=('init/settings/S.java','launcher/LSettings.java','util/data/INT.java','menu/Menu.java')
        sources={n:hashlib.sha256(z.read(n)).hexdigest() for n in source_paths}
        anchors={member:next(i for i,line in enumerate(lines,1) if 'public final Setting '+member+';' in line) for member in MEMBERS}
    with tempfile.TemporaryDirectory() as temp:
        directory=Path(temp)
        body='static int read(init.settings.S s){return '+ '+'.join('s.'+n+'.get()+s.'+n+'.min()+s.'+n+'.max()' for n in MEMBERS)+';}'
        probes=[compile_probe(java,jar,directory,'ConfiguredSettingsRead',body),
                compile_probe(java,jar,directory,'ProtectedRawSetting','static int read(init.settings.S s){return s.volumeMaster.s.get();}','compiler.err.report.access')]
    return {'passed':True,'reviewed_at':datetime.now(timezone.utc).isoformat(),'scope':'Fixed public settings UI getters on an already initialized S object; no game class initialization or engine execution in this review.',
        'game_jar_sha256':sha(jar),'source_archive_sha256':sha(archive),'documented_script_contract':False,
        'source_verified_public_fields':list(MEMBERS),'declaration_lines':anchors,'selected_source_sha256':sources,'selected_methods':records,'compiler_probes':probes,
        'normal_menu_bootstrap_sha256':fingerprint(bootstrap),'normal_menu_initializes_settings_before_core':True,
        'lazy_accessor_sha256':fingerprint(lazy),'lazy_accessor_invoked_by_candidate':False,
        'conclusions':['S.get can allocate/initialize/load settings; reader accepts an already initialized S and does not call that accessor.',
            'Setting.get returns a clamped launcher-backed value; SettingPerc overrides it with a truncated normalized 0..20 UI step. Audio and brightness use this adapter.',
            'Zero quantized audio steps can conceal a positive underlying launcher percentage; not proof of zero gain or OS/device mute.',
            'Setters, save, applyRuntimeConfigs, getValue and make are not observer calls. Protected raw backing setting access is rejected by external compilation.',
            'The copied-game bootstrap calls S.get().make before CORE creation, so its later update callback supplies an existing object. The shipped normal Menu.start also initializes S before CORE creation; this establishes bootstrap ordering, not a live main-menu observation callback.'],
        'limits':['Selected methods/source/ranges only, not a complete transitive call graph or full game/launcher settings schema.','No physical audio, UI visibility, focus state, effective rendering, autosave ETA or native behavior proven by static review.'],
        'reviewer_source_sha256':sha(__file__)}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--game-dir',type=Path,required=True);p.add_argument('--jdk-home',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output.write_text(json.dumps(review(a.game_dir,a.jdk_home),indent=2)+'\n')
