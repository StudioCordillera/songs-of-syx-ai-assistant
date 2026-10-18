# Game API boundary — 0.12.0

The game-facing plugin runs inside Songs of Syx using `script.SCRIPT` and `SCRIPT_INSTANCE`. All gameplay observations originate from direct public game API calls on the game update thread via public `GAME.addAfterUpdate`. The Python MCP reads detached local exports; it does not inspect or control the game process itself.

The plugin has no private-field reflection, arbitrary object traversal, memory reading, native/window callback hooks, synthetic mouse/keyboard input, screenshot capture, OS automation, arbitrary method invocation or state writes. The previous raw-field and computer-use implementations have been removed from the current source and build. Old Git history is not the current supported implementation.

## Primary references and their limits

Read locally from the licensed 0.71.44 installation; proprietary source/docs are not redistributed:

| Reference | Establishes |
| --- | --- |
| `info/MAKE_A_MOD.txt` | Mod metadata, version folders and launcher mod discovery. |
| `info/scriptGuide.odt`, Overview / Project setup | Describes itself as semi-official; instructs adding `SongsOfSyx.jar` to the classpath and implementing `script.SCRIPT`. Also warns that much of the game code is undocumented. |
| `info/SongsOfSyx-sources.jar!/script/SCRIPT.java` | Documented factory, init/update/save/load, render/hover/key/mouse callbacks. We use creation/save/load and register a separate public after-update observer; observation-only implementation. |
| `info/SongsOfSyx-sources.jar!/game/GameDisposable.java` | Cleanup on next game initialization; does not promise an unload-to-menu callback. |
| Installed `SongsOfSyx.jar` public API | Compiles the typed collectors against the actual installed build; current loader uses `V71/script/*.jar`. |

A public method verified in shipped source is not automatically a documented, stable mod API. The guide supports script integration but does not individually document every statistic getter. This project makes that distinction explicit; no claim of a fully documented API for every game variable or menu is made. Where strict documentation or public accessibility is missing, leave the feature unavailable rather than add a reflection/native workaround.

## Explicit data mappings

All following collectors use direct public members from the shipped game. These are **source-verified public API mappings**, not separate official manuals documenting each getter:

| Export | Entry points checked against the game |
| --- | --- |
| Envelope | `VERSION.VERSION_STRING`, `GAME.updateI()`, `PATHS.currentMods()` |
| Population | `STATS.POP().POP.data`, `RACES.all()`, `HCLASSES.ALL()` |
| Resources and flows | `RESOURCES.ALL()`, `RESOURCE.owned()`, `SETT.ROOMS().STOCKPILE.tally()`, `GAME.player().res()` |
| Workforce | `SETT.ROOMS().ins()`, blueprint/room employment getters |
| Research | `TECHS.ALL()`, `GAME.player().tech().level()` |
| Entities | Snapshot: first 1,000 IDs/types/positions, explicit truncation. On-demand: `SETT.ENTITIES().getAllEnts()` bounded slot pages and `getByID(int)` for explicit IDs, plus fixed public class/type/position/stat getters |
| Selected individual stats | `Humanoid.indu()`, `Induvidual.clas()/hType()`, named `STAT.hasIndu()/indu()` and `INT_O.get/min/max`; raw units, partial schema |
| Aggregate stats | `STATS.COLLECTIONS()`, stat data/info/divider accessors |
| Trade / diplomacy | `GAME.player().trade`, `FACTIONS.active()`, `DIP.get()` |
| World / events | `WORLD.REGIONS().active()`, region public accessors, `GAME.events()`, `GAME.EVENT()` |
| Clock / map size | `GAME.SPEED`, `TIME`, `SETT.TWIDTH/THEIGHT` |
| Installed help | Public resource, technology and stat name/description accessors |

Each domain remains partial and includes a coverage reason. New data mappings need an entry here, primary-source review and a build/runtime check. Unknown mechanics/units remain explicit.

## UI and lifecycle

Partial UI context is now exported through direct public view/overlay/subject APIs; see API_ESTABLISHMENT.md and api-audit.json. Documented SCRIPT hover/key/mouse callbacks are observations/hooks, not an API for synthetic input or an accessibility tree. Do not substitute screenshots, OS input or private UI fields. The UI adapter reports selected subject identity, known overlay flags and room blueprint context. It explicitly excludes private tabs, exact selected room instances, tooltip text and a full panel hierarchy. These are source-verified APIs, not stable official contracts.

Cleanup occurs at next game initialization and JVM shutdown. Without an officially established unload callback, return-to-menu relies on the 30-second freshness timeout; the last snapshot may remain marked loaded in that window. This is a known limitation, not all-menu support.

## MCP and references

