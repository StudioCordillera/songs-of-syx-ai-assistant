# Roadmap

## Current focus

Return to the core mod objectives. Further provider integration, account binding and sign-in work are deferred while the game-data and guidance foundations advance. Existing chat implementations remain available experimentally; they are not evidence that the core mod is complete.

The game-facing boundary remains an in-process SCRIPT mod using explicit public APIs verified against the installed game and shipped source. Distinguish documented script contracts from source-verified public members. Do not use reflection, private fields, process-memory inspection, screenshots, native input or arbitrary method invocation to fill gaps.

The runnable player checkpoint now requires a source-matching `releases/latest-user-test.zip` with simplified DeepSeek Pro chat. Rebuild and validate the player bundle after production changes; `dev/check_user_test_release.py`, the repository pre-push hook and CI detect stale bundled code. Keep the last tested download while preparing a candidate. See USER_TEST_VALIDATION.json and releases/README.md. This delivery requirement does not replace the core objectives below.

## 1. Selective access to game state — first priority

Goal: let an assistant discover available variables and request a complex, bounded selection quickly, without receiving the entire state on each question.

Implemented: 18 partial typed domains; snapshot filters, projections, joins, arithmetic and aggregates; on-demand person/stat reads; retained entity captures for stable paging; finite terrain/floor/room/mineral/path reads. Results identify their observation, session, coverage and scope. The compiler audit currently inventories 353 public production member references. The offline public-member catalog is a discovery backlog, not a count of supported variables.

Next work:

- Inventory the fields already exported against the public-member catalog. Prioritize missing settlement resource flows, workforce/production relationships, research and world-region data that help answer concrete player questions.
- Extend explicit typed mappings with source anchors, meanings, units, null/unavailable behavior, relationships and scene applicability. Unknown units and mechanics must remain explicit.
- Keep reads bounded and on the game thread. Establish consistent retained spatial selections where cross-page consistency is needed; validate costs in a large settlement.
- For each added mapping, check direct getter agreement in an isolated copied game, update the compiler/source audit and add an agent-facing query example.

Acceptance: the assistant can discover each supported field and retrieve only the requested rows/attributes, with truthful truncation, consistency and provenance. Unsupported fields remain discoverable as coverage gaps rather than invented values. Full game-state coverage is not yet established.

## 2. UI context and lifecycle accuracy

Goal: answer questions about the current view and selection, and remain truthful through pauses, menus, reloads and scene changes.

Implemented: active views, known overlay flags, selected person and individual stats, open room blueprints, bounded public popup/section content and save-session rotation. Public after-update sampling continues through UI pauses. Historical observation builds have isolated city/world/editor/battle and transition evidence; see the exact build scopes in VALIDATION.md and validation-evidence.json.

Next work:

- Establish appropriate public getters for additional selected objects and management context before exposing them.
- Investigate a documented unload-to-menu lifecycle hook. Until one is established, preserve the explicit freshness limitation: return-to-menu may leave the previous observation apparently current for up to 30 seconds, then current state becomes unknown.
- Revalidate supported scenes and transitions whenever relevant collectors change. Test unsupported or ambiguous contexts as unavailable; do not infer a topmost panel from unordered overlay flags.

Acceptance: a context-dependent answer uses the same observation as its data query, identifies ambiguity and refuses unavailable/stale context. Exact selected room instances, complete tooltip/tab/panel hierarchy, standalone main-menu identity and exhaustive all-menu coverage remain unestablished.

## 3. Trustworthy, cited reference access

Goal: give the assistant easy access to official, developer and high-quality community material relevant to the user's question and game version.

Implemented: installed game-help retrieval now includes 111 room and three research-currency descriptions in the copied-game check (834 total references), with links from room UI context, employment, production and currency data. See INSTALLED_HELP_VALIDATION.json. A reviewed starter corpus contains eleven original external-source summaries with direct URLs, authority and version caveats. This is a small foundation, not comprehensive guide coverage. Twenty-nine authored cases now pass through actual MCP, including supporting-passage/caveat checks, explicit version mismatches and authority filters; relevance ranks before version/authority tie-breakers (GUIDANCE_VALIDATION.json and GUIDANCE_EVALUATION.md).

