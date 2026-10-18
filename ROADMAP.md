# Roadmap

Current boundary: an in-process SCRIPT mod, typed public-API observations, bounded snapshot selections and cited reference retrieval. No private reflection or native/OS UI automation. See API_BOUNDARY.md.

1. Expand explicit data mappings with primary-source provenance, meanings, units and per-version coverage. Leave inaccessible data unavailable.
2. Extend the established partial UI context and evidence catalog. Selected subject/view/known-overlay/room-blueprint reads, named individual statistics and bounded exposed popup/section content are implemented. Exact selected room instances, tooltip text, management tabs and panel ordering require appropriate public APIs.
3. Establish a documented unload-to-menu lifecycle hook or keep the freshness limitation explicit; test menus/transitions and large settlements.
4. Extend reviewed official/developer reference coverage and version-aware search.
5. Implement the shared in-game chat client, multiple separate chats, durable game-session/chat logs and provider-independent conversation loop described in IN_GAME_CHAT.md. Every supported subscription/API choice must use this interface. Prioritize a usable first-class DeepSeek API path alongside the shared UI/history; external coding-client profiles are development bridges, not completed product support. Follow PROVIDERS.md for official authentication, entitlements and provider-specific tool-call behavior.

Full game state, all-menu coverage and a fully documented stable mod API are not currently available.

On-demand entity requests are implemented in 0.7.0: fixed public fields and named individual stats, bounded filters/cursors, update-thread evaluation and request/session/tick provenance. The isolated over-1,000-entity fixture passes. Next data-access work is broader typed non-entity schemas, attribute meanings/units and large-city performance. Legacy cursor paging is mutable across responses, and no complete game-state schema is claimed.

0.8.0 checks both editor activations and deployment-to-retreat restoration, and exposes bounded public popup/section content. Remaining UI work requires further typed public mappings and runtime evidence; private panel enumeration, exact room/tab/tooltip readers and lifecycle/result callbacks still need appropriate public APIs. At that release, stable multi-page data selection was separate unfinished work.

0.9.0 exposes scene division status and latest hover-consumption flags, and checks running battles plus controlled victory/defeat restoration through public game UI dispatch. Source/private result content remains unavailable; no action API is shipped. At that release, further work included stable bounded selection across pages, broader typed variable/relationship mappings, unit/mechanics evidence, full world/editor workflows and naturally occurring campaign transitions.

Offline declaration discovery now covers the shipped source archive: 2,052 public types / 17,442 public declared member candidates, with all 246 production reference IDs present. See API_DISCOVERY.md and API_DISCOVERY.json. This creates a systematic mapping backlog, not a count of game variables or an official getter contract; mutation/rendering/utility APIs are deliberately not auto-exposed.

0.10.0 adds four typed person relationships (workplace, profession, stored home coordinates and scene division), with source-backed meanings and copied-game validation of present/absent assignments. At that release, full state coverage, stable multi-page observations and all-menu/lifecycle coverage remained unfinished.

0.11.0 implements stable paging of bounded retained entity observations and public after-update sampling through UI pauses. Broader non-entity selection, worker synchronization, complete variable coverage and lifecycle/menu gaps remain objectives. Provider acceptance gates now explicitly include Claude subscription, Claude API and DeepSeek API; local Claude MCP health passes, while authenticated model/tool round-trips and in-game selection remain pending.

0.12.0 adds bounded spatial selection of public terrain/floor/room/mineral/path data, with structured field meanings and explicit shared-room/component limits. Remaining map work includes broader typed fields, consistent retained spatial batches and performance validation. Full world-map/variable schemas, UI-selection/lifecycle contracts and comprehensive menu/combat coverage remain objectives.

The shared in-game client/session-history requirement was made explicit on 2026-10-17 after the user reported that DeepSeek API access lacked a usable client. It is a required feature for every provider, not an optional post-integration enhancement. No chat UI, transcript persistence or authenticated in-game provider flow is implemented yet.

### 2026-10-17 chat implementation checkpoint

Shared SQLite history, bounded read-only MCP conversation loop, native DeepSeek streaming/tool transport, file coordinator and opt-in public-widget panel are implemented experimentally. See [implementation and open gates](CHAT_BACKEND.md). Subscription adapters, authenticated end-to-end replies, in-game connection setup and broad menu/focus/lifecycle validation remain required.
