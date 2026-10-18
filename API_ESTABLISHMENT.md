# API establishment report — game 0.71.44

This report establishes what can be verified within the user's required in-process public-API boundary. It does not create an official guarantee on behalf of the game developer.

## Evidence levels

1. **Documented script contract:** the shipped semi-official script guide and SCRIPT interface describe script creation, updates and persistence callbacks. They do not document every game statistic or menu.
2. **Source-verified public API:** Java compiler attribution resolves each game member referenced by production mod code. The current inventory contains 375 members, all public. Of these, 374 match declaring type, name, arity and simple parameter types in shipped source; the remaining member is the compiler-generated enum `values()` method. Seven referenced members have their own Javadoc blocks; Javadoc presence does not establish semantics or stability. Script override contracts are reviewed separately from the member-reference inventory.
3. **Runtime evidence:** the isolated fixture exercises supported contexts using public game methods and a copied save. The production mod only observes. Test mutations and engine bootstrap code are never packaged into the mod.
4. **Unavailable/unvalidated:** missing public accessors and untested transitions stay explicit. No reflection, screenshot, native-input or package-access workaround is added.

The [official documentation project](https://github.com/songsofsyx/documentation) links the published guide. Its [getting-started page](https://songs-of-syx.readthedocs.io/en/latest/modding_getting_started.html), checked 2026-10-17, contains a heading but no API details. This does not supply the missing member-level contracts.

Runtime evidence spans the 0.12.0 spatial/scene fixtures, 0.11.0 retained-capture/context fixtures, 0.10.0 relationship fixture, 0.9.0 battle lifecycle fixture, 0.8.0 extended-context fixture, 0.7.0 scene/entity fixtures and 0.6.0 context fixture. Exact run scopes are recorded in VALIDATION.md and validation-evidence.json.

## Current coverage matrix

| Capability | Established access | Runtime scope / limits |
| --- | --- | --- |
| Exported state variables | 18 partial typed public-API domains; 375 referenced members in the audit | Existing copied save; not every variable or every entity attribute |
| Regional resource accrual/schedule | `RD.OUTPUT().get(TR.get(resource)).yearlyAccumilation.get(region)` and configured cyclic offset getter | Campaign resource-backed rows, bounded to 10,000 cells; stored accrual is not inventory/delivered total/ETA. See REGIONAL_OUTPUTS.md and REGIONAL_OUTPUT_VALIDATION.json |
| On-demand regional outputs | Same explicit public stored counter/schedule getters plus bounded active-registry bindings | Fixed region/resource matrix queries independent of cached rows. Separate live pages; not a retained/global transaction. See REGIONAL_LIVE_READS.md |
| Active view | `VIEW.current`, subview `isActive` | Settlement, world, settlement tactical HUD, generated deployment/engagement and controlled victory/defeat restoration, plus initial/terrain world generation; editor activation checked on a copied completed world |
| Selected subject | `UISubjects.current`, individual class/type and named `STAT.hasIndu` / `STAT.indu` getters | 58 individual statistics observed in the copied-save subject; values/min/max and installed-help reference IDs. Panel may remain behind a modal overlay |
| Room context | `UIRooms.openIs` and room-list membership | Room blueprint/table/detail presence exercised; exact selected instance unavailable |
| World faction panels | `UIFactions.openIs()` / `openIs(Faction)` / `diploIs(Faction)` | Active completed-world view only; bounded active-faction scan; underlying panel presence may be obscured by a modal. See WORLD_FACTION_CONTEXT.md |
| Game menu / confirmation | Public known interrupters and `isActivated` | Both exercised; menu subpages not enumerated |
| Management | `IManager.open` | Open/closed exercised; selected tab remains private |
| Encyclopedia | Known public WIKI interrupter | Open/closed exercised |
| Loading overlay | Known public ILoadScreen interrupter | Overlay flag exercised; actual save reload is a separate transition test |
| Save reload | Documented script creation plus session rotation | Copied save reloaded in the same process; new session verified |
| Main menu | No plugin context callback/accessor established | Fixture returns there; plugin uses freshness/unknown-state fallback, not menu identification |
| Full tooltip text | No read-only public enumeration established | Presence only; GBox text storage is private |
| Complete panel hierarchy / stacking | No public general enumeration/order established | Known overlay flags only; cannot select a topmost panel from these flags |
| All game variables / all menus | No complete public schema or contract established | Still unavailable; natural campaign outcomes/full combat history, complete world generation/editor workflows, menu subpages and every popup combination are not exhaustively tested |

## Scene scope and semantic checks

The snapshot identifies whether an instantiated settlement is a city or a generated battlefield. Domain scopes distinguish scene-local observations, campaign/player data, and mixed resource logistics. During initial world setup, seventeen domains are explicitly unavailable; settings remain observable. Generated terrain alone does not establish a completed playable world. The exact wizard stage remains private.

`RESOURCE.owned()` is a mixed logistics quantity: warehouse/hauler and import/export/station goods, including incoming station goods, minus player trade promises. It is not a warehouse count and may be negative. Resource field definitions identify this scope separately from stockpile storage/capacity. A development-only bytecode check verifies this getter's operations against the installed JAR. Three further checks confirm the public after-update dispatch, the exit-to-menu factory and the package-private engine-disposal contract. Only fingerprints, member names and conclusions are published, not proprietary method bodies.

## Agent-facing tools

`get_game_ui_context` returns a partial UI observation from the same snapshot as exported state, including active view, known overlay flags, selected subject identity and open room blueprints. Unsupported details have reasons. Selected objects describe underlying panels and may be obscured; “this” is not automatically resolved when a modal is open. Individual subject statistics must not be inferred from population aggregates.

`select_game_state` supports a `{"context":"/selected_subject/entity_id"}` expression and optional `include_ui_context: true`, using the same snapshot as the data query. Results carry source coverage and scope, including joined sources. The selected person has a dedicated `/selected_subject` export in the entities domain, independent of the bounded `/items` list. Named individual statistics are partial, not a complete attribute schema.

`get_game_api_support(query, offset, limit)` returns capability evidence/limits and a paginated, searchable compiler inventory with source paths, declaration lines, source hashes and mod call sites. It is usable without a loaded game. It does not expose a method-call or private-field interface.

Stale status now distinguishes `observed_game_loaded` from the current `game_loaded` value. Once observations expire, current loaded state is null/unknown and `get_game_ui_context` refuses the stale observation. A clock skew receives its own unknown-state reason.

## Reproduce the audit

Use a full JDK 17+ for the development audit (the mod itself still targets Java 16 bytecode):

```sh
python3 audit_api.py --game-dir '/path/to/Songs of Syx'
```

`SYX_JAVA_HOME` may point to a complete JDK. The audit uses compiler attribution with annotation processing disabled; it reads the licensed game JAR and shipped source archive as references. It writes `api-audit.json` and the metadata-only `syx_api_manifest.py`. No game method bodies or game state are bundled. Audit failure on non-public members or unresolved source anchors prevents regeneration.

`dev/ApiAudit.java` and the context test scenario are development tools, outside the production mod source tree. Test-only UI methods are excluded from the production member inventory and JAR.

## Remaining upstream/API gaps

An official complete state schema, a stable contract for individual getters, selected room-instance/tab readers, a general panel tree, tooltip text enumeration and a script-level unload/menu callback were not established. Existing private/package-private fields do not satisfy the boundary. These need an appropriate public API, official clarification/extension, or a narrower product promise. Further local tooling can inspect availability but cannot turn an undocumented/private implementation into an official public contract.

A concrete unsent proposal for these missing public contracts is recorded in UPSTREAM_API_REQUEST.md. It is not an implementation or official support promise.

## Selected individual data — 0.8.0

The entities domain includes a dedicated `selected_subject` object with identity, race, class, type and named statistics whose public `hasIndu()` advertises an individual getter. This path does not depend on the first-1,000 `/items` export. Each statistic provides raw integer value, getter bounds, coverage and a `reference_id`. Missing getters fail individually; unknown semantic units stay unknown. A selected person is not inferred from population statistics. A null selection remains null.

The installed-help search accepts an exact reference ID such as the returned `stat:N`, so an advisor can retrieve the matching in-game description rather than guessing the meaning from a numeric value. These descriptions are installed game/mod data, not an official stability promise. The original copied save has 295 entities. The 0.7.0 isolated fixture raises this to 1,395 temporary entities and verifies that a target beyond the prefix is available through both dedicated selection and on-demand requests.

## On-demand entity access — introduced in 0.7.0

Fixed public getters now serve bounded entity requests across the instantiated scene. Explicit IDs use `ENTETIES.getByID(int)`; broader filters use bounded read-only array traversal. The production compiler inventory includes this lookup's source declaration. Installed stat references advertise whether a named individual getter exists.

The isolated fixture adds temporary citizens to a copied game without saving it. It verifies 1,395 live entities, a selected target absent from the 1,000-row snapshot prefix, direct attribute/stat reads, combined class/race/type/tile/stat predicates, 18-page complete paused-scene traversal, unknown-stat rejection, concurrent MCP reads and same-response UI context. Fixture mutations are never part of production. No arbitrary-field or method-call interface was introduced.

This is more complete entity access, not a complete game-variable schema. Every page is a separate observation; generic entity histories/private AI remain unavailable. The 0.11.0 tools below add bounded retained paging. See QUERY_GUIDE.md and validation-evidence.json for exact scope.

## Exposed UI content and transitions — 0.8.0

`known_content` reads three public roots: primary popup, secondary popup and section. Typed mappings use `IPopup.current`, `InterGuisection.current`, `GuiSection.elements`, `CLICKABLE.ClickSwitch.current`, `GTextR.text`, public control flags and internal UI bounds. Opaque widgets are retained as opaque; no private label/input fields are read. The general interrupter collection is still private. Its nested iterator methods do not make the collection publicly enumerable.

Reads are bounded to 80 nodes total, depth six, 4,096 UTF-16 text characters and 512 per label. Shared references point to an observation-local node ID. These IDs are not action handles. Truncation, getter errors and unavailable text remain explicit. Visibility flags and known ancestors do not establish clipping, occlusion or final rendered visibility; child order does not establish global overlay stacking. Public label strings are not a reconstruction of rendered pixels or tooltip contents.

The isolated extended fixture checks sixteen phases: base city; primary/secondary popups; section; node/text/depth limits; closed content; text input without private-value export; full-screen prompt; copied-save reload; world editor; return to city with the editing workflow flag still set; battle setup editor; return to city; battle deployment; and public retreat restoring the city with a new session. Content widgets are constructed by the fixture using game APIs, so this is not a claim that every native game dialog is readable. Retreat is tested from deployment, not active fighting. The test-supplied exiter asserts the result; production does not expose an arbitrary battle-result event feed.

The snapshot now explains that WorldGen workflow flags can persist after editor exit. `active_view` identifies the current UI mode. The battle deployment flag is likewise described as a logical flag, not proof that simulation/combat is running; the pinned start overlay remains inaccessible through a public read getter.

## Running battles, scene divisions and input consumption — 0.9.0

The military domain includes `scene_armies` for the player/enemy armies of the instantiated city or battlefield. Nonempty/configured division rows expose scene division ID, army-local index, name, present/configured men, race, raw morale and the public `DivStatus.isFighting()` engagement flag. These are public getters/fields checked by the compiler inventory and copied-game runtime. They do not enumerate every campaign army, order, history or private AI attribute.

The engagement flag is a published worker-buffer observation. It can lag and remain true after men reach zero when battle workers pause for a conclusion. It is not an instantaneous combat indicator or complete damage/projectile log. Morale is a raw game factor; do not convert it to a percentage. Configured minus present men is not a general casualty measure. IDs belong to the observed scene; do not reuse them across scene regeneration/session changes.

`input_capture` reports latest public hover-dispatch consumption by global and current-view managers. `global_hover_consumed_without_known_overlay_flag` is the literal combination of those observations, not a dialog identity. A false value does not prove that no private overlay exists. No cursor target, complete input routing, global stacking or rendered visibility is established.

The nine-phase battle lifecycle fixture starts two generated battles through public `ViewSubSimple.uiManager` / `InterManager.hover` / `InterManager.click`, issues public melee orders, observes actual engine engagement, then applies deterministic test-only elimination to set up victory and defeat result paths. It closes the actual private result overlays through the public dispatcher using a public `UIBattleResult` layout reference. Test-supplied exiters verify VICTORY/DEFEAT, and both restore the copied city with new sessions. No native/OS input, screenshot, private overlay field or protected callback is read/invoked directly. These test actions are excluded from production.

The result overlay remains private and has no mapped public presence/title/content getter. Production reports counts, raw hover-consumption data and that unsupported reason; it does not fabricate a result dialog identity or expose an arbitrary battle-outcome feed. The fixture proves controlled paths, not natural campaign outcomes, battle AI quality, every combat condition or every result UI workflow.

## Broader declaration discovery

API_DISCOVERY.md records a separate compiler-based scan of the shipped source/archive pair: 2,052 public types and 17,442 declared public member candidates. It includes all 246 production references and retains unresolved source-anchor matches explicitly. Constructors, mutators and rendering APIs are candidates only; this is not live variable coverage. No new production methods are exposed by the catalog. The public CORE/CORE_STATE/menu declarations inspected in this pass still do not establish a current-menu getter or unload callback.

## Person relationships — 0.10.0

`query_live_entities` accepts `relationships` as an optional projected field. The selected-subject snapshot contains the same typed relationship DTO independently of the first-1,000 prefix. Each relationship has `available` and `data`: a successful getter returning no assignment object/coordinate returns null data; a getter exception returns unavailable with an error class. Non-humanoid projections return null. No new filter expression, arbitrary property traversal or action interface is introduced.

| Relationship | Public entry point and source implementation reviewed | Meaning / boundary |
| --- | --- | --- |
| workplace | `STATS.WORK().EMPLOYED.get(h)` via `StatObject.get`; `StatsWork.Work.get` reads the stored room index | Assigned room ID, blueprint key, name and anchor tile. Not current job execution, physical presence or the UI-selected room |
| profession | `STATS.WORK().profession.get(h.indu())`; `StatsWork.Profession.get` reads a stored blueprint index | Recorded profession blueprint. Do not substitute it for the current assigned workplace |
| home_assignment | `STATS.HOME().GETTER.hCoo(h)` | Stored assigned-home tile coordinates, copied immediately from a reusable scratch coordinate. Not current position, room-instance identity, occupancy or independently validated house existence |
| division | `Humanoid.division()` via `STATS.BATTLE().DIV.get`; `Div.index`, `indexArmy`, `player` | Scene division ID, army-local index and side, joinable with the observed scene-army division IDs. Not a persistent campaign army ID or private orders/history |

These public getters are source-verified rather than officially documented stable member contracts. Room and division IDs may be reused after deletion/regeneration; use session and observation provenance. Reads run only on the game update thread and detached DTOs contain no retained game objects or scratch coordinates.

The 1,395-entity copied-game fixture checks null and non-null assignments for all four relationships, selected-person parity beyond the bounded prefix, existing predicates, 18-page paused-scene traversal and concurrent MCP requests. Both the verifier and game process exit zero. It does not establish active-simulation consistency, every entity subtype or large-city performance. No production control methods are added.

## Retained entity observations and menu-pause sampling — 0.11.0

`capture_live_entities` copies one complete matching bounded selection through fixed public getters in a single `GAME.addAfterUpdate` callback. `read_entity_capture` pages server-local immutable encoded DTOs with their original tick/time/session and optional original UI context. Selection completeness is enforced within row/scan/stat/byte bounds; failures retain nothing. This does not synchronize all worker threads, enumerate the entire game schema or preserve observations indefinitely. See QUERY_GUIDE.md for limits.

The successful copied-game run captures 1,395 entities and reads 70 pages while the game advances from capture tick 2,493,770 to a later observed tick 2,493,869. Every page retains the original capture tick/time, excludes a newly created fixture citizen, and a new capture sees that citizen. Original UI context, concurrent MCP pages, byte bounds and row/scan failures pass. Both game and verifier exit zero. The eleven-context scenario also passes against this exact mod, including reload/session rotation and the stale/unknown main-menu fallback. Earlier battle/editor scenarios retain their earlier adapter/hash scope.

This work exposed that a UI pause at nonzero requested speed can skip SCRIPT resource updates. Sampling now uses public `GAME.addAfterUpdate`, checked against shipped source and installed bytecode and observed to refresh the menu/world context during that pause. This is a source-verified hook, not a new official stability promise. It still supplies no standalone main-menu accessor or immediate unload callback. Failed exploratory runs and fixture corrections are described in VALIDATION.md.

## Spatial public data — 0.12.0

`query_live_tiles` reads selected groups inside explicit bounds, combining terrain/floor/room-blueprint/mineral-resource, room-presence and throne-component filters. This expands the map domain beyond dimensions without exporting the entire tile map into every prompt. Fixed projections, bounded scans and per-observation provenance preserve the read-only boundary.

| Group | Source-verified route | Meaning / limit |
| --- | --- | --- |
| terrain | Terrain.get, TerrainTile.key/name/roofIs/isMassiveWall | Installed terrain identity and engine flags; no construction eligibility or final visibility |
| floor | Floors.getter and degrade.get | Floor key/name/road flag; degradation getter factor from shifted stored bits divided by seven, not remaining lifetime |
| room | ROOMS.map.get, Room.blueprint/index/name/mX/mY/area | Room record at explicit coordinates, including singleton records. Only RoomInstance has instance_room_id. Singleton area is furniture bounding area; no UI selection or usable-space/occupancy inference |
| minerals | Minables.getter, amountInt, amountD, value | Associated resource, stored 6-bit amount, amount/63 and one-bit richness value; no warehouse quantity, extracted yield or exhaustion forecast |
| path | PATHING.getAvailability and reachability.is | Raw availability fields and tile/orthogonal-neighbor component connection to the throne; no route for a particular citizen/army or construction guarantee |

Coordinate-aware singleton getters may update internal scratch caches; values are copied immediately. No game objects cross into the daemon or MCP. Six own Javadoc blocks in the current inventory do not establish stable official contracts for these fields. Exact runtime scope and failed exploratory setup are recorded in VALIDATION.md and validation-evidence.json.

The 0.12.0 clean run passes sixteen direct-getter point cases, 306 matching tiles across 33 paused-city pages, and all eight scene phases with both tile and legacy entity requests. Both game and verifier exit zero. Main-menu identity, arbitrary native dialogs, full active-combat tile semantics, complete world generation/editor workflows and performance remain unestablished.

The current workforce checkpoint has 358 compiler-resolved public references, all paired with the retained declaration catalog. WORKFORCE_CONTRACT_REVIEW.json and WORKFORCE_VALIDATION.json distinguish stored public-reader semantics from finite copied-game getter/arithmetic/join checks. PLAYER_CORE_VALIDATION.json pins the current full seven-group follow-up. These additions do not establish complete variables, exact selected-room identity or exhaustive menus.


The producer-degradation mapping brings the current compiler inventory to 359 public references, all paired with the checksum-verified retained declaration catalog. One new production reference is `RoomInstance.getDegrade()`; private/package implementation details are inspected statically only to establish its limited call chain. The observer never obtains a degrader handle or invokes maintenance. ROOM_DEGRADATION.md and DEGRADATION_CONTRACT_REVIEW.json distinguish the normalized thresholded base read from excluded chamber/construction semantics. This is shipped-source verification, not a new documented stable contract, complete modifier model or exhaustive room/menu coverage.


## Finite UI/lifecycle route review

UI_LIFECYCLE_BOUNDARY_REVIEW.json adds paired source/binary fingerprints, an ordinary-mod positive faction-observer compilation probe and six negative named-access probes. It distinguishes public stored observers from panel-binding/text-builder mutations and inaccessible live-object routes. WORLD_FACTION_CONTEXT.md describes the supported bounded faction mapping; selected room/region, complete management tabs, tooltip text and immediate unload remain unestablished. This finite review is not a proof that no other public mechanism exists.