Thirteen read-only tools are available: UI context and API support/evidence, plus status, field schema discovery, bounded subtree reads, structured selection, query help, installed-reference search and reviewed external-source search. Filters, projections, joins and aggregates operate on exported public-API data. There is no raw Java field query or control mailbox. A bounded read-request transport asks the game update thread for fixed entity observations; it accepts no gameplay action, arbitrary method or object-member path.

Local JSON export and stdio MCP are the transport between the in-process plugin and the assistant. The selected official assistant client handles provider authentication/inference; see PROVIDERS.md. External guide summaries are reference evidence, not a source of live game state or executable instructions.

## Compiler inventory

The production references resolve to 246 public game API members. The metadata inventory includes source anchors and hashes; it does not enumerate every game variable or establish official stability. See API_ESTABLISHMENT.md for exact evidence levels and runtime checks.

## On-demand read transport — introduced in 0.7.0

`query_live_entities` writes a bounded request to the local private runtime directory. The file daemon parses a strict fixed-key protocol and hands an immutable request to the game update thread. Only that thread reads game APIs. It returns detached data; the daemon performs response serialization and atomic file replacement. The MCP client verifies request/session/version/time identity and bounds. Concurrent POSIX clients serialize requests with an OS-managed file lock. No network listener or process-inspection adapter is used.

Supported selection is finite: IDs, race/class/humanoid type, exclusive-upper tile bounds, up to four raw stat comparisons, and fixed projected fields. Explicit IDs use public `ENTETIES.getByID`; other selections scan at most 10,000 array slots per response. No writable game API is added. These new members are compiler/source audited; public accessibility is not an official stability contract. The shipped `getAllEnts` Javadoc explicitly describes its returned array as read-only; the adapter never changes its entries.

## Typed UI-content mapping — 0.8.0

Known popup/section roots expose public render objects. The adapter follows only mapped `GuiSection.elements` and `CLICKABLE.ClickSwitch.current` edges, reads `GTextR.text` labels, control active/selected flags and public internal bounds. This is bounded typed traversal of exposed UI data, not arbitrary object/field traversal. It does not invoke render, hover, input, click, layout, setter or gameplay methods. No private wrappers are unwrapped. General panel enumeration, final visibility and global stacking remain unsupported.

The seven production source files are included in the compiler inventory. The development extended fixture constructs game widgets and activates editors/retreat through public methods; none of those test mutations are included in the production JAR.

## Scene divisions and public hover flags — 0.9.0

Production reads `Army.divisions`, `Div.info`, `DivInfo.men/name`, `Div.menNrOf/index/indexArmy/race/morale/status` and `DivStatus.isFighting`, plus public `InterManager.isHovered` through known global/current-view managers. No battle orders, kill, speed, hover or click calls are added to production. Source boundary checks reject these concrete test-control call patterns in the mod tree; they supplement review rather than prove every possible mutation is absent.

Battle validation uses public game UI dispatch and public test-only orders/casualty setup. The pinned start button and actual private conclusion overlay are never obtained through reflection or a private field. The fixture constructs the public result-layout type to locate its Close control, then dispatches to the actual game manager; the game performs its normal protected callbacks internally. This is a source-verified test path, not a documented stable computer-use contract or a shipped action interface.

0.10.0 adds fixed person-assignment observations through public workplace/profession/home-coordinate/division readers. Each getter has explicit available/data status. Stored assignments do not establish current activity, occupancy, selected UI room or persistent IDs. See API_ESTABLISHMENT.md for source and runtime scope.

0.11.0 adds bounded retained entity captures using the same fixed public getters. Only detached DTOs are retained in the MCP server; no game object is cached there. `GAME.addAfterUpdate` is source/binary verified and runtime checked for UI-paused sampling, not a separately documented stable contract. Capture selection and legacy cursor limits are distinguished in QUERY_GUIDE.md.

## Finite tile access — 0.12.0

A separate TileReadRequest serves finite terrain/floor/room/mineral/path projections and AND filters, bounded to the instantiated map. Public routes include SETT.TERRAIN/FLOOR/ROOMS/MINERALS/PATH, their public maps and named getters. Coordinate-aware RoomSingleton name/anchor/area getters refresh reusable scratch caches; copied DTOs never retain those objects. No gameplay setter or UI-selected-room inference is added. Room map record IDs may be shared; only RoomInstance gets an instance ID. QUERY_GUIDE.md and agent-facing field definitions record units, source paths and limitations. Public source/binary accessibility still does not establish a separately documented stable getter contract.

## Optional mod-owned chat GUI

The experimental `ChatPanel` adds a separate public `InterGuisection`, public GUI widgets and public input-focus state for its own composer. `AssistantScript` schedules GUI work on the game update thread and moves detached chat IPC strings on its I/O worker. The production panel never invokes game input dispatch, existing gameplay controls or private UI traversal. These widget members are source/compiler-verified public APIs; this is not a claim of official stability. The compiler audit now inventories 275 public production member references. The older 246-member inventory is the observation-only 0.12.0 baseline. The test-only `ChatUiScenario` dispatches public manager clicks exclusively to the mod's own widgets in a throwaway profile; it is not packaged. See [the implementation](CHAT_BACKEND.md) and [its evidence](CHAT_VALIDATION.json).

