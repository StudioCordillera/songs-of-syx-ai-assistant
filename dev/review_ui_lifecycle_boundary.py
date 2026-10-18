"""Review finite UI/lifecycle routes in licensed files, without loading game classes.

Publishes metadata, hashes and conclusions only. Compiler probes check accessibility;
selected bytecode checks are not a complete call-graph or absence-of-API proof.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'dev'))
from verify_bytecode import disassemble,method,fingerprint


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def require(body,markers):
    for marker in markers:
        if marker not in body:raise ValueError('Reviewed UI/lifecycle route changed: '+marker)


def reader(body,markers):
    require(body,markers)
    if re.search(r'\b(?:putfield|putstatic|[abilfdcs]astore|new|newarray|anewarray|multianewarray|invokedynamic)\b',body):
        raise ValueError('Candidate observer gained a write/allocation/dynamic dispatch')
    for line in body.splitlines():
        branch=re.match(r'\s*(\d+):\s+(?:if\w*|goto(?:_w)?)\s+(\d+)',line)
        if branch and int(branch[2])<=int(branch[1]):raise ValueError('Candidate observer gained a backward branch')


def compile_probe(java,jar,directory,name,body,diagnostic=None):
    source=directory/(name+'.java')
    source.write_text('final class '+name+' { '+body+' }\n')
    args=[*java,'-m','jdk.compiler/com.sun.tools.javac.Main','-proc:none','-XDrawDiagnostics',
          '--release','16','-cp',str(jar),'-d',str(directory),str(source)]
    result=subprocess.run(args,capture_output=True,text=True,timeout=30)
    if diagnostic is None:
        if result.returncode:raise ValueError('Public UI observer route no longer compiles: '+name)
    elif result.returncode==0 or diagnostic not in result.stderr:
        raise ValueError('Expected access restriction changed; re-review: '+name)
    return {'id':name,'expected_compilation':'success' if diagnostic is None else 'rejected',
            'matched':True,'diagnostic_category':diagnostic,
            'probe_source_sha256':sha(source),'compiler_output_sha256':hashlib.sha256(result.stderr.encode()).hexdigest()}


def review(game,jdk,catalog_path):
    jar=game/'SongsOfSyx.jar';archive=game/'info/SongsOfSyx-sources.jar'
    catalog_raw=catalog_path.read_bytes()
    if len(catalog_raw)>32*1024*1024:raise ValueError('Declaration catalog exceeds 32 MiB')
    catalog=json.loads(catalog_raw)
    if (catalog['game_jar_sha256'],catalog['source_archive_sha256'])!=(sha(jar),sha(archive)):
        raise ValueError('Declaration catalog differs from licensed game/source pair')
    ids={m['id'] for m in catalog['members']}
    required=['view.main.VIEW#world()','view.world.WorldView#UI','view.world.WorldUI#factions',
        'view.world.ui.faction.UIFactions#openIs()','view.world.ui.faction.UIFactions#openIs(game.faction.Faction)',
        'view.world.ui.faction.UIFactions#diploIs(game.faction.Faction)',
        'view.sett.ui.room.UIRoom#detailIns()','view.world.ui.region.UIRegions#get(world.map.regions.Region)',
        'util.gui.misc.GBox#text()','snake2d.CORE#setCurrentState(snake2d.CORE_STATE.Constructor)',
        'game.GameDisposable#GameDisposable()']
    if not set(required)<=ids:raise ValueError('Reviewed public declaration missing from catalog')
    java=['java','-Djava.home='+str(jdk.resolve())];cache={};records=[]
    with zipfile.ZipFile(archive) as z:
        def inspect(owner,signature,markers,read_only=False):
            if owner not in cache:cache[owner]=disassemble(java,jar,owner)
            body=method(cache[owner],signature)
            (reader if read_only else require)(body,markers)
            path=owner.split('$')[0].replace('.','/')+'.java'
            records.append({'owner':owner,'signature':signature,'source_path':path,
                'source_sha256':hashlib.sha256(z.read(path)).hexdigest(),
                'normalized_disassembly_sha256':fingerprint(body),'direct_reader_check':read_only})
            return body
        inspect('view.world.ui.faction.UIFactions','public boolean openIs();',['ISidePanels.added:'],True)
        inspect('view.world.ui.faction.UIFactions','public boolean openIs(game.faction.Faction);',
                ['ISidePanels.added:','UIFaction.f:','if_acmpne'],True)
        inspect('view.world.ui.faction.UIFactions','public boolean diploIs(game.faction.Faction);',
                ['ISidePanels.added:','UIFaction.f:','UIFaction.dipIS:'],True)
        inspect('view.world.ui.faction.UIFaction','public game.faction.Faction f();',['GETTER$GETTER_IMP.get:'],True)
        inspect('view.world.ui.faction.UIFaction','public boolean dipIS();',['CLICKABLE$ClickSwitch.current:'],True)
        inspect('view.interrupter.ISidePanels','public boolean added(view.interrupter.ISidePanel);',['ArrayList.size:','ArrayList.get:'])
        inspect('view.sett.ui.room.UIRoom','public settlement.room.main.RoomInstance detailIns();',['UIRoom$Detail.room:'],True)
        for owner in ['Other','Play','PlayCapitol']:
            body=inspect('view.world.ui.region.'+owner,'public view.interrupter.ISidePanel get(world.map.regions.Region);',['GETTER$GETTER_IMP.set:'])
            if owner!='Other':require(body,['.add:','ISidePanel.titleSet:'])
        inspect('util.gui.misc.GBox','public util.gui.misc.GText text();',['textsFreeI:','putfield','GText.clear:'])
        inspect('game.GAME','private game.GAME(game.GameSpec) throws java.io.IOException;',
                ['CORE.disposeClient:','GameDisposable.disposeAll:'])
        inspect('view.menu.IMenu','void exit2Menu();',['CORE.setCurrentState:'])
        inspect('view.menu.IMenu$12','public snake2d.CORE_STATE getState();',['menu/Menu.make:'])
        resource=disassemble(java,jar,'snake2d.CORE_RESOURCE')
        require(resource,['  abstract void dis();'])
        scripts={}
        for owner in ['script.SCRIPT','script.SCRIPT$SCRIPT_INSTANCE']:
            declaration=disassemble(java,jar,owner)
            # Names are public API metadata; neither source nor bytecode bodies are published.
            names=re.findall(r'^  public (?:default |abstract )?[^\n;(]+? (\w+)\([^\n;]*\)(?: throws [^;\n]+)?;$',declaration,re.M)
            scripts[owner]=sorted(names)
        expected={'script.SCRIPT':{'name','desc','initBeforeGameCreated','initBeforeGameInited','createInstance','isSelectable','forceInit'},
                  'script.SCRIPT$SCRIPT_INSTANCE':{'update','save','load','hoverTimer','render','keyPush','mouseClick','handleBrokenSavedState','hover'}}
        if any(set(scripts[k])!=v for k,v in expected.items()):raise ValueError('SCRIPT declaration set changed; review new lifecycle contracts')
        paths=['script/SCRIPT.java','game/GameDisposable.java','snake2d/CORE.java','snake2d/CORE_RESOURCE.java',
            'snake2d/CORE_STATE.java','snake2d/Updater.java','view/sett/ui/room/UIRooms.java',
            'view/ui/manage/IManager.java','view/interrupter/InterManager.java','view/world/ui/region/UIRegions.java']
        sources={path:{'sha256':hashlib.sha256(z.read(path)).hexdigest()} for path in paths}
        source_markers={'view/sett/ui/room/UIRooms.java':['final UIRoom[] rooms ='],
            'view/ui/manage/IManager.java':['private IFullView current;'],
            'view/interrupter/InterManager.java':['private final Collection inters'],
            'snake2d/Updater.java':['private CORE_STATE current;','current.exit();'],
            'game/GameDisposable.java':['protected abstract void dispose();','static void disposeAll()']}
        for path,markers in source_markers.items():require(z.read(path).decode(),markers)
    with tempfile.TemporaryDirectory(prefix='syx-ui-access-') as tmp:
        directory=Path(tmp)
        probes=[compile_probe(java,jar,directory,'FactionObservers',
            'boolean read(game.faction.Faction f) { var ui=view.main.VIEW.world().UI.factions; return ui.openIs() || ui.openIs(f) || ui.diploIs(f); }')]
        cases=[('LiveRoomAccess','Object read() { return view.main.VIEW.s().ui.rooms.rooms; }','compiler.err.not.def.public.cant.access'),
            ('ManagementTabAccess','Object read() { return view.main.VIEW.UI().manager.current; }','compiler.err.report.access'),
            ('GeneralPanelAccess','Object read() { return view.main.VIEW.inters().manager.inters; }','compiler.err.report.access'),
            ('TooltipStorageAccess','Object read() { return view.main.VIEW.hoverBox().texts; }','compiler.err.report.access'),
            ('RegionSelectionAccess','boolean read(world.map.regions.Region r) { return view.main.VIEW.world().UI.regions.active(r); }','compiler.err.not.def.public.cant.access'),
            ('EngineDisposalHook','static class Hook extends snake2d.CORE_RESOURCE { public void dis() {} }','compiler.err.does.not.override.abstract')]
        for name,body,diagnostic in cases:probes.append(compile_probe(java,jar,directory,name,body,diagnostic))
    return {'passed':True,'reviewed_at':datetime.now(timezone.utc).isoformat(),
        'stage':'Finite static UI/lifecycle route review; runtime evidence is recorded separately',
        'game_jar_sha256':sha(jar),'source_archive_sha256':sha(archive),'catalog_sha256':hashlib.sha256(catalog_raw).hexdigest(),
        'verifier_source_sha256':sha(Path(__file__)),'public_declaration_members':required,
        'selected_method_checks':records,'additional_source_files':sources,'script_public_declarations':scripts,
        'compile_probes':probes,'inference_calls':0,'game_methods_executed':0,
        'conclusions':[
            'Faction list presence, faction-specific detail presence and diplomacy-tab presence have a compiling public route. Selected bodies read stored panel/identity/switch state; panel membership loops over added panels. These findings alone do not establish native agreement, bounded faction enumeration, null/unavailable behavior or cost; inspect separate production/native evidence.',
            'UIRoom.detailIns is a public stored getter, but the live UIRooms.rooms field is package-private. Constructing another UIRoom would not identify the actual selection. No selected-room mapping is established by this route.',
            'UIRegions.get dispatches to panel-binding methods; all three reviewed implementations assign the region getter. Player/capital paths also install a tool and title. It is excluded from production observations. Region active is package-private.',
            'GBox.text allocates/clears pooled text and advances its cursor; it is a builder, not enumeration of displayed tooltip text. Stored text collection is private.',
            'Management current and general interrupter collection remain private. Known flags and bounded popup content do not establish their selected tab, ordering or full tree.',
            'Reviewed SCRIPT declarations expose creation/update/persistence/input/render callbacks but no unload callback. GameDisposable disposal is called during GAME construction, not a proven immediate menu-unload notification. Engine disposal remains package-private and cannot be implemented by an ordinary external subclass. Updater current state is private; public state replacement is a mutation, not observation.'
        ],'limits':[
            'Shipped source/binary/accessibility evidence, not an official stable mod contract or exhaustive proof that no other public route exists.',
            'Direct bytecode checks do not establish transitive purity, thread safety, runtime availability, boundedness of faction scans or full state/menu coverage.',
            'Compiler probes compile against the licensed JAR with annotation processing disabled; they never load or run game classes. Negative probes cover only the named access paths.',
            'No production source, runtime mapping or player payload is changed by this static review. No screenshots, native input, process memory or reflection are used.'
        ]}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--game-dir',type=Path,required=True);p.add_argument('--jdk-home',type=Path,required=True)
    p.add_argument('--catalog',type=Path,default=ROOT/'build/game-api-catalog.json')
    p.add_argument('--output',type=Path,default=ROOT/'UI_LIFECYCLE_BOUNDARY_REVIEW.json')
    a=p.parse_args();report=review(a.game_dir.resolve(),a.jdk_home.resolve(),a.catalog)
    a.output.write_text(json.dumps(report,indent=2)+'\n');print('UI/lifecycle static review passed:',a.output)
