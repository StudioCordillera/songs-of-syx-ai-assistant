# Repository map

Start with [README](README.md), [shared agent instructions](AGENTS.md), [contributor workflow](CONTRIBUTING.md), [handoff](WORK_STATUS.md) and [roadmap](ROADMAP.md). [DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md) lists every tracked Markdown guide and root JSON artifact, with current/historical scope. Counts and exact tested hashes come from the reports, not this map.

## Runtime data flow

Game process public after-update callback → detached Java DTOs → local snapshot/fixed request mailboxes → Python stdio MCP → selected observations/reference passages → local chat coordinator → DeepSeek Pro → mod-owned transcript. SQLite holds private session/chat history. The I/O worker and MCP never traverse live game objects. The model gets read-only tools, not a game-control, shell or screenshot interface. See [architecture](ARCHITECTURE.md).

## Game bridge: mod/src/main/java/syx/assistant/

| File | Responsibility / edit boundary |
| --- | --- |
| AssistantScript.java | SCRIPT lifecycle, after-update registration, game-thread/worker handoff, snapshot/mailbox/chat IPC and supported-version guard. |
| StateCollector.java | Eighteen partial domains, installed help, typed field definitions and bounded room/resource/region relationships. New fields require provenance, bounds and getter/MCP validation. |
| UiContextCollector.java | Scene/view/overlay/subject/room-blueprint, world-list membership and bounded world-faction-panel context through mapped public getters. No private selected-room fallback. |
| UiContentCollector.java | Bounded exposed popup/section labels/controls, ancestry and opaque/error/truncation markers. |
| WeatherObservation.java | Fixed city weather factors/flags, strict numeric/scope refusal and detached field meanings; no weather mutation/target/forecast. |
| StockpileReadRequest.java | Fixed per-warehouse/resource live pages, strict framing, typed stored counters/predicates/identity and bounded update-thread matrix scan. |
| RegionalReadRequest.java | Fixed live/complete-capture active-region/resource matrix protocols, bounded range/faction predicates and projections on the update thread; independent of cached row prefix. |
| EntityReadRequest.java | Strict live/capture protocol parsing, finite predicates/projections, public entity/stat/workplace reads on the update thread. |
| TileReadRequest.java | Strict rectangle/filter/projection protocol and bounded terrain/floor/room/mineral/path reads. |
| ChatPanel.java | Our own simple/advanced public GUI widgets, text/focus, chat list/transcript/composer; no gameplay-control dispatch. |
| JsonWriter.java | Detached DTO encoding; no game traversal. |

Only these production classes are packaged. `mod/tests/` contains non-shipped bootstrap and public-API fixtures; some deliberately mutate only copied in-process game state. `LiveSmoke.java` / PathCheck enforce copied save and isolated user.home before engine start. `DegradationPositiveScenario` is a test-only public maintenance action, never an MCP action.

The historical pre-production per-warehouse request draft lives under `dev/candidates/stockpiles/`; [candidate scope and next gates](STOCKPILE_LIVE_CANDIDATE.md) distinguish it from the eleven packaged classes. `dev/verify_stockpile_candidate.py` compiles it and checks detached parsing plus paired public room-lookup bodies without starting the game. `dev/run_stockpile_candidate.py` separately executes bounded direct-getter/page/filter/refusal checks in the isolated copied city through an explicit test-only scenario override; it does not dispatch candidate requests through the player or MCP. The new production path is documented in STOCKPILE_LIVE_READS.md and tested with `dev/run_read_fixture.py --case stockpile-live`. Reproducing an older candidate requires its original source/payload checkout.

The unchanged housing candidate also has a separate real-chamber/bounds runner: `dev/run_housing_chamber.py` and `dev/candidates/housing-chamber/StockpileScenario.java`. [HOUSING_CHAMBER_VALIDATION.json](HOUSING_CHAMBER_VALIDATION.json) records one created empty chamber, one controlled occupied assignment using a new test-only promoted noble, restored null home/removal, and actual scan/row limits. Its public mutations belong only in the disposable fixture; there is no production action or new MCP field.

## Python runtime modules

