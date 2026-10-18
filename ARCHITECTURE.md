# Architecture

See [the code map](REPOSITORY_MAP.md) for modules and [the query guide](QUERY_GUIDE.md) for schemas, limits and consistency. This describes the current implementation; [deferred chat/provider requirements](IN_GAME_CHAT.md) are not all implemented.

## Data flow and process ownership

1. The in-process Java SCRIPT registers public `GAME.addAfterUpdate`. Fixed typed collectors sample public game APIs on the update thread, including UI-paused simulation, and copy values into detached DTOs. UI context belongs to the same observation.
2. The mod's I/O worker serializes/publishes atomic local snapshots about every two wall-clock seconds while callbacks run. It parses fixed entity/tile request mailboxes but never traverses game objects on that thread. New-load/session rotation and JVM cleanup are separate from the freshness fallback.
3. The Python stdio MCP validates/caches snapshots and executes bounded selection locally. It exposes thirteen game-read-only tools: snapshot/query/schema/reference/context/discovery, live entity/tile reads and retained entity capture paging. A capture changes only the server's local cache, never the game.
4. The mod-owned chat panel exchanges detached strings through local IPC. The Python coordinator owns SQLite histories, cancellation and bounded tool/model orchestration. DeepSeek inference occurs here, not in Java or the MCP bridge. The optional advanced Claude SDK route uses an isolated worker; provider/account expansion remains deferred.
5. The simple player uses explicit `deepseek-v4-pro` with no Flash fallback or login/provider/debug controls. Raw bounded tool events remain private in SQLite, not the visible transcript. The provider receives selected observations/retrieved passages according to the chosen chat route.

No remote listener, private reflection, arbitrary field/method tool, process-memory reader, screenshot, native game automation or gameplay mutation is shipped. Mod-owned public widgets are not an API for driving other game controls. Test-only public actions are confined to disposable path-validated copied-game fixtures and are never packaged into the mod.

## Cached observations and selection

Snapshots contain game version/mods, session/sequence/tick/time, scene/UI context, installed help and eighteen partial domains. Snapshot input is capped at 16 MiB. A batch shares one cached observation; an explicit snapshot pin rejects a mismatch rather than silently substituting another. Null, unavailable, zero, skipped/failed rows and collection truncation are distinct. Ancestor diagnostics follow paged data, joins and aggregates; exported totals do not prove complete city coverage.

Room/resource/race/region keys have explicit mappings and scope. Room IDs can be reused even within a session. Recorded workplace/profession/home/division assignments do not prove current activity or occupancy. Stored production buckets/factors/degradation do not establish exact sample age, current throughput or complete bonuses. Source-backed field definitions and feature guides carry those limits.

## On-demand entities and retained captures

Live entity requests use fixed independently validated keys. The update callback performs a named-ID lookup or bounded scene-slot scan, optional AND predicates (including recorded workplace), named individual stats and chosen projections. Each response carries its own observation/context; live cursor pages are separate mutable observations.

Live bounds include 8 KiB request, 64 KiB response, eight-second client deadline, 10,000 slots, 100 rows, four stat predicates and 100 projected stat cells. Capture protocol 2 instead requires origin cursor/ID projection and bounds the complete matching selection to 100,000 slots, 2,000 rows, 4,000 stat cells and 2 MiB. Incomplete scans, extra rows or predicate errors retain nothing. The MCP cache holds at most three immutable encoded captures for 120 seconds; token pages preserve original tick/time/context and require a fresh same-session/version game status. No global battle/simulation-worker transaction is claimed.

## Spatial reads

Tile requests share the POSIX request lock with entities. Fixed rectangle/filter/projection reads run only in the after-update observer, scan at most 4,096 tiles and return at most 100 rows within 64 KiB. Upper coordinate bounds are exclusive; cursors are row-major rectangle offsets. Each page is a separate observation: entity tokens do not retain tiles. Group available/data and predicate errors distinguish failure from absent floor/room/mineral. Coordinate rooms are not UI selections, and path flags are not a specific person's route. Public singleton scratch values are copied immediately. Retained spatial selection remains open.

## UI and lifecycle limits

Fixed public view/overlay/subject APIs expose active views, selected-person data, open room blueprint and bounded public popup/section labels/controls. Opaque wrappers, truncation and read errors remain explicit. Known overlays do not establish global stacking/topmost visibility; selected room instances, tooltips and management tabs remain unavailable.

There is no established immediate unload-to-menu callback. A stopped export may remain apparently current for up to 30 seconds, then loaded/current state becomes unknown. Next initialization rotates the session and cleans old transport; JVM shutdown is separately observed. Published battle-worker engagement can lag or persist while paused and is not a synchronized combat log. See [API establishment](API_ESTABLISHMENT.md) and exact [validation scopes](VALIDATION.md).

## References and trust

Installed descriptions retain exact IDs, version and active mods. Thirteen reviewed external summaries retain URLs, authority, retrieval dates and compatibility caveats. Whole-word relevance ranks before compatibility/authority tie-breakers; scores are not factual confidence. Historical developer guidance may have unknown current-patch compatibility. Retrieved strings are data, never executable instructions. Automatic crawling/refresh and comprehensive guide coverage remain unimplemented.

## Boundaries, providers and delivery

Documented SCRIPT lifecycle contracts are distinct from public members verified in shipped source/binaries. Compiler audit metadata and the broader offline declaration catalog are provenance/discovery aids, not arbitrary API invocation or counts of supported variables.

The shared chat/history client is implemented and has finite DeepSeek Pro player evidence. Advanced Claude subscription evidence is older and bounded; Claude API inference, native OpenAI account integration, all-screen/keyboard acceptance and in-game setup are incomplete. An existing signed-in external Codex/Claude MCP client is a separate development bridge. The local MCP itself performs no inference and needs no provider key.

`make_user_test.py` packages only our classes/Python/player files from matching provider/source evidence. Freshness checks protect the tracked latest ZIP; promotion retains its tested predecessor. Exact USER_TEST/PLAYER_CORE reports identify tested builds, while older reports retain their hashes. [CONTRIBUTING.md](CONTRIBUTING.md) covers collaborative reconciliation and candidate validation.