Next work:

- Expand reviewed coverage around food/service problems, production/workforce, storage/logistics, research, trade and population needs.
- Verify primary sources and retain author, URL, retrieval date, applicable versions and explicit uncertainty. Distinguish official/developer statements from community recommendations.
- Evaluate retrieval using representative player questions and verify that returned passages actually support the proposed advice. Keep external guidance separate from live-state evidence.

Acceptance: advice cites retrieved supporting material, explains version mismatches and separates observed facts from recommendations. No fabricated citations or unsupported mechanics claims.

## 4. Shared in-game chat — retained requirement

The user must have an in-game chat client with separate chats and durable session/chat logs, regardless of the eventual supported provider. DeepSeek API and Claude subscription have passed bounded two-turn in-game flows with selective reads and guide citations. Local rename/evidence/export/delete and reload attachment also have isolated evidence. See CHAT_BACKEND.md and CHAT_VALIDATION.json for build-specific limits.

Remaining client work includes broader menu/focus/lifecycle checks, physical keyboard and multiline usability, model selection and connection setup. Further provider/account expansion is deferred by the current focus; OpenAI access and Claude API inference are not claimed complete.

## Evidence and completion

API_BOUNDARY.md and API_ESTABLISHMENT.md explain the API boundary and observation baseline. API_DISCOVERY.md/JSON describe public declaration discovery. QUERY_GUIDE.md describes selection and consistency limits. VALIDATION.md and validation-evidence.json retain historical observation evidence; CHAT_VALIDATION.json records the experimental shared-chat evidence. Passing an older build's fixture does not validate a newly changed build.

The first core checkpoint adds the [data-coverage inventory](DATA_COVERAGE.md) and expanded research prerequisites/currencies/costs with copied-game getter agreement and an MCP relational query (CORE_VALIDATION.json). The same checkpoint establishes the shared observed room-instance key across employment and individual workplace records, including a selected-worker MCP join. The following checkpoint maps bounded current producer-room inputs/outputs and recorded quantities, with a room/employment/resource MCP join (PRODUCTION_VALIDATION.json). Next work includes production modifiers, explicit bucket-age evidence and large-city performance/cap validation. The mod is not finished: complete variables, complete menus and comprehensive reference coverage remain open objectives.

The subsequent production-period review (PRODUCTION_PERIOD_REVIEW.json / PRODUCTION_PERIODS.md) checks integer rollover, fractional carry and protected age-marker visibility against source and bytecode without executing game classes. Exact bucket age remains unknown through the inspected APIs. The exact current player JAR now passes the reproducible copied-save core suite in PLAYER_CORE_VALIDATION.json: production getter/MCP parity, eight scene phases, eleven UI/lifecycle phases with 834 installed references, and additional popup/content/editor/retreat checks. dev/verify_current_player_core.py reproduces these groups without provider requests. These remain finite sampled checks, not exhaustive menu acceptance.

Selective-query-examples.json and SELECTIVE_QUERY_VALIDATION.json add independently checked filter/join/group examples and local offline engine timings. They preserve the original observation timestamp, do not make a stale snapshot live and do not establish large-city collection cost. Remaining work includes that larger-city validation, additional typed world/trade/service fields and broader reviewed reference coverage.

The regional population checkpoint adds capped campaign-region total and playable-race counters, capital/area and player ownership, with same-observation region joins. WORLD_VALIDATION.json records 203 regions and 1,218 race-count rows checked through public getters and actual MCP. No regional growth forecast, non-playable census or huge-world/cap-failure runtime coverage is claimed. Exact regional timestamps remain unexposed. Next data priorities are source-established world economy/trade relationships and their units, plus large-city collector cost; keep reference expansion and remaining UI lifecycle gaps on the roadmap.