| Module | Responsibility |
| --- | --- |
| syx_mcp.py | Snapshot/domain models, freshness/cache, Advisor and nineteen tool registrations; stdio entry point. |
| syx_query.py | Fixed snapshot selection language, joins/arithmetic/grouping/sort, shared work/row/source budgets and collection diagnostics. |
| syx_live.py | Strict entity selections, live/capture wire transport and agent-facing schema/help. |
| syx_capture.py | Immutable encoded retained entity/tile/regional observations in separate bounded pools, server-local tokens, shared paging/freshness guards and original provenance. |
| syx_stockpiles.py | Strict warehouse/resource schema, wire encoding and response identity/projection/predicate/cursor/error/size validation; shared guarded live transport. |
| syx_regions.py | Strict regional live/capture selections/wire, shared guarded transport and response matrix/projection/identity/completeness/cap checks. |
| syx_tiles.py | Strict live/capture tile selection schemas, fixed mailbox and same-response context checks; captures must fit one callback. |
| syx_knowledge.py | Reviewed SEEDS, non-destructive corpus merge and knowledge CLI. Search/ranking lives in Advisor in syx_mcp.py. |
| syx_api_support.py | Curated capability routing, source/evidence/limit descriptions and explicit gaps; not arbitrary invocation. |
| syx_api_manifest.py | Generated compiler audit metadata. Regenerate with audit_api.py; never hand-merge it. |
| syx_chat_service.py | Local IPC coordinator, fresh MCP automatic player attachment / explicit advanced attachment, simple/advanced routes, key boundaries and lifecycle. |
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
| dev/verify_*_contract.py, verify_bytecode.py, review_production_modifier_boundary.py, review_stockpile_boundary.py, review_ui_lifecycle_boundary.py, review_world_list_boundary.py, review_regional_output_boundary.py, verify_production_periods.py | Static licensed source/binary review without initializing game classes; publish metadata/hashes/conclusions only. |
| test_*.py | Offline regression tests with mock providers/synthetic observations/local Git repos. No key or paid inference needed. |
| mod/tests/ + dev/verify_*.py | Explicit licensed-game getter/MCP/context/cap/lifecycle fixtures and metadata-only reports. Read each verifier's scope. |
| dev/run_read_fixture.py | Fixed tile/entity/world-faction-context/regional regressions and regional collector/MCP timing samples against published/candidate player; locks/restores copied mod and checks copied-save integrity. |
| dev/run_stockpile_probe.py | Published/candidate JAR copied-city stockpile readers, overload/sum/lifecycle checks and global reservation DTO/MCP parity; locks/restores copied mod, no provider calls. |
| dev/run_player_chat_check.py | Explicit paid two-turn Pro test using a manually supplied key; builds/audits current source, isolates game/MCP credentials and restores copied-profile mod. |
| dev/verify_user_test_chat.py | Verify an already executed native Pro chat/history; does not itself launch the game or provider. |
| dev/verify_current_player_core.py | Exact published/candidate JAR through seven copied-save groups, no inference. |
| dev/profile_collection_cost.py / benchmark_selective_queries.py | Descriptive collection/selection timings for exact published payload; audited game/source pair, copied mod restore/save integrity and shared lock. Current small-city evidence is separate from historical timings and larger-city acceptance. |
| make_user_test.py | Package only our Java/Python/player assets from matching provider/source evidence; retain prior tested ZIP. |
| dev/check_user_test_release.py | Standard-library freshness/hash checker for current production payload; CI/pre-push gate, not a game playtest. |
| dev/native_game_completion.py | Finite engine-crash/fixture-failure log guard for read/core/cost runners; normal captured stderr alone is not a failure. Explicit feature completion markers supplement process exit codes. |
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
- `REGIONAL_OUTPUT_BOUNDARY_REVIEW.json` / `REGIONAL_OUTPUT_BOUNDARY.md` / `REGIONAL_OUTPUT_READER_VALIDATION.json`: original candidate stored-reader/offset evidence and excluded mutating helpers; its earlier JAR/hashes remain historical. REGIONAL_OUTPUTS.md / REGIONAL_OUTPUT_VALIDATION.json describe the subsequent bounded DTO/MCP mapping.
- `WORLD_LIST_BOUNDARY_REVIEW.json` / `WORLD_LIST_CONTEXT_VALIDATION.json` / `WORLD_LIST_CONTEXT.md`: source/compiler membership review and finite native availability/modal/hidden/editor/MCP checks; no selected-object or list-content claim.
- `UI_LIFECYCLE_BOUNDARY_REVIEW.json` / `WORLD_FACTION_CONTEXT.md`: finite source/compiler route checks, public faction panel observations and explicit inaccessible/mutating alternatives; WORLD_FACTION_CONTEXT_VALIDATION.json pins eleven copied-game/MCP phases. Not exhaustive API absence proof.
- `REGIONAL_CAPTURE_VALIDATION.json`: complete single-callback regional selections, retained pages after counter/context changes, real reload invalidation and finite capture timings; REGIONAL_CAPTURES.md describes protocol and limits.
- `REGIONAL_REQUEST_COST_VALIDATION.json`: earlier live-page JAR regional collector/encoding samples plus sequential actual MCP latency; finite paused campaign, separate from regular collector cost. Reproduce with the `regional-cost` read-fixture case.
- `CURRENT_COLLECTION_COST_VALIDATION.json`: current published collector in a paused small copied city; COLLECTION_COST_VALIDATION.json preserves the older workforce build. Neither proves large-city/live-capture cost.
- `COLLABORATION_VALIDATION.json`: the original developer-tool/docs checkpoint, separate from the player's test count/JAR; pinned hashes/counts remain historical as current guides evolve.

