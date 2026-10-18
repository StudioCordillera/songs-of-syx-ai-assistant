# Repository map

Start with [README](README.md), [shared agent instructions](AGENTS.md), [contributor workflow](CONTRIBUTING.md), [handoff](WORK_STATUS.md) and [roadmap](ROADMAP.md). [DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md) lists every tracked Markdown guide and root JSON artifact, with current/historical scope. Counts and exact tested hashes come from the reports, not this map.

## Runtime data flow

Game process public after-update callback → detached Java DTOs → local snapshot/fixed request mailboxes → Python stdio MCP → selected observations/reference passages → local chat coordinator → DeepSeek Pro → mod-owned transcript. SQLite holds private session/chat history. The I/O worker and MCP never traverse live game objects. The model gets read-only tools, not a game-control, shell or screenshot interface. See [architecture](ARCHITECTURE.md).

## Game bridge: mod/src/main/java/syx/assistant/

| File | Responsibility / edit boundary |
| --- | --- |
| AssistantScript.java | SCRIPT lifecycle, after-update registration, game-thread/worker handoff, snapshot/mailbox/chat IPC and supported-version guard. |
| StateCollector.java | Eighteen partial domains, installed help, typed field definitions and bounded room/resource/region relationships. New fields require provenance, bounds and getter/MCP validation. |
| UiContextCollector.java | Scene/view/overlay/subject/room-blueprint and bounded world-faction-panel context through mapped public getters. No private selected-room fallback. |
| UiContentCollector.java | Bounded exposed popup/section labels/controls, ancestry and opaque/error/truncation markers. |
| EntityReadRequest.java | Strict live/capture protocol parsing, finite predicates/projections, public entity/stat/workplace reads on the update thread. |
| TileReadRequest.java | Strict rectangle/filter/projection protocol and bounded terrain/floor/room/mineral/path reads. |
| ChatPanel.java | Our own simple/advanced public GUI widgets, text/focus, chat list/transcript/composer; no gameplay-control dispatch. |
| JsonWriter.java | Detached DTO encoding; no game traversal. |

Only these production classes are packaged. `mod/tests/` contains non-shipped bootstrap and public-API fixtures; some deliberately mutate only copied in-process game state. `LiveSmoke.java` / PathCheck enforce copied save and isolated user.home before engine start. `DegradationPositiveScenario` is a test-only public maintenance action, never an MCP action.

## Python runtime modules

| Module | Responsibility |
| --- | --- |
| syx_mcp.py | Snapshot/domain models, freshness/cache, Advisor and fifteen tool registrations; stdio entry point. |
| syx_query.py | Fixed snapshot selection language, joins/arithmetic/grouping/sort, shared work/row/source budgets and collection diagnostics. |
| syx_live.py | Strict entity selections, live/capture wire transport and agent-facing schema/help. |
| syx_capture.py | Immutable encoded retained entity/tile observations in separate bounded pools, server-local tokens, shared paging/freshness guards and original provenance. |
| syx_tiles.py | Strict live/capture tile selection schemas, fixed mailbox and same-response context checks; captures must fit one callback. |
| syx_knowledge.py | Reviewed SEEDS, non-destructive corpus merge and knowledge CLI. Search/ranking lives in Advisor in syx_mcp.py. |
| syx_api_support.py | Curated capability routing, source/evidence/limit descriptions and explicit gaps; not arbitrary invocation. |
| syx_api_manifest.py | Generated compiler audit metadata. Regenerate with audit_api.py; never hand-merge it. |
| syx_chat_service.py | Local IPC coordinator, explicit game attachment, simple/advanced routes, key boundaries and lifecycle. |
| syx_chat.py | Bounded native DeepSeek conversation/tool loop and citation/evidence integration. |
| syx_deepseek.py | Streaming native API protocol and explicit model/endpoint errors; simple chat selects Pro explicitly. |
| syx_chat_store.py | Private SQLite chat/session/event persistence, recovery, secret redaction, local export/delete. |
| syx_claude.py / syx_claude_worker.py | Advanced official SDK worker route, isolated tools/auth context; provider expansion deferred. |
| syx_openai_auth.py / syx_openai_plan.py | Prepared/deferred official account/Responses work, mostly mocked evidence; not completed player integration. |

## Build, validation and release

