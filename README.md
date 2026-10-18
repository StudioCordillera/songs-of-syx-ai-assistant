# Songs of Syx AI Assistant

A local Java mod and MCP server that let an assistant inspect a loaded Songs of Syx game, request selected data, and advise the player with cited evidence.

**0.12.0 observation baseline, with an experimental chat development implementation.**

[Chat backend and opt-in in-game panel](CHAT_BACKEND.md): authenticated DeepSeek API and Claude subscription conversations, separate session/chat histories, cited MCP observations, expandable evidence and export/delete controls. Claude API is implemented but awaiting credential validation; OpenAI sign-in and full client acceptance remain pending.

**Experimental working prototype for game 0.71.44 (Steam build 23998889).** Tested against a copied save on Linux. Other game version strings are rejected by the runtime guard; the tested binary hashes are recorded in the audit, and the guard does not attest the loaded JAR hash. This is not a finished in-game chat application.

## What works

- Request specific entities across the instantiated scene through fixed public getters: IDs, race/class/type, tile bounds, individual-stat comparisons and chosen attributes. Bounded cursor pages reach beyond the snapshot prefix.
- Discover explicitly exported fields and request selected public-API observations without dumping the whole snapshot into the model.
- Filter, project, join, group, aggregate, sort and paginate normalized snapshot data. Batched queries share one snapshot.
- Eighteen explicitly partial domain collectors: population, resources, production, employment, services, housing, health, law, happiness, research, trade, diplomacy, military, world, map, entities, events and settings.
- Per-room current recipe input/output rows and stored production quantities, joinable to employment and resources; explicit caps, mixed scopes and stored-bucket caveats. See [production evidence](PRODUCTION_VALIDATION.json).
- Research prerequisite relationships, per-currency next-level costs and point allocation through public getters; discover meanings before treating these as an unlock decision. See [core development evidence](CORE_VALIDATION.json) and [data coverage](DATA_COVERAGE.md).
- Search resource, technology, stat, room and research-currency descriptions loaded by the game. The latest copied-save test produced 834 reference records, tagged with the exact version and active mods.
- Search a small reviewed external corpus with direct links, author/authority, retrieval date and compatibility warnings. Whole-word relevance ranks first; version compatibility and official/developer authority break ties. An authority filter is available.
- On-demand person relationships: assigned workplace room, recorded profession, stored home coordinates and scene division. Absence and getter failure stay distinct.
- Selected citizen identity/class/type and named individual statistics, linked to installed descriptions and independent of the bounded entity list.
- Bounded label/control observations from exposed popup and section roots, with explicit opaque/truncated content. Editor activation and retreat-to-city transitions are checked in an isolated copied game.
- Scene division counts, raw morale and published engagement flags, with stale-buffer limits. Controlled running-battle victory/defeat paths are checked using public game UI dispatch in the test fixture.
- Partial UI context through public view/overlay/subject APIs, plus a searchable API evidence catalog. See [the establishment report](API_ESTABLISHMENT.md).
- Game access exclusively through the in-process script mod and mapped public game APIs. No private reflection, screenshot capture or native/input hooks.

Read the [query guide](QUERY_GUIDE.md), [installation instructions](INSTALL.md), [architecture](ARCHITECTURE.md), [validation report](VALIDATION.md), [API boundary and source provenance](API_BOUNDARY.md), and [reference register](REFERENCES.md).

## Quick start

Python 3.11+ and a full JDK 17+ are required for the development tests and API audits below. The mod targets Java 16 bytecode. Use your licensed game installation:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m pytest -q
python3 build_mod.py --game-dir '/path/to/Songs of Syx'
```

Copy `dist/syx-ai-assistant` into the game's user mod directory, enable it in the launcher, then load a game. Configure your existing Codex client using [codex.example.toml](codex.example.toml). Both processes must use the same `SYX_STATE_DIR`; the default is `~/.local/share/syx-assistant`. Windows uses `.venv\Scripts\syx-mcp.exe`.

Install the optional reviewed starter summaries with `.venv/bin/syx-knowledge`. Without a corpus, installed-game references still work. Call `game_status`, then `game_query_help` to get started.

## Subscription connection

Use an existing Codex client signed in with ChatGPT and connect this local MCP server. The client supplies the model and its subscription entitlements; the MCP server makes no inference calls and needs no OpenAI credentials.

The experimental shared in-game panel has bounded DeepSeek API and Claude subscription acceptance evidence. Native OpenAI plan integration remains pending. OpenAI's eligible local/open-source application route requires registration and consent; native computer use and hosted MCP have preview restrictions. See the [connection decision](ARCHITECTURE.md#openai-connection). An API-key route would have separate billing.

## Current limits

All normalized domains are partial; complete state access is not claimed. Legacy on-demand cursor pages are separate mutable observations. New bounded entity captures retain one observation for paging; they are not a global simulation-worker transaction. This transport currently requires a POSIX MCP host. Public API mappings are verified against shipped source, while the script lifecycle is documented in the shipped guide and SCRIPT interface. Much of the game code is undocumented; public does not mean a stable officially documented contract. See API_BOUNDARY.md. UI context is partial: view, known overlays, selected subject, room blueprint and bounded exposed popup/section content. Full tooltip text, selected room instance, management tab and arbitrary panel order are unavailable. Screenshots and game control remain excluded. The external corpus starts with nine reviewed summaries; automatic web retrieval and comprehensive coverage remain unimplemented. Return-to-menu detection relies on freshness expiry (up to 30 seconds); cleanup is established for next initialization and JVM shutdown.

Do not commit game binaries, game source, saves, snapshots, screenshots of private saves, account credentials or copied full guides. The repository is public; no source license has been selected for redistribution.

For the broader offline public-declaration inventory and remaining mapping work, see [API_DISCOVERY.md](API_DISCOVERY.md). It catalogs candidate declarations without executing game code or automatically exposing mutators.

Provider requirements and connection profiles are tracked in [PROVIDERS.md](PROVIDERS.md). DeepSeek API and Claude subscription have bounded in-game acceptance evidence in CHAT_VALIDATION.json. Claude API, native OpenAI integration and the remaining model/client acceptance gates stay open.

0.11.0 adds retained bounded entity selections (`capture_live_entities` / `read_entity_capture`) and refreshes observations through public `GAME.addAfterUpdate`, including UI-paused nonzero-speed menus. The copied-game run retained 1,395 entities across 70 pages while simulation advanced. Full state/schema and all-menu coverage remain unfinished.

0.12.0 adds bounded spatial queries for terrain, floors, coordinate-aware rooms, minerals and path flags. Request a rectangle, combine fixed filters and project just the needed groups with `query_live_tiles`; read the meanings and limits in QUERY_GUIDE.md. All domains remain partial.

**Required player interface:** every supported subscription/API option must provide the same [in-game chat client and session/chat history](IN_GAME_CHAT.md). DeepSeek needs a first-class API path in that interface; external client profiles are development aids. The development implementation provides the shared panel and durable histories; see CHAT_BACKEND.md for current routes and open acceptance gates.

OpenAI subscription sign-in and transport are [prepared separately](OPENAI_CONNECTION.md); final account-access approval and authenticated integration remain pending.