## Player-experience revision and background regression

[PLAYER_EXPERIENCE_PLAN.md](PLAYER_EXPERIENCE_PLAN.md) maps the latest user requests, current gaps and acceptance order. `mod/tests/ChatBackgroundScenario.java`, `dev/verify_chat_background.py` and `dev/run_read_fixture.py --case chat-background` exercise current published own-panel widgets at speed 1 with simulated delayed inference through the real coordinator/MCP/history. [CHAT_BACKGROUND_VALIDATION.json](CHAT_BACKGROUND_VALIDATION.json) records finite open/closed time progression and closed completion/reopen. CLAUDE_UX_COLLABORATION.json records four completed local Opus/max peer reviews and the parent session-limit failure; [CLAUDE_UX_REVIEW.md](CLAUDE_UX_REVIEW.md) preserves their edited findings. That historical invocation produced no final design. The later independent prototype and completed peer critique are mapped below. This fixture evidence does not establish native redesign; production automatic attachment has its own later exact-source reports. [Blueprint candidate discovery](BLUEPRINT_REFERENCE_CANDIDATES.md) records page-text/metadata leads only; geometry, rights and current-game compatibility still need review.

## Developer unread/history candidate

[CHAT_HISTORY_CANDIDATE.md](CHAT_HISTORY_CANDIDATE.md) documents `dev/chat_history_candidate.py`, isolated SQLite receipt/migration/runtime-filter code not imported or packaged by the player. `test_chat_history_candidate.py` supplies twelve authored cases, including actual latest/previous bundled-store compatibility. [Candidate evidence](CHAT_HISTORY_CANDIDATE_VALIDATION.json) pins source/bundle hashes and explicit budgets; no badge, automatic routing, stable world identity or real display acknowledgement is claimed.

## Private/local and deferred material

Ignored `.venv/`, `.tools/`, build/, dist/, runtime/, env/auth files and local game installation are not a portable dependency bundle. Contributors supply their own licensed game, Java/JDK, compatible copied save and provider key. Do not commit private patches/logs or use another app's credential files. The public repository has no selected redistribution license.

`examples/providers/`, `claude.mcp.example.json` and `codex.example.toml` are external-client development aids. They are not required for native Pro tests and do not establish every provider's authenticated acceptance. OPENAI_CONNECTION.md, PROVIDERS.md and IN_GAME_CHAT.md retain deferred requirements. No provider/account expansion is implied by collaborating with Claude.

At handoff, update WORK_STATUS and the relevant current feature guides. Keep precise history in reports/Git; do not rewrite old dates/hashes or add another unqualified "current" claim to a historical checkpoint.

## Earlier reviewed ground-moisture candidate

[GROUND_MOISTURE_BOUNDARY.md](GROUND_MOISTURE_BOUNDARY.md) explains two stored tile readers and the outstanding production acceptance. `dev/review_ground_moisture.py` pins source/binary/compiler semantics; `mod/tests/GroundMoistureScenario.java`, `dev/verify_ground_moisture.py` and `dev/run_read_fixture.py --case ground-moisture` validate the finite copied-city candidate. [Static review](GROUND_MOISTURE_BOUNDARY_REVIEW.json) and [reader report](GROUND_MOISTURE_READER_VALIDATION.json) are candidate evidence, not new MCP support or all-scene acceptance. Latest player payload is unchanged.

