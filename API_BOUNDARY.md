# Game API boundary — 0.5.0

The game-facing plugin runs inside Songs of Syx using `script.SCRIPT` and `SCRIPT_INSTANCE`. All gameplay observations originate from direct public game API calls on the script update thread. The Python MCP reads detached local exports; it does not inspect or control the game process itself.

The plugin has no private-field reflection, arbitrary object traversal, memory reading, native/window callback hooks, synthetic mouse/keyboard input, screenshot capture, OS automation, arbitrary method invocation or state writes. The previous raw-field and computer-use implementations have been removed from the current source and build. Old Git history is not the current supported implementation.

## Primary references and their limits

Read locally from the licensed 0.71.44 installation; proprietary source/docs are not redistributed:

| Reference | Establishes |
| --- | --- |
| `info/MAKE_A_MOD.txt` | Mod metadata, version folders and launcher mod discovery. |
| `info/scriptGuide.odt`, Overview / Project setup | Describes itself as semi-official; instructs adding `SongsOfSyx.jar` to the classpath and implementing `script.SCRIPT`. Also warns that much of the game code is undocumented. |
| `info/SongsOfSyx-sources.jar!/script/SCRIPT.java` | Documented factory, init/update/save/load, render/hover/key/mouse callbacks. We use creation/update/save/load; observation-only implementation. |
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
| Entities | `SETT.ENTITIES().getAllEnts()`, IDs, positions, race; first 1,000, explicit truncation |
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

Nine read-only tools are available: UI context and API support/evidence, plus status, field schema discovery, bounded subtree reads, structured selection, query help, installed-reference search and reviewed external-source search. Filters, projections, joins and aggregates operate on exported public-API data. There is no raw Java field query or control mailbox.

Local JSON export and stdio MCP are the transport between the in-process plugin and the assistant. The assistant client handles OpenAI authentication/inference. External guide summaries are reference evidence, not a source of live game state or executable instructions.

## Compiler inventory

The production references resolve to 165 public game API members. The metadata inventory includes source anchors and hashes; it does not enumerate every game variable or establish official stability. See API_ESTABLISHMENT.md for exact evidence levels and runtime checks.
