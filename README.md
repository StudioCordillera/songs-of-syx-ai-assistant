# Songs of Syx AI Assistant

A local Java mod and MCP server that let an assistant inspect a loaded Songs of Syx game, request selected data, and advise the player with cited evidence.

**Experimental working prototype for game 0.71.44 (Steam build 23998889).** Tested against a copied save on Linux. Other builds are rejected by the runtime guard. This is not a finished in-game chat application.

## What works

- Discover game fields and request targeted reads of the reachable game-owned object graph, including private variables, without dumping the whole state into the model.
- Filter, project, join, group, aggregate, sort and paginate normalized snapshot data. Batched queries share one snapshot; targeted live field reads share one game update tick.
- Eighteen explicitly partial domain collectors: population, resources, production, employment, services, housing, health, law, happiness, research, trade, diplomacy, military, world, map, entities, events and settings.
- Search resource, technology and stat descriptions loaded by the game. The copied-save test produced 720 reference records, tagged with the exact version and active mods.
- Search a small reviewed external corpus with direct links, author/authority, retrieval date and compatibility warnings. Official/developer evidence ranks first; an authority filter is available.
- Optional game-only screenshots and UI input. The player must enable a five-minute control grant in the game; physical input and Stop revoke it.

Read the [query guide](QUERY_GUIDE.md), [installation instructions](INSTALL.md), [architecture](ARCHITECTURE.md), [validation report](VALIDATION.md), [computer-use limitations](COMPUTER_USE.md), and [reference register](REFERENCES.md).

## Quick start

Python 3.11+ and a full JDK 16+ are required to build. Use your licensed game installation:

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

A custom in-game chat UI and its supported subscription login remain future work. OpenAI's eligible local/open-source application route requires registration and consent; native computer use and hosted MCP have preview restrictions. See the [connection decision](ARCHITECTURE.md#openai-connection). An API-key route would have separate billing.

## Current limits

Raw field discovery exposes a broad reachable game graph, not every value in the JVM. Native/non-game objects are blocked, result sizes and traversal are bounded, and raw field meanings/units may be undocumented. All normalized domains are partial. Large entity collections, tile inspection and relationships need further typed collectors. The external corpus starts with two reviewed summaries; automatic web retrieval, refresh and comprehensive reference coverage are not implemented.

Do not commit game binaries, game source, saves, snapshots, screenshots of private saves, account credentials or copied full guides. The repository is private; no source license has been selected for redistribution.
