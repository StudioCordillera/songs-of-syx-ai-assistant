# Roadmap

## Current focus

Return to the core mod objectives. Further provider integration, account binding and sign-in work are deferred while the game-data and guidance foundations advance. Existing chat implementations remain available experimentally; they are not evidence that the core mod is complete.

The game-facing boundary remains an in-process SCRIPT mod using explicit public APIs verified against the installed game and shipped source. Distinguish documented script contracts from source-verified public members. Do not use reflection, private fields, process-memory inspection, screenshots, native input or arbitrary method invocation to fill gaps.

## 1. Selective access to game state — first priority

Goal: let an assistant discover available variables and request a complex, bounded selection quickly, without receiving the entire state on each question.

Implemented: 18 partial typed domains; snapshot filters, projections, joins, arithmetic and aggregates; on-demand person/stat reads; retained entity captures for stable paging; finite terrain/floor/room/mineral/path reads. Results identify their observation, session, coverage and scope. The compiler audit currently inventories 306 public production member references. The offline public-member catalog is a discovery backlog, not a count of supported variables.

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

Implemented: installed game-help retrieval and a reviewed starter corpus of eight original external-source summaries with direct URLs, authority and version caveats. This is a small foundation, not comprehensive guide coverage. Nine authored retrieval cases now pass through actual MCP; relevance ranks before version/authority tie-breakers (GUIDANCE_VALIDATION.json).

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