The current shared-chat audit inventories 276 public production game members, all source/compiler matched and present in the offline catalog. Earlier 275/246-member inventories belong to their stated builds. No private game API reference was added. Current hashes and per-provider evidence are in CHAT_VALIDATION.json.

## Research relationships and allocation — development checkpoint

The research collector reads `TECH.requires`, public prerequisite records and technology costs, plus `PTech` level/cost getters and `TechCurr` total/allocated/frozen/available/penalty getters. `TECHS` expands the prerequisite closure during initialization; exported relationships include indirect requirements. No research setter, unlock action, history-writing `produced()` call, penalty-refreshing `isPenaltyLocked()` call or scratch-buffer affordability getter is used in production. Runtime/source evidence is in CORE_VALIDATION.json. The production audit now contains 293 public members; earlier counts refer to their stated builds. These mappings are source-verified public APIs, not separately documented stable contracts.

## Per-room production — development checkpoint

Only `ROOM_PRODUCER_INSTANCE.industry/industryI`, current `Industry.ins/outs/index`, and public `IndustryResource` resource/rate/day/dayPrev/year/yearPrev getters are read. Declaring owners and source hashes are in the 306-member public compiler audit. The scalar data getters internally access the room's public data interface; reviewed concrete implementations return their production storage without an update call. The adapter never obtains that array directly, retains game objects, calls `updateRoom`, changes recipes, increments quantities or calculates UI production forecasts. Room reads run on the update thread and are detached before I/O.

The production domain explicitly mixes campaign ledger and scene room data; nested coverage/scope, 2,000-row/10,000-room limits, failure counts and truncation are exported. Stored day accumulation includes fractional carry and ledger buckets are not forcibly refreshed. Public source-verified mappings still do not establish a stable official getter contract or every room's mechanics. See PRODUCTION_VALIDATION.json for the build-specific runtime scope.


## Installed room/currency references

Room descriptions use public `RoomBlueprintImp.info.name/desc` from mapped blueprint types. Research-currency descriptions use public `TECHS.COSTS` and `TechCurrency.bo` info fields. The 308-member compiler inventory remains entirely public. Fixed namespace IDs connect these installed descriptions to employment, current producer recipes, research currencies and known open room-blueprint panels; they are reference IDs, not game control handles. No private wiki/tooltip extraction or UI activation is performed in production. Active mods can override the installed descriptions. Exact runtime scope is in INSTALLED_HELP_VALIDATION.json.

## Regional population checkpoint

World data adds public `RD.RACES`, `RDRaces.population/all`, `RDRace.race/pop`, inherited `RData.get`, `Region.capitol` and `RegionInfo.area`. The stored getters do not force regional simulation updates. Demographic batches are bounded and detached; no backing-array layout, protected fields, population setter or private state is accessed. WORLD_VALIDATION.json pins the getter/MCP comparison and source review. These are source-verified public members, not separately documented stable SCRIPT contracts.

## Resource trade pipeline checkpoint

The adapter uses public Player.buyer/seller routes, PBuyer/PSeller counter accessors and public configuration readers, with TRADE_TYPE identifiers. Resource adapters are reached through their public base API; no inaccessible implementation field is accessed. The observer never calls reserve/deliver/remove/extract/set to obtain data. Those public mutations appear only in the isolated copied-game fixture to establish nonzero read cases. The staged city data is suppressed on battlefields and distinguished from the campaign ledger. TRADE_VALIDATION.json pins source review, compiler access and copied-game MCP checks; no separately documented stable getter contract is claimed.

## Per-room service counters

Only public `ROOM_SERVICER.service` and `RoomServiceInstance.total/available/reserved` are added. The three counter readers are checked as direct stored-field returns against the installed binary, with shipped-source anchors. No service reporting, finder query, reservation write, load/refresh or private implementation cast is used. The current compiler audit contains 346 public references and zero non-public references. The counters retain room-specific raw meanings, with no people/day or individual-access inference. See SERVICE_COUNTERS.md and SERVICE_VALIDATION.json.

## Configured cohort service permissions

The collector adds public RoomServiceAccess.ALL/stats/index, RoomService.room, StatServiceImp.permission, BOOLEANO.is and HCLASS_RACE.clP readers. Production uses the returned public boolean interface, never the private permission implementation or bitmap, and calls no setter or accessRequest. The configured flag is explicitly distinct from the individual eligibility rules found in shipped accessRequest source. Static source/binary review is scoped evidence, not an official stable contract or a general purity proof. City policy is unavailable on battlefields and incomplete setup. The compiler audit contains 353 public members and zero non-public references. See SERVICE_PERMISSIONS.md and SERVICE_VALIDATION.json.