[Stored tile moisture](GROUND_MOISTURE.md) is the optional production base/current projection through the existing live/retained tile path. `TileReadRequest.java`, `syx_tiles.py`, `TileScenario.java`, `dev/verify_tiles.py` and `dev/verify_scenes.py` carry mapping, definitions and native/MCP follow-up. The earlier candidate report remains separately scoped.

`test_syx_tiles.py` includes a cheap cross-layer projection-discovery preflight; the licensed-game tile fixture independently checks the snapshot field list against MCP query help and actual field values. This guards metadata drift without treating source-text agreement as runtime proof.

## Cached viewport candidate

[VIEWPORT_BOUNDARY.md](VIEWPORT_BOUNDARY.md) distinguishes stored window geometry from selection/hover/rendered visibility. `dev/review_viewport_boundary.py` pins compiler/source/selected-bytecode checks; `mod/tests/ViewportScenario.java`, `dev/verify_viewport.py` and `dev/run_read_fixture.py --case viewport` reproduce eleven public-action copied-game phases. [Static review](VIEWPORT_BOUNDARY_REVIEW.json) and [candidate report](VIEWPORT_CANDIDATE_VALIDATION.json) do not add a production DTO/MCP field.

## Automatic player connection checkpoint

[AUTO_CONNECTION.md](AUTO_CONNECTION.md) maps paired IPC 2, automatic opening/reconnect-on-send, bounded runtime filters and per-chat draft preservation. `test_auto_connection.py` supplies offline admission/filter/race cases. `dev/run_chat_connection_check.py` / `dev/verify_auto_connection.py`, `ChatAutoConnectScenario.java` and `ChatUiScenario.java` provide copied-save feature/focus checks with fake providers or no key, separate from actual Pro acceptance. `dev/verify_player_distribution.py` checks fresh extracted dependencies/startup/isolated installation and optional provided-key exclusion without inference. Feature reports pin current source and JAR. Durable world identity, unread badges and native redesign remain open.

[CHAT_INPUT_BOUNDARY.md](CHAT_INPUT_BOUNDARY.md) and `dev/review_chat_input_boundary.py` map future public own-widget gesture inputs, cached-pointer/mutable-handle limits, rejected private focus access and layered-render visibility limits. CHAT_INPUT_BOUNDARY_REVIEW.json is static candidate evidence with zero game initializations, not native drag/badge acceptance.

[CHAT_GESTURE_CANDIDATE.md](CHAT_GESTURE_CANDIDATE.md) maps the unshipped game-independent `dev/chat_gesture_candidate.py` model and 25 offline cases in `test_chat_gesture_candidate.py`. It supplies no native polling/hit-testing/focus or actual player movement.

## Detached unread/display development

[CHAT_DISPLAY_CANDIDATE.md](CHAT_DISPLAY_CANDIDATE.md) maps `dev/chat_display_candidate.py`, the unshipped Java protocol/coverage models under `dev/java/syx/assistant/candidate/`, and `test_chat_display_candidate.py` / `test_chat_display_java.py`. [Offline evidence](CHAT_DISPLAY_CANDIDATE_VALIDATION.json) is separate from player acceptance. [CHAT_VISIBILITY_BOUNDARY.md](CHAT_VISIBILITY_BOUNDARY.md), [static review](CHAT_VISIBILITY_BOUNDARY_REVIEW.json) and [native probe](CHAT_VISIBILITY_VALIDATION.json) map `dev/review_chat_visibility_boundary.py`, `dev/verify_chat_visibility.py`, `mod/tests/ChatVisibilityScenario.java` and the `chat-visibility` read-fixture case. They establish finite callback/tooltip/activation limitations, not an automatic read gate.

`dev/measure_chat_display_candidate.py` measures disposable synthetic short-history/at-row-cap detached broker scans and unchanged refreshes; [CHAT_DISPLAY_COST_VALIDATION.json](CHAT_DISPLAY_COST_VALIDATION.json) keeps the exact source and workload limits. No production latency or native repaint acceptance is implied.

[REFERENCE_FEED_RECHECK.json](REFERENCE_FEED_RECHECK.json) records the independent official Steam API recheck of existing service guidance, including author/date/body-hash provenance and cached-archive/canonical-mapping limits. It does not add or refresh production summaries automatically.

[BLUEPRINT_PLANNER_REVIEW.json](BLUEPRINT_PLANNER_REVIEW.json) pins selected upstream author software/license/version and lossy-conversion caveats. It extends [blueprint discovery](BLUEPRINT_REFERENCE_CANDIDATES.md) without importing code/assets or claiming a verified current-game schematic.

