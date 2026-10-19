"""Verify finite public world-list observer routes without initializing game classes."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'dev'))
from review_ui_lifecycle_boundary import compile_probe,reader,require,sha
from verify_bytecode import disassemble,method,fingerprint


def review(game,jdk,catalog_path):
    jar=game/'SongsOfSyx.jar';archive=game/'info/SongsOfSyx-sources.jar'
    raw=catalog_path.read_bytes();catalog=json.loads(raw)
    if catalog['game_jar_sha256']!=sha(jar) or catalog['source_archive_sha256']!=sha(archive):
        raise ValueError('Catalog differs from licensed game/source pair')
    required=['view.main.VIEW#world()','view.world.WorldView#UI','view.world.WorldView#panels',
        'view.world.WorldUI#armies','view.world.WorldUI#regions',
        'view.world.ui.army.UIArmies#listIsOpen(view.interrupter.ISidePanels)',
        'view.world.ui.region.UIRegions#playerList','view.world.ui.region.UIRegions#allList',
        'view.interrupter.ISidePanels#added(view.interrupter.ISidePanel)']
    if not set(required)<={m['id'] for m in catalog['members']}:raise ValueError('Candidate public declaration missing')
    java=['java','-Djava.home='+str(jdk.resolve())];records=[]
    cases=[('view.world.ui.army.UIArmies','public boolean listIsOpen(view.interrupter.ISidePanels);',['ISidePanels.added:'],True),
        ('view.interrupter.ISidePanels','public boolean added(view.interrupter.ISidePanel);',
            ['Interrupter.isActivated:','ArrayList.size:','ArrayList.get:','if_acmpne'],False),
        ('view.interrupter.Interrupter','public final boolean isActivated();',['addManager:'],True),
        ('snake2d.util.sets.ArrayList','public int size();',['last:I','ireturn'],True),
        ('snake2d.util.sets.ArrayList','public E get(int);',['last:I','es:[Ljava/lang/Object;','aaload','areturn'],True)]
    with zipfile.ZipFile(archive) as z:
        for owner,signature,markers,no_loop in cases:
            body=method(disassemble(java,jar,owner),signature)
            if no_loop:
                reader(body,markers)
                calls=re.findall(r'// (?:InterfaceMethod|Method) ([^\s:]+):',body)
                if (owner=='view.world.ui.army.UIArmies' and (len(calls)!=1 or not calls[0].endswith('ISidePanels.added'))) or (owner!='view.world.ui.army.UIArmies' and calls):
                    raise ValueError('Direct reader call surface changed')
            else:
                require(body,markers)
                if re.search(r'\b(?:putfield|putstatic|[abilfdcs]astore|new|newarray|anewarray|multianewarray|invokedynamic)\b',body):
                    raise ValueError('Membership reader gained heap write/allocation')
                calls=re.findall(r'// (?:InterfaceMethod|Method) ([^\s:]+):',body)
                if len(calls)!=3 or {c.rsplit('.',1)[-1] for c in calls}!={'isActivated','size','get'}:
                    raise ValueError('Membership reader call surface changed')
            path=owner.replace('.','/')+'.java'
            records.append({'owner':owner,'signature':signature,'source_path':path,
                'source_sha256':hashlib.sha256(z.read(path)).hexdigest(),'normalized_disassembly_sha256':fingerprint(body),
                'no_direct_heap_write_allocation':True,'loop_bound':'Source-verified fixed 16-slot added collection' if not no_loop else 'No backward branch'})
        constructor=method(disassemble(java,jar,'view.interrupter.ISidePanels'),'public view.interrupter.ISidePanels(view.interrupter.InterManager, int);')
        if len(re.findall(r'\bbipush\s+16\b',constructor))!=3:raise ValueError('Panel pool constructor bound changed')
        capacity_check={'owner':'view.interrupter.ISidePanels','signature':'public view.interrupter.ISidePanels(view.interrupter.InterManager, int);',
            'normalized_disassembly_sha256':fingerprint(constructor),'fixed_pool_capacity':16,'scope':'Constructor inspected only, never invoked by production observer'}
        paths=['view/world/WorldUI.java' ,'view/world/WorldView.java','view/world/ui/region/UIRegions.java',
            'view/world/ui/region/ListPlayer.java','view/world/ui/region/ListAll.java','view/interrupter/ISidePanels.java',
            'snake2d/util/sets/ArrayList.java']
        source={p:z.read(p).decode() for p in paths}
        require(source['view/interrupter/ISidePanels.java'],['private final ArrayList<Panel> free = new ArrayList<>(16);',
            'private final ArrayList<Panel> added = new ArrayList<>(16);','for (int i = 0; i < 16; i++)','free.add(new Panel());'])
        require(source['snake2d/util/sets/ArrayList.java'],['private final Object[] es;','es = new Object[size];',
            'if (!hasRoom())','throw new RuntimeException("I\'m full!"'])
        require(source['view/world/ui/region/UIRegions.java'],['public final ISidePanel playerList;',
            'public final ISidePanel allList;','playerList = new ListPlayer(panels);','allList = new ListAll();'])
        require(source['view/world/ui/region/ListPlayer.java'],['realm().regions()-1','realm().region(index+1)'])
        require(source['view/world/ui/region/ListAll.java'],['f.info.area() > 0 && !(f.faction() == FACTIONS.player() && f.capitol())'])
        files={p:hashlib.sha256(z.read(p)).hexdigest() for p in paths}
    with tempfile.TemporaryDirectory(prefix='syx-world-list-access-') as tmp:
        probe=compile_probe(java,jar,Path(tmp),'WorldListObservers',
            'boolean[] read() { var w=view.main.VIEW.world(); return new boolean[]{ w.UI.armies.listIsOpen(w.panels), w.panels.added(w.UI.regions.playerList), w.panels.added(w.UI.regions.allList) }; }')
    return {'passed':True,'reviewed_at':datetime.now(timezone.utc).isoformat(),'game_jar_sha256':sha(jar),
        'source_archive_sha256':sha(archive),'catalog_sha256':hashlib.sha256(raw).hexdigest(),
        'verifier_source_sha256':sha(Path(__file__)),'public_declaration_members':required,'selected_method_checks':records,
        'additional_source_sha256':files,'fixed_pool_constructor_check':capacity_check,'helper_source_sha256':{n:sha(ROOT/n) for n in ['dev/review_ui_lifecycle_boundary.py','dev/verify_bytecode.py']},'compile_probe':probe,'game_methods_executed':0,'inference_calls':0,
        'conclusions':['Three compiling public observer routes return activated side-panel-manager membership, not selected army/region identities, list rows/search/sort, a tab tree or rendered visibility.',
            'ISidePanels.added first requires manager activation, then identity-scans its private fixed-capacity 16-slot collection. Three production checks need at most 48 membership comparisons in this pinned implementation. Ordinary getter calls have the selected read-only bytecode surface checked separately.',
            'playerList is the Realm panel whose row builder skips realm index zero. allList is the Regions browser whose source excludes the player capital and applies its own sort/filter. Their presence does not prove a complete census, foreign-only listing or selection.',
            'Inactive views, hidden UI and modals require explicit scope guards/caveats; compile/source checks alone do not establish live behavior. Panel-opening/binding/get(Region) or hide actions are excluded from production observers.'],
        'limits':['Shipped source/binary/compiler evidence, not separately documented stable contracts or formal whole-game purity/thread-safety proof.',
            'No native agreement, lifecycle/occlusion/fault or cost evidence is implied. Inspect separately source-pinned runtime reports before promoting observations.',
            'No game initialization, reflection, process memory, screenshots or native input. Metadata/hashes only; licensed source/bodies are not redistributed.']}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--game-dir',type=Path,required=True);p.add_argument('--jdk-home',type=Path,required=True)
    p.add_argument('--catalog',type=Path,default=ROOT/'build/game-api-catalog.json')
    p.add_argument('--output',type=Path,default=ROOT/'WORLD_LIST_BOUNDARY_REVIEW.json');a=p.parse_args()
    report=review(a.game_dir.resolve(),a.jdk_home.resolve(),a.catalog)
    a.output.write_text(json.dumps(report,indent=2)+'\n');print('World-list boundary review passed:',a.output)
