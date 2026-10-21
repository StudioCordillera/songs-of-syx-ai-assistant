"""Check portable local links, complete documentation inventory and selected current facts."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote,urlsplit

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))


def inventory(root):
    raw=subprocess.check_output(['git','-C',str(root),'ls-files','--cached','--others','--exclude-standard','-z'])
    return sorted({Path(p.decode()) for p in raw.split(b'\0') if p and
        (p.decode().endswith('.md') or ('/' not in p.decode() and p.decode().endswith('.json')))})


def scope(path):
    name=path.name
    if name in {'AGENTS.md','CLAUDE.md','CONTRIBUTING.md','LOCAL_DEVELOPMENT.md','REPOSITORY_MAP.md','DOCUMENTATION_INDEX.md','WORK_STATUS.md'}:
        return 'Current collaboration / navigation'
    if name in {'README.md','ARCHITECTURE.md','INSTALL.md','ROADMAP.md','QUERY_GUIDE.md','DATA_COVERAGE.md','VALIDATION.md'} or str(path)=='releases/README.md':
        return 'Current guide; historical sections retain their stated scope'
    if name in {'PROVIDERS.md','IN_GAME_CHAT.md','OPENAI_CONNECTION.md','CHAT_BACKEND.md','COMPUTER_USE.md','UPSTREAM_API_REQUEST.md'}:
        return 'Requirements / advanced or historical routes; current simple player is Pro'
    if name in {'USER_TEST_VALIDATION.json','PLAYER_CORE_VALIDATION.json','WORKFORCE_VALIDATION.json','SERVICE_VALIDATION.json',
                'DEGRADATION_VALIDATION.json','DEGRADATION_POSITIVE_VALIDATION.json','GUIDANCE_VALIDATION.json',
                'CAPABILITY_DISCOVERY_VALIDATION.json','AUTO_CONNECTION_VALIDATION.json','CHAT_FOCUS_VALIDATION.json',
                'PLAYER_DISTRIBUTION_VALIDATION.json'}:
        return 'Current linked player/feature evidence; inspect exact source/JAR hashes and case scope'
    if name in {'TILE_CAPTURE_VALIDATION.json','ENTITY_CAPTURE_REGRESSION_VALIDATION.json'}:return 'Current retained-read native evidence; inspect bounded selection and source/JAR scope'
    if name=='REGIONAL_REQUEST_COST_VALIDATION.json':return 'Earlier live-page build regional collector/encoding and sequential MCP timings; finite paused campaign, not worst-case acceptance'
    if name=='REGIONAL_CAPTURE_VALIDATION.json':return 'Native regional capture/paging/restoration/reload and finite cost samples; inspect exact source/JAR and limits'
    if name=='REGIONAL_LIVE_VALIDATION.json':return 'Live regional MCP protocol/matrix/scene checks; partial-cache case is explicitly authored'
    if name=='REGIONAL_OUTPUT_VALIDATION.json':return 'Native regional output DTO/MCP exposure; inspect bounded matrix/control and source/JAR scope'
    if name=='REGIONAL_OUTPUT_READER_VALIDATION.json':return 'Candidate native regional stored-reader probe only; no production MCP counter exposure'
    if name=='WORLD_LIST_CONTEXT_VALIDATION.json':return 'Fourteen native world-list membership/context phases with explicit clean completion; inspect exact source/JAR/limits'
    if name=='WORLD_FACTION_CONTEXT_VALIDATION.json':return 'Native faction-panel/current-context and MCP join checks; finite copied-world scope'
    if name=='CURRENT_COLLECTION_COST_VALIDATION.json':return 'Current published collector small-city timings; historical baseline preserved, no large-city/live-request acceptance'
    if name=='STOCKPILE_BOOKKEEPING_VALIDATION.json':return 'Current global stockpile DTO/MCP evidence; per-room arrays are fixture-only'
    if name=='STOCKPILE_READER_VALIDATION.json':return 'Candidate native-reader checks and existing aggregate MCP parity; additional production fields pending'
    if name=='COLLABORATION_VALIDATION.json':return 'Historical collaboration/dev-doc checkpoint; inspect pinned hashes, separate from player evidence'
    if name=='CHAT_TARGET_TASKS_VALIDATION.json':return 'Developer-only owned task/Stop lifecycle with fake providers and copied-city restoration; no native control or fresh real Pro acceptance'
    if name=='CHAT_TARGET_DISPATCH_PRO_VALIDATION.json':return 'Developer-only explicit paid Pro target handoff; copied-game restoration and fake-provider plumbing checks, not native UI/release acceptance'
    if name=='CHAT_TARGET_DISPATCH_VALIDATION.json':return 'Developer-only accepted-turn claim tests and copied-city fake-provider handoff; not native player or paid Pro acceptance'
    if name=='CHAT_TARGET_DISPATCH.md':return 'Developer dispatch seam, cancellation/restart/unknown-delivery contract and remaining integration gates'
    if name=='CHAT_HISTORY_CANDIDATE_VALIDATION.json':return 'Developer-only SQLite receipt/filter/migration and actual bundled-store compatibility tests; not production badge/world-routing acceptance'
    if name=='SELECTED_RESIDENT_QUERY_VALIDATION.json':return 'Existing production three-join/four-source query: two same-callback subject selections, eight actual MCP calls and synthetic absence/precondition cases; no new player mapping'
    if name=='CHAT_GESTURE_JAVA_VALIDATION.json':return 'Unshipped detached Java/Python gesture policy traces and independent outcomes; no native input/focus/widget/player or new peer-review acceptance'
    if name=='HOUSING_REFERENCE_RELEASE_VALIDATION.json':return 'Promoted exact historical housing summaries; 15 records/45 MCP cases, prior seeds/installer AST preserved, fresh player/core/provider/distribution; unchanged Java class contents'
    if name=='HOUSING_GUIDANCE_CANDIDATE_VALIDATION.json':return 'Developer-only two historical housing summaries plus unchanged baseline: 45 actual MCP retrieval cases; no production corpus/player update'
    if name=='HOUSING_REFERENCE_REVIEW.json':return 'Original canonical historical developer comment review, body/author/version caveats and hashes; no current mechanic or corpus promotion'
    if name=='HOUSING_RUNNING_VALIDATION.json':return 'Unchanged production housing: six finite unpaused copied-city observations, direct getter parity and retained-original MCP cache/pin transitions; no all-scene/reassignment guarantee'
    if name=='HOUSING_VALIDATION.json':return 'Production housing: exact-build native DTO/MCP, eight phases, controlled fault/chamber; bounded recorded assignments, not full mechanics'
    if name=='HOUSING_CONTRACT_REVIEW.json':return 'Production housing public source/compiler/selected-bytecode and bad-budget review; not stable documented contracts'
    if name=='HOUSING_BOUNDARY_REVIEW.json':return 'Unregistered housing selected source/public-reader/budget review; mutating routes excluded, no native/player acceptance'
    if name=='HOUSING_RELATIONS_VALIDATION.json':return 'Developer-only detached source-described home relations; native/MCP joins/discovery and atomic relation cap, production mapping unshipped'
    if name=='QUERY_DIAGNOSTICS_RELEASE_VALIDATION.json':return 'Historical fixed scalar query metadata repair; fresh paid/core/distribution/native query checks, unchanged Java class contents; housing mapping unshipped'
    if name=='HOUSING_QUERY_DIAGNOSTICS_VALIDATION.json':return 'Positive native/MCP fixed housing diagnostic propagation; developer-augmented rows, no production housing mapping'
    if name=='HOUSING_QUERY_CANDIDATE_VALIDATION.json':return 'Developer-augmented native snapshot through real MCP; selective query parity and demonstrated missing diagnostics; production readiness false'
    if name=='HOUSING_SCENE_VALIDATION.json':return 'Developer-only unchanged housing candidate in eight real scene/reload phases; separate production MCP regressions, no housing MCP field'
    if name=='HOUSING_FAULT_VALIDATION.json':return 'Developer-only public furnishing clear induces one capacity getter error; failed row omitted and full housing DTO restored'
    if name=='HOUSING_CHAMBER_VALIDATION.json':return 'Developer-only constructed empty/occupied chamber, restored assignment/removal and actual scan/row bounds; unchanged player'
    if name=='HOUSING_CANDIDATE_VALIDATION.json':return 'Unregistered housing: 32 ordinary-home/roster/ledger samples; native noble, budget/fault/lifecycle and MCP integration remain open'
    if name=='WEATHER_VALIDATION.json':return 'Prior weather release getter/DTO/MCP and eight actual scene checks; retain recorded source/JAR scope, unchanged Java class comparison is separate'
    if name=='WEATHER_CONTRACT_REVIEW.json':return 'Production weather public attribution/selected source-bytecode and detached checks; not stable documented contracts'
    if name=='WEATHER_SCENE_VALIDATION.json':return 'Unregistered weather: eight actual scene phases and seven restored public normalization controls; native invalid stored readers remain unproven'
    if name=='WEATHER_CANDIDATE_REVIEW.json':return 'Unregistered weather public-reader/source/bytecode and detached numeric-shape checks; no native or player acceptance'
    if name=='WEATHER_CANDIDATE_NATIVE_VALIDATION.json':return 'Unregistered weather candidate: 48 native samples/672 getter comparisons; no weather MCP/player integration'
    if name=='STOCKPILE_MATRIX_VALIDATION.json':return 'Actual 101/100-room MCP scan/row bounds and ordered removal; fixed public fixture setup, not large-city cost or native byte/fault coverage'
    if name=='STOCKPILE_LIFECYCLE_SOURCE_REVIEW.json':return 'Manual selected shipped-source lifecycle/public fixture-route review; not a stable documented contract'
    if name=='STOCKPILE_LIFECYCLE_VALIDATION.json':return 'Actual copied-city same-ID replacement/removal MCP regression against unchanged published player; finite scope'
    if name in {'api-audit.json','API_DISCOVERY.json'}:return 'Generated current audit/pairing; declaration candidates are not runtime variables'
    if name.endswith('_REVIEW.json') or name=='REFERENCE_SOURCE_REVIEW.json':return 'Pinned source review; exact date/hash/scope, not an automatic refresh'
    if name.endswith('_VALIDATION.json') or name in {'provider-validation.json','validation-evidence.json'}:
        return 'Earlier pinned evidence; read hashes, historical scope and current PLAYER_CORE follow-up'
    if name.endswith('.json'):return 'Authored query/corpus/demo/discovery fixture; not live state or complete coverage'
    return 'Feature/reference guide; read linked build/evidence limits'


def index_text(root,paths):
    lines=['# Documentation and artifact index','',
        'Generated by `python3 dev/check_documentation.py --write-index`. Current guides can include historical sections; report filenames alone do not establish freshness. Read hashes/dates and parent links. This inventory contains every tracked or pending non-ignored Markdown file and root JSON artifact, not private runtime/game material.','',
        '| File | Role / evidence scope |','| --- | --- |']
    for path in paths:
        lines.append(f'| [{path.as_posix()}]({path.as_posix()}) | {scope(path)} |')
    return '\n'.join(lines)+'\n'


def local_link_errors(root,path):
    errors=[]
    for match in re.finditer(r'(?<!!)\[[^\]]+\]\(([^)]+)\)',path.read_text()):
        target=match.group(1).strip().split(' "',1)[0].strip('<>')
        parsed=urlsplit(target)
        if parsed.scheme or parsed.netloc or not parsed.path:continue
        if parsed.path.startswith('/'):
            errors.append(f'{path.relative_to(root)}: nonportable absolute local link {parsed.path}');continue
        linked=path.parent/unquote(parsed.path)
        if not linked.exists():errors.append(f'{path.relative_to(root)}: missing local link {target}')
    return errors


def check(root=ROOT,write=False):
    paths=inventory(root)
    if Path('DOCUMENTATION_INDEX.md') not in paths:paths.append(Path('DOCUMENTATION_INDEX.md'));paths.sort()
    expected=index_text(root,paths);index=root/'DOCUMENTATION_INDEX.md'
    if write:index.write_text(expected)
    errors=[]
    tracked=subprocess.check_output(['git','-C',str(root),'ls-files','-z']).split(b'\0')
    for name in tracked:
        if not name:continue
        base=Path(name.decode()).name
        if base=='auth.json' or base=='.env' or (base.startswith('.env.') and base!='.env.example'):
            errors.append('Private credential file is tracked: '+name.decode())
    if not index.is_file() or index.read_text()!=expected:errors.append('Documentation index is stale; run --write-index')
    for relative in paths:
        if relative.suffix=='.md' and (root/relative).is_file():errors.extend(local_link_errors(root,root/relative))
    # Selected current entry-point claims must follow source metadata, not historical numbers.
    from syx_knowledge import SEEDS
    audit=json.loads((root/'api-audit.json').read_text());release=json.loads((root/'USER_TEST_VALIDATION.json').read_text())
    count=len(audit['members']);model=release['requested_model']
    requirements={
        'README.md':[f'{len(SEEDS)} reviewed',model],
        'INSTALL.md':[f'{len(SEEDS)} reviewed'],
        'CHAT_BACKEND.md':[f'{len(SEEDS)} reviewed'],
        'API_ESTABLISHMENT.md':[f'current inventory contains {count} members'],
        'API_DISCOVERY.md':[f'All {count} production reference IDs'],
        'examples/providers/deepseek-api.env.example':[':-'+model],
        'CLAUDE.md':['@AGENTS.md'],
    }
    for name,phrases in requirements.items():
        content=(root/name).read_text()
        for phrase in phrases:
            if phrase not in content:errors.append(f'{name}: current fact missing: {phrase}')
    for name in ['README.md','ARCHITECTURE.md','INSTALL.md','CONTRIBUTING.md']:
        content=(root/name).read_text()
        for phrase in ['repository is private','merges nine reviewed','Search eleven reviewed',
                       'A custom in-game chat/authentication client remains future work',
                       'This is a required design, not implemented functionality','does not yet include that player-facing client']:
            if phrase in content:errors.append(f'{name}: stale current claim: {phrase}')
    if errors:raise ValueError('\n'.join(errors))
    return {'passed':True,'markdown_files_checked':sum(p.suffix=='.md' for p in paths),'indexed_artifacts':len(paths),
        'current_seed_count':len(SEEDS),'current_public_member_count':count,'current_player_model':model,
        'limits':['Checks local link destinations/inventory and selected current entry-point facts, not every semantic claim or external URL availability.',
                  'Historical evidence dates/hashes are preserved. No game/provider inference performed by this check.']}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write-index',action='store_true');a=p.parse_args()
    try:r=check(write=a.write_index)
    except (ValueError,OSError) as error:raise SystemExit(str(error))
    print(json.dumps(r,indent=2))