[CHAT_DISPLAY_REFRESH_VALIDATION.json](CHAT_DISPLAY_REFRESH_VALIDATION.json) preserves synthetic before/after encoded-row cache timings and the subsequent 394-test exact-source recheck; original row-cost reports retain their prior source hashes.

[PLAYER_CHAT_PROTOTYPE.md](PLAYER_CHAT_PROTOTYPE.md) maps the Codex-authored standalone `design/player-chat-prototype.html` and [finite browser review](PLAYER_CHAT_PROTOTYPE_VALIDATION.json). It uses recovered Claude findings but is not attributed to a completed new Claude response or native mod acceptance.

[CLAUDE_PROTOTYPE_REVIEW.md](CLAUDE_PROTOTYPE_REVIEW.md) records the completed local Opus 5.5 source critique, accepted browser fixes, rejected identity/read-policy alternatives and finite post-review checks; [invocation evidence](CLAUDE_UX_COLLABORATION.json) keeps earlier generation timeouts separate.

## Next-message target evidence candidate

[CHAT_TARGET_CANDIDATE.md](CHAT_TARGET_CANDIDATE.md) maps `dev/chat_target_candidate.py` and `test_chat_target_candidate.py`: explicit per-chat entity/tile/regional capture pages, immutable original provenance, lifecycle/hash revalidation and bounded all-or-nothing evidence preparation. [Offline evidence](CHAT_TARGET_CANDIDATE_VALIDATION.json) uses real encoded capture pools with synthetic game reads. No native chips/picker, interprocess transport, durable enqueue, provider or gameplay actions are shipped.

[CHAT_TARGET_TRANSPORT.md](CHAT_TARGET_TRANSPORT.md) maps `dev/chat_target_transport.py`, the shared `DraftEvidence` normalization in `dev/chat_target_candidate.py`, `dev/target_transport_fixture.py` and `test_chat_target_transport.py`. The async candidate uses four fixed existing MCP readers, whole-operation deadlines and owned-session semantics. Actual production MCP stdio tests use synthetic capture rows; no native/coordinator/send integration or new player tools are implied. [Transport evidence](CHAT_TARGET_TRANSPORT_VALIDATION.json) keeps this distinct from the earlier same-process report.

## Durable target-backed acceptance candidate

[CHAT_TARGET_QUEUE.md](CHAT_TARGET_QUEUE.md) maps `dev/chat_target_queue.py`, strict send-intent preparation/exact accepted-ID clearing in the target adapters, the shared receipt registry coexistence correction and `test_chat_target_queue.py`. It atomically records an undispatched question and original evidence, recovers exact acknowledgements and preserves newer chips. The copied-city tile verifier adds getter-backed acceptance/store-restart/ack checks. [Evidence](CHAT_TARGET_QUEUE_VALIDATION.json) is separate from native client/provider integration; no production source or game command changes are implied.

[CHAT_TARGET_DISPATCH.md](CHAT_TARGET_DISPATCH.md) maps `dev/chat_target_dispatch.py` and `test_chat_target_dispatch.py`: an explicit developer-only accepted-turn claim/store seam into the unchanged Conversation loop, no automatic replay after uncertain delivery. Copied-city tile evidence uses a fake provider after original token eviction. [Validation](CHAT_TARGET_DISPATCH_VALIDATION.json) is not player/native controls or real Pro acceptance.

`dev/verify_target_dispatch_pro.py` is an explicit paid follow-up invoked only by the tiles runner with `--env-file`; `test_target_dispatch_pro_check.py` replaces inference with a fake. [Pro handoff evidence](CHAT_TARGET_DISPATCH_PRO_VALIDATION.json) distinguishes workflow/round attempts, exact outgoing evidence, copied-game restoration and remaining native/client/semantic gates. The default runner remains zero-inference.

[CHAT_TARGET_TASKS.md](CHAT_TARGET_TASKS.md) maps `dev/chat_target_tasks.py` and `test_chat_target_tasks.py`: explicit accepted-task ownership, exact Stop, no-replay status, bounded concurrency/recent summaries and pending-cleanup-aware teardown. Copied-city fake-provider task completion/Stop and [evidence](CHAT_TARGET_TASKS_VALIDATION.json) remain separate from native request/button integration.

