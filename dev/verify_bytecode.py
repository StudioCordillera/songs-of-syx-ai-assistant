"""Development-only checks of critical installed method bodies; publishes hashes and conclusions, not bytecode."""
import hashlib
import re
import subprocess


def disassemble(java, jar, class_name):
    result=subprocess.run([*java,'-m','jdk.jdeps/com.sun.tools.javap.Main','-c','-private',
        '-cp',str(jar),class_name],capture_output=True,text=True,check=True,timeout=30)
    return result.stdout


def method(text, signature):
    start=text.index('  '+signature)
    match=re.search(r'\n  (?:public |protected |private |static |abstract |[\w.$<>]+\s+[\w.$<>]+\()',text[start+3:])
    return text[start:start+3+match.start()] if match else text[start:]


def fingerprint(text):
    normalized=re.sub(r'#\d+','#',text).strip()
    return hashlib.sha256(normalized.encode()).hexdigest()


def verify(java, jar):
    owned=method(disassemble(java,jar,'init.resources.RESOURCE'),'public int owned();')
    cursor=0
    for marker in ['ROOMS.STOCKPILE:', 'StockpileTally.amountReservable:', 'ROOMS.EXPORT:',
                   'ROOMS.IMPORT:', 'ROOMS.HAULER:', 'HaulerTally.amountReservable:',
                   'ROOMS.STATION:', '$Total.stored:', '$Total.incoming:', 'FACTIONS.player:',
                   'Player.seller:', '.promised:', 'isub', 'ireturn']:
        cursor=owned.index(marker,cursor)+len(marker)
    if len(re.findall(r'\biadd\b',owned))!=5 or len(re.findall(r'\bisub\b',owned))!=1:
        raise ValueError('RESOURCE.owned arithmetic changed; re-establish its definition')
    exit_menu=method(disassemble(java,jar,'view.menu.IMenu'),'void exit2Menu();')
    if 'CORE.setCurrentState:' not in exit_menu:raise ValueError('Menu transition changed')
    constructor=method(disassemble(java,jar,'view.menu.IMenu$12'),'public snake2d.CORE_STATE getState();')
    if 'menu/Menu.make:' not in constructor:raise ValueError('Menu factory changed')
    resource=disassemble(java,jar,'snake2d.CORE_RESOURCE')
    if not re.search(r'^  abstract void dis\(\);$',resource,re.M):
        raise ValueError('Disposal API visibility changed; re-audit its applicability')
    game=disassemble(java,jar,'game.GAME')
    update=method(game,'public void update(double, double);')
    register=method(game,'public static void addAfterUpdate(snake2d.util.misc.ACTION);')
    resource_update=update.rindex('game/GAME$GameResource.update:')
    dispatch=update.index('onUpdateFinish:',resource_update)
    if 'snake2d/util/misc/ACTION.exe:' not in update[dispatch:] or 'onUpdateFinish:' not in register or 'ArrayListGrower.add:' not in register:
        raise ValueError('After-update observer dispatch changed; re-establish sampling phase')
    return {
        'method':'Selected member references/access/arithmetic inspected with JDK javap; no game method execution. Not formal equivalence of the complete shipped source and binary.',
        'checks':[
            {'id':'game_after_update_dispatch','passed':True,'member':'game.GAME#addAfterUpdate(ACTION)',
             'normalized_disassembly_sha256':fingerprint(update+register),
             'conclusion':'Public registration appends an ACTION to the after-update collection, dispatched after resource update loops. UI-paused nonzero-speed behavior needs runtime validation; no standalone menu/unload contract is established.'},
            {'id':'resource_owned_definition','passed':True,'member':'init.resources.RESOURCE#owned()',
             'normalized_disassembly_sha256':fingerprint(owned),
             'conclusion':'Scene logistics and incoming station goods are added; player trade promises are subtracted. Not warehouse-only inventory.'},
            {'id':'return_to_menu','passed':True,'member':'view.menu.IMenu#exit2Menu()',
             'normalized_disassembly_sha256':fingerprint(exit_menu+constructor),
             'conclusion':'Private/package API requests CORE state replacement with Menu.make; no SCRIPT unload callback is established by this path.'},
            {'id':'engine_disposal_visibility','passed':True,'member':'snake2d.CORE_RESOURCE#dis()',
             'conclusion':'Abstract disposal method is package-private, not a callback a normal mod subclass can implement.'}
        ]}
