# Songs of Syx AI Assistant

A local Java mod and MCP server for selective game observations, UI-aware questions and cited guidance. The current player build targets **Songs of Syx 0.71.44**. Core coverage is partial; provider/account expansion is deferred.

## Play the tested build

[Download the latest tested Linux ZIP](https://github.com/StudioCordillera/songs-of-syx-ai-assistant/raw/refs/heads/main/releases/latest-user-test.zip), extract it, run `python3 install-mod.py`, then `sh start-chat.sh`. Enable the mod, load a game and open **AI chat → New chat**. Python and first-launch internet access for dependencies are required; no Java compiler is needed to use the bundle.

The player gets **DeepSeek Pro** (`deepseek-v4-pro`), a simple chat list/transcript, wrapped composer, Send/Stop and durable local histories. The helper keeps its key outside version control and the published bundle; it never bundles credentials. Login/provider/debug controls are hidden and raw tool evidence stays in private history. See [player instructions](user_test/README.txt), [installation](INSTALL.md) and [build/rollback policy](releases/README.md).

## Start collaborating

Read [shared instructions](AGENTS.md), the [repository map](REPOSITORY_MAP.md), [contributor/test workflow](CONTRIBUTING.md), [current handoff](WORK_STATUS.md) and [roadmap](ROADMAP.md). Claude's [entry file](CLAUDE.md) imports the same shared instructions. The [documentation index](DOCUMENTATION_INDEX.md) maps current guides and historical evidence.

At the start of every run, and again before publishing:

```sh
python3 dev/collaboration_status.py
```

It fetches remote branches/tags and reports remote changes, overlapping unpublished work and a changed tracked player bundle. It never merges or discards files. Compare competing implementations and their tests; keep the stronger solution or combine them, regardless of author. [Reconciliation instructions](CONTRIBUTING.md#reconcile-concurrent-work) explain preservation and acceptance.

## What is implemented

- Eighteen partial domains spanning population, resources, production, employment, services, housing, health, law, happiness, research, trade, diplomacy, military, world, map, entities, events and settings.
- Discoverable fields/provenance and bounded filters, projections, joins, grouping, arithmetic, aggregates, sorting and pagination. Query batches share one cached observation.
- On-demand person/stat/relationship reads beyond the exported prefix, recorded-workplace filtering and retained entity captures for consistent bounded paging. Separate live cursor pages remain different observations.
- Bounded terrain/floor/room/mineral/path queries and [retained tile selections](TILE_CAPTURES.md): one callback, up to 4,096 scanned tiles, 100 matches and 64 KiB, then stable paging. Live tile pages remain separate observations; neither route identifies the UI-selected room.
- Recipe/recorded-flow and staffing joins, stored workforce factors and producer degradation with explicit units, threshold, age and completeness limits. Configured service permissions and stored service-point counters are distinct from individual access/daily capacity.
- Bounded city stockpile reservations and assigned capacity, city trade bookkeeping, regional population, [regional resource accruals and configured schedules](REGIONAL_OUTPUTS.md), and research relationships. [Stockpile counters](STOCKPILE_BOOKKEEPING.md) distinguish reserved goods from incoming capacity and keep zero capacity/unavailable scenes explicit. [Data coverage](DATA_COVERAGE.md) describes fields and missing mappings.
- Installed help (834 references in the copied-game fixture) and 13 reviewed external summaries, with direct URLs, authority and version caveats. Lexical relevance ranks before compatibility/authority tie-breakers. See [reference register](REFERENCES.md) and [retrieval evaluation](GUIDANCE_EVALUATION.md).
- [On-demand regional output selections](REGIONAL_LIVE_READS.md) read explicit active-region/resource cells independently of cached export limits. [Retained regional captures](REGIONAL_CAPTURES.md) keep one complete selection consistent across pages: up to 10,000 requested cells, 2,000 matching rows and 2 MiB, with failure refusal and original provenance.
- [World faction panel context](WORLD_FACTION_CONTEXT.md): bounded active-faction identity and stored diplomacy-tab observations, with same-snapshot diplomacy joins and explicit modal/inactive-view limits.
- [World list-panel context](WORLD_LIST_CONTEXT.md): army, realm and region-browser membership with unavailable/null, modal/hidden UI and same-observation query rules. No selected army/region inference.
- Partial public-API UI context: active views, known overlays, selected person, open room blueprint and bounded exposed popup/section content. [UI/API limits](API_ESTABLISHMENT.md) remain explicit.

The production bridge uses explicit **in-process public game APIs**, detached DTOs and no private reflection, process memory, screenshots, native input or gameplay-control tools. Most getters are verified against shipped source/binaries; they are not separately documented stable mod contracts. See [API boundary](API_BOUNDARY.md), [architecture](ARCHITECTURE.md) and [query guide](QUERY_GUIDE.md).

## Development

Python 3.11+, Git and a full JDK 17+ are needed for the offline suite/compiler audits. Licensed game files and a working native desktop/OpenGL environment are needed for copied-game tests. Keys are unnecessary for offline tests:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m pytest -q
python3 dev/check_documentation.py
python3 dev/check_user_test_release.py
```

[CONTRIBUTING.md](CONTRIBUTING.md) gives portable game/JDK configuration and a repeatable two-turn Pro integration command. Claude on this shared device uses the ignored local `.env` through `--env-file .env`; other environments may supply `DEEPSEEK_API_KEY` directly. Paid tests run only when explicitly invoked. No contributor must rely on another person's credential path or ignored tools; LOCAL_DEVELOPMENT.md records conveniences available on this shared device.

## Evidence and remaining gaps

[USER_TEST_VALIDATION.json](USER_TEST_VALIDATION.json) pins the published player source/JAR and provider check. [PLAYER_CORE_VALIDATION.json](PLAYER_CORE_VALIDATION.json) pins seven finite copied-save groups. The degradation mapping also has a separate controlled nonzero-room test; it does not establish natural wear or output effects. [VALIDATION.md](VALIDATION.md) separates current and historical evidence; old hashes and retrieval dates are not relabeled as new tests.

Complete variables/production modifiers, larger retained spatial selections, larger-city costs and other collector cap/fault paths, broader current-version references, physical keyboard/display testing and exhaustive menus remain open. Exact selected-room identity, tooltip/tab hierarchy and immediate unload-to-menu identification are unestablished. Return to menu can leave the previous observation apparently current for up to 30 seconds, then state becomes unknown.

The advanced [chat/provider implementation](CHAT_BACKEND.md) has older bounded Claude subscription evidence; Claude API inference and native OpenAI integration remain incomplete. The current player remains simple Pro. External [Codex](codex.example.toml)/[Claude](claude.mcp.example.json) MCP profiles are development bridges, not completion of in-game account support. [Provider](PROVIDERS.md) and [chat requirements](IN_GAME_CHAT.md) retain deferred gates.

The repository is public. No redistribution license has been selected. Do not commit keys, auth files, licensed game binaries/source, saves, snapshots, histories or copied full guides.