[CACHED_VIEWPORT.md](CACHED_VIEWPORT.md) maps the production `UiContextCollector.cachedViewport` primitive DTO, same-tick public-getter fixture, actual MCP context/selection verifier, scene invariant helper and query example. [Viewport evidence](VIEWPORT_VALIDATION.json) separates supported cache observations from unavailable management/setup/editor states and unknown rendered visibility/cache age.


## Warehouse removal and ID reuse regression

`mod/tests/StockpileLifecycleScenario.java`, `dev/verify_stockpile_lifecycle.py` and `dev/run_read_fixture.py --case stockpile-lifecycle` validate three public-action copied-city phases through the actual production MCP: baseline, a distinct same-ID instance and complete removal. [Evidence](STOCKPILE_LIFECYCLE_VALIDATION.json) pins nine successful pages, expected explicit-ID/cursor refusals and clean restoration. [Manual source review](STOCKPILE_LIFECYCLE_SOURCE_REVIEW.json) separates public fixture routes from static internal implementation inspection. No production code, provider call or player ZIP changes; multi-room/cap/fault coverage remains open.


## Real multi-warehouse matrix regression

`mod/tests/StockpileMatrixScenario.java`, `dev/verify_stockpile_matrix.py` and `dev/run_read_fixture.py --case stockpile-matrix` create fixed small real test rooms in the copied city and compare 101/100-room matrices before/after middle removal. [Pinned evidence and selected source review](STOCKPILE_MATRIX_VALIDATION.json) cover 8,442 getter cells, 129 successful MCP pages, ordered slot shifts, explicit-order queries, actual 4,096-cell empty scans and 100-row projected pages. Developer-only setup is not a normal build/material or larger-city performance fixture. No player source/ZIP changes, provider calls or production game actions.


## Stored weather reader candidate

[Weather candidate scope](WEATHER_CANDIDATE.md) maps `dev/candidates/weather/syx/assistant/candidate/WeatherObservation.java`, detached `WeatherPureCheck.java`, the explicit host `StockpileScenario.java` override, `dev/review_weather_candidate.py` and `dev/run_weather_candidate.py`. [Source/codec review](WEATHER_CANDIDATE_REVIEW.json) is separate from [48 native samples/672 getter comparisons](WEATHER_CANDIDATE_NATIVE_VALIDATION.json). That developer package remains unregistered; the separate production implementation and current MCP evidence are mapped below. The shared disposable host supports optional review/completion hooks; its stockpile defaults remain unchanged. Latest/previous tested payloads are preserved.


[Weather scene follow-up](WEATHER_SCENE_VALIDATION.json) maps `dev/run_weather_scenes.py`, `dev/candidates/weather/scenes/StockpileScenario.java`, the optional own-fixture observer in `mod/tests/SceneScenario.java` and the validated copied-save property in the shared native host. Eight real scene phases and seven restored public-setter normalization cases are separate from earlier 48-sample weather evidence. Public normalization blocks this attempted native NaN injection route; no native malformed stored weather or new MCP/player field is claimed.


## Production stored weather

[Weather fields and scopes](WEATHER.md), `WeatherObservation.java`, the map-domain wrapper, `WeatherScenario.java` and `dev/verify_weather.py` supply same-callback full-observation getter/DTO checks and actual retained-original MCP projections, followed by eight actual live weather scene queries. `dev/review_weather_production.py` / [contract review](WEATHER_CONTRACT_REVIEW.json) and [runtime evidence](WEATHER_VALIDATION.json) separate public source/bytecode/codec findings from actual behavior. `test_weather.py`, `weather-query-example.json` and the capability-discovery verifier cover zero/unavailable/stale snapshot and discoverable source meanings. Earlier candidate reports retain their source/JAR dates.


## Housing record/ledger candidate

[Housing candidate scope](HOUSING_CANDIDATE.md) maps `dev/candidates/housing/syx/assistant/candidate/HousingObservation.java`, the explicit `StockpileScenario.java` host override, `dev/review_housing_boundary.py` and `dev/run_housing_candidate.py`. [Selected source/public-reader review](HOUSING_BOUNDARY_REVIEW.json) is separate from [32 native samples](HOUSING_CANDIDATE_VALIDATION.json): 36 ordinary homes, 204 assignment links and 16 eligibility-weighted cohort rows. Noble branch, actual budgets/faults and broader lifecycle remain unvalidated. No production/MCP housing field or player ZIP change yet.