| Entry point | Purpose / requirements |
| --- | --- |
| pyproject.toml | Python modules, CLI entry points, pinned MCP plus optional development/SDK/auth dependencies. |
| build_mod.py | Compile only our Java against a licensed game JAR, release 16; creates _Info and our own mod JAR. |
| audit_api.py + dev/ApiAudit.java | Compiler-resolved production game members, public-access/source anchors and critical bytecode checks; regenerates api-audit.json/syx_api_manifest.py. |
| catalog_api.py + dev/GameApiCatalog.java | Offline public declaration candidate catalog under ignored build/; API_DISCOVERY.json is the retained summary/current production pairing. No runtime getter safety is inferred. |
| dev/verify_*_contract.py, verify_bytecode.py, review_production_modifier_boundary.py, review_stockpile_boundary.py, review_ui_lifecycle_boundary.py, review_regional_output_boundary.py, verify_production_periods.py | Static licensed source/binary review without initializing game classes; publish metadata/hashes/conclusions only. |
| test_*.py | Offline regression tests with mock providers/synthetic observations/local Git repos. No key or paid inference needed. |
| mod/tests/ + dev/verify_*.py | Explicit licensed-game getter/MCP/context/cap/lifecycle fixtures and metadata-only reports. Read each verifier's scope. |
| dev/run_read_fixture.py | Fixed tile/entity/world-faction-context regressions and a regional-output candidate-reader probe against published/candidate player; locks/restores copied mod and checks copied-save integrity. |
| dev/run_stockpile_probe.py | Published/candidate JAR copied-city stockpile readers, overload/sum/lifecycle checks and global reservation DTO/MCP parity; locks/restores copied mod, no provider calls. |
| dev/run_player_chat_check.py | Explicit paid two-turn Pro test using a manually supplied key; builds/audits current source, isolates game/MCP credentials and restores copied-profile mod. |
| dev/verify_user_test_chat.py | Verify an already executed native Pro chat/history; does not itself launch the game or provider. |
| dev/verify_current_player_core.py | Exact published/candidate JAR through seven copied-save groups, no inference. |
| dev/profile_collection_cost.py / benchmark_selective_queries.py | Descriptive collection/selection timings for exact published payload; audited game/source pair, copied mod restore/save integrity and shared lock. Current small-city evidence is separate from historical timings and larger-city acceptance. |
| make_user_test.py | Package only our Java/Python/player assets from matching provider/source evidence; retain prior tested ZIP. |
| dev/check_user_test_release.py | Standard-library freshness/hash checker for current production payload; CI/pre-push gate, not a game playtest. |
| dev/game_fixture_lock.py | Machine-wide advisory lock for cooperating native runners on this shared device; core/chat/cost acquire it automatically. |
| dev/collaboration_status.py | Fetch refs/tags and report divergence, overlap and tracked release changes; no automatic integration or file mutation. |
| dev/check_documentation.py | Check local links, documentation inventory and selected current facts; --write-index refreshes the deterministic index. |
| .github/workflows/check-user-test.yml / .githooks/pre-push | Automated freshness/documentation checks. Licensed game/provider tests remain explicit local work. |

The release whitelist is `make_user_test.MODULES`, five files in `user_test/`, own mod classes and _Info. The tracked `releases/latest-user-test.zip` must match production source on published main; `previous-user-test.zip` retains its tested predecessor. Neither contains game binaries/source, saves, keys, histories or full guides. `releases/latest-user-test.json` embeds the exact validation and checksums. Documentation/developer-tool-only changes leave the unchanged playable payload intact.

## Data, examples and evidence

- `snapshot.example.json` / `corpus.example.json`: explicitly synthetic examples, never live fallback data.
- `guidance-questions.json`: authored retrieval/support/caveat cases; `source-directory.json` is discovery/routing material, not proof every URL was reviewed.
- `*-query-example.json` / `selective-query-examples.json`: executable selection examples; sort paths refer to projected result names.
- `USER_TEST_VALIDATION.json`: published player JAR/Python/provider evidence; `PLAYER_CORE_VALIDATION.json`: its exact grouped native follow-up.
- `DEGRADATION_*`, `WORKFORCE_*`, `SERVICE_VALIDATION.json`, `GUIDANCE_VALIDATION.json`, `CAPABILITY_DISCOVERY_VALIDATION.json`: read exact hashes/scopes and current parent links. Controlled/synthetic cases do not imply natural all-state coverage.
- `STOCKPILE_BOUNDARY_REVIEW.json` / `STOCKPILE_BOUNDARY.md`: static candidate review; STOCKPILE_READER_VALIDATION.json pins the earlier reader-only JAR. STOCKPILE_BOOKKEEPING_VALIDATION.json checks current global reservation DTO/MCP exposure; per-room arrays remain fixture-only.
- Other `*_VALIDATION.json`, `validation-evidence.json`, `provider-validation.json` and source-review reports may belong to older builds. Preserve them as historical evidence; current equivalents can be nested in PLAYER_CORE. The index distinguishes their roles.
- `REGIONAL_OUTPUT_BOUNDARY_REVIEW.json` / `REGIONAL_OUTPUT_BOUNDARY.md` / `REGIONAL_OUTPUT_READER_VALIDATION.json`: candidate stored regional counters, configured cyclic offsets and excluded mutating helpers; finite native reader/identity evidence, no production MCP counter table.
- `UI_LIFECYCLE_BOUNDARY_REVIEW.json` / `WORLD_FACTION_CONTEXT.md`: finite source/compiler route checks, public faction panel observations and explicit inaccessible/mutating alternatives; WORLD_FACTION_CONTEXT_VALIDATION.json pins eleven copied-game/MCP phases. Not exhaustive API absence proof.
- `CURRENT_COLLECTION_COST_VALIDATION.json`: current published collector in a paused small copied city; COLLECTION_COST_VALIDATION.json preserves the older workforce build. Neither proves large-city/live-capture cost.
- `COLLABORATION_VALIDATION.json`: the original developer-tool/docs checkpoint, separate from the player's test count/JAR; pinned hashes/counts remain historical as current guides evolve.

## Private/local and deferred material

Ignored `.venv/`, `.tools/`, build/, dist/, runtime/, env/auth files and local game installation are not a portable dependency bundle. Contributors supply their own licensed game, Java/JDK, compatible copied save and provider key. Do not commit private patches/logs or use another app's credential files. The public repository has no selected redistribution license.

`examples/providers/`, `claude.mcp.example.json` and `codex.example.toml` are external-client development aids. They are not required for native Pro tests and do not establish every provider's authenticated acceptance. OPENAI_CONNECTION.md, PROVIDERS.md and IN_GAME_CHAT.md retain deferred requirements. No provider/account expansion is implied by collaborating with Claude.

At handoff, update WORK_STATUS and the relevant current feature guides. Keep precise history in reports/Git; do not rewrite old dates/hashes or add another unqualified "current" claim to a historical checkpoint.