The city-trade checkpoint adds capped resource stages by trade reason and configured buyer/seller limits, separate from the campaign daily ledger. TRADE_VALIDATION.json checks 42 resource policies and 168 stage records, including deliberately nonzero public-bookkeeping/policy cases in an isolated copied city. A source-backed stage-sum check and actual MCP stock/policy join pass. Production makes no reservation, delivery, extraction or policy write. Full order records, executable quotes/tariffs, non-resource tradables, routes/ETAs and nonzero caravan travel remain unestablished; city trade is unavailable on battlefields. See TRADE_PIPELINE.md.

The query layer now retains explicit nested observation coverage: unavailable table sources/joins are refused, container projections/pages are null rather than empty successes, and subtree coverage/scope/reason is retained. Tests and actual battlefield MCP count/page checks distinguish this from a genuinely available empty source. The current trade checkpoint passes 148 tests, two Pro turns and the full six-group copied-save suite. Next work should balance further source-backed logistics/economy mappings with current-version guidance coverage and collector cost validation; unresolved exact menu/selection and public-API gaps remain explicit.

The reference-evaluation checkpoint strengthens the unchanged nine-source corpus: 20 actual MCP cases check 31 supporting passages and 18 caveats, direct citation/speaker metadata, four version inputs and authority-filter refusal cases. Negative tests reject missing support, stripped caveats and misleading attribution/compatibility. This validates local evidence retrieval, not generated-answer correctness or newly refreshed sources. The runtime/player ZIP remains unchanged and source-matching; next reference work remains reviewed coverage expansion and current-version source verification.

The service-counter checkpoint adds bounded per-room total/available/reserved service points through public ROOM_SERVICER readers, with same-observation staffing joins and installed help links. Static source/binary review establishes direct stored reads, without service reporting/refresh/reservation writes. These remain raw room-specific points, not daily people capacity or individual access. The copied-city check compares eight service rooms, including naturally nonzero available/reserved cases; remaining priorities include service demand/access relationships, large-city costs/caps, reference expansion and unresolved UI lifecycle gaps.

The exact service-counter player bundle passes 155 Python tests, two real Pro turns, all seven copied-save core groups and fresh extracted-client startup/install checks. The prior tested ZIP is retained. Source/bytecode review and current scene/UI evidence are pinned in SERVICE_VALIDATION.json and PLAYER_CORE_VALIDATION.json; full state/menu coverage, individual service permissions/demand and large-city/cap validation remain open.

The reference/discovery expansion adds two reviewed official V71 topic summaries with canonical citations, rendering provenance and explicit exact-patch uncertainty. The corpus now has eleven records; 29 actual MCP cases check 42 supporting fragments and 30 caveats. Offline capability discovery now routes service counters, city trade stages and regional population to existing mappings/evidence, while all-variable/all-menu gaps stay unavailable. The Java JAR is unchanged; earlier core/scene reports retain their prior Python hashes rather than being relabeled as a new full-suite run. See REFERENCE_EXPANSION.md. Further reviewed sources, demand/permission mappings, large-city/cap validation and unresolved UI accessors remain priorities.

The configured-service-policy checkpoint adds registered service types and bounded race/class flags through public permission interfaces, separate from actual individual access. The copied-city fixture checks 544 rules across 17 types, including test-only controlled true/false settings, population joins and installed help. Child/parent and noble/tourist exceptions remain explicit; battlefield/setup city policy is unavailable. Atomic cohort batches, caps and failure diagnostics are documented in SERVICE_PERMISSIONS.md. Full individual eligibility, demand/reachability, large-city/cap behavior, broader references and missing UI accessors remain open.

The exact policy build passes 160 Python tests, two Pro turns, all seven copied-save core groups, 29 guidance cases, offline capability discovery and fresh extracted-client checks. Current scene tests refuse unavailable battlefield city-policy pages/counts rather than fabricating empty denial settings. The tested ZIP and installed mod match the current source, with the previous ZIP retained. These remain finite cases, not complete individual eligibility or all-state/menu coverage.
