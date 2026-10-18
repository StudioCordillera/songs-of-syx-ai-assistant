# Architecture — 0.12.0

The Java mod implements the shipped SCRIPT interface. Typed collectors read public game APIs on the game update thread through public `GAME.addAfterUpdate` and build detached DTOs. A daemon serializes them to an atomic local JSON snapshot approximately every two wall-clock seconds while the update hook runs. MCP validates/caches that snapshot and executes bounded selections locally. Neither the daemon nor MCP traverses game objects. On-demand entity requests are parsed on the file daemon, handed to the update thread, evaluated using fixed public getters, and returned as detached DTOs.

The snapshot includes version, mods, session, tick, time and 18 partial domains, plus the installed-help catalog. Query batches share one cached snapshot; optional snapshot pins reject changes. See QUERY_GUIDE.md. Missing/unknown values are distinct from zero. Snapshot input is limited to 16 MiB. Retained-capture MCP tool text is bounded to 64 KiB; transport framing can add bytes.

Thirteen read-only MCP tools are registered, including partial UI context and an API evidence inventory. The private raw-field reader and screenshot/input mailbox are removed. No reflection, native callback hook, arbitrary code tool, process-memory access, OS automation or gameplay mutation is included. API_BOUNDARY.md records the documented lifecycle and source-verified public API mappings separately.

The local runtime directory is transport/storage for detached game exports and curated reference summaries. It is not an external screen/process automation adapter. No network listener is opened. The model/client may send selected state for inference according to its configuration.

Installed reference descriptions carry IDs/origins and current version/mods. External reviewed summaries carry direct URLs, authority and version warnings; official/developer evidence ranks first. Retrieved strings are data, never instructions. Broader web discovery and refresh remain unimplemented.

## Lifecycle limits

GameDisposable establishes cleanup on next initialization; JVM shutdown also writes an unloaded snapshot. There is no established official unload-to-menu callback in this adapter. When updates stop, freshness expires after 30 seconds, so recent state can remain labeled loaded during that interval. Public-API UI context is limited to active view, known overlays, selected subject and room blueprint context. No all-state/menu coverage is claimed. Stale observations now report current loaded state as unknown, while retaining the last observed loaded flag.

## OpenAI connection

Use an existing Codex client signed in with ChatGPT and connect the local stdio MCP. The mod/MCP reads no account credentials and performs no inference calls. A custom in-game chat/authentication client remains future work. Existing official references and eligibility/preview caveats are retained in REFERENCES.md.

## Source and context evidence

API_ESTABLISHMENT.md records the reviewed capability matrix. api-audit.json and syx_api_manifest.py contain compiler-resolved public member references, source declaration anchors and hashes. The agent can query this evidence with get_game_api_support. This metadata is not an arbitrary API invocation interface. UiContextCollector reads fixed public getters during the game after-update callback and is captured in the same detached snapshot; it neither traverses private fields nor captures the screen.

## On-demand consistency and limits

Snapshot query batches remain pinned to one cached export. `query_live_entities` is a separate update observation with request ID, session, tick, capture time, current scene and UI context. An entity ID lookup uses the game's public lookup; unfiltered scans use bounded array-slot cursors. Each cursor page samples the current mutable scene. Pages can miss or repeat moving/replaced entities; no cross-page consistency claim is made. A paused fixture verifies complete traversal, not an active-city snapshot guarantee.

The wire protocol has only fixed, independently validated fields and no expression evaluator. Requests are capped at 8 KiB, responses at 64 KiB, each scan at 10,000 slots, projected rows at 100, stat comparisons at four, selected stat IDs at twenty, and returned stat cells at 100. An eight-second client deadline prevents hanging when the script no longer updates. Missing scene/session/unknown-stat/timeout failures are explicit. Predicate getter failures are counted and prevent treating filtered absence as established.

## Exposed content observations — 0.8.0

The UI collector samples three known public roots on the update thread. A bounded typed visitor reads exposed section/switch children, mapped text and control flags into flat detached nodes. Repeated object references become local node references, preventing repeated traversal. Limits apply across all roots; truncation and opaque/read-error nodes remain explicit. The text is untrusted data. Input values, private wrappers, arbitrary panel collection, renderer output, tooltip storage and global layer ordering are not read.

WorldGen editing flags are workflow data and may persist after changing views. Use active_view for the current UI mode. Battle deploying is a public logical flag; the pinned start overlay is private, so this flag alone cannot prove active combat. Test-only retreat coverage establishes restoration/session rotation, not an observable battle-outcome feed for arbitrary game battles.

## Published battle status and input-consumption flags — 0.9.0

Scene army/division values are detached during the game after-update callback. Engagement comes from the battle worker's latest published status buffer and may lag or persist while workers are paused. These observations are not a synchronized full combat log or an instantaneous fighting guarantee. Counts and raw morale remain separate, explicitly scoped quantities.

The context includes latest public global/view hover-consumption flags. They expose input-consumption evidence without enumerating the private manager collection or synthesizing production input. A private result screen can consume hover while every mapped overlay flag is false. That does not make its identity, text or outcome available. Tests use game-internal public dispatch; the shipped mod remains observational.

The optional person relationships projection and selected-person snapshot share one typed DTO builder. Public getters run on the update thread; room names/IDs, stored home coordinates and division IDs are copied immediately. No retained scratch coordinate or game object crosses into the daemon. Getter failure is distinct from an unassigned/null relationship. These are recorded assignments, not an activity or UI-selection model.

## Multi-provider requirement

PROVIDERS.md adds Claude subscription, Claude API and DeepSeek API support alongside OpenAI. The required product design provides the common in-game chat/session-history interface in IN_GAME_CHAT.md, backed by a local conversation coordinator and provider adapters. Existing external clients are development bridges; their configurations alone do not complete provider support. Provider/account credentials and inference stay outside the observational game bridge/MCP. Future in-game adapters must preserve query bounds, context/freshness semantics, tool-call IDs and cited references across providers, and must never switch provider or billing route silently. Configuration templates do not constitute authenticated integration tests.

## Retained entity selections and observer phase — 0.11.0

`capture_live_entities` requests one bounded after-update observation, including original scene/UI context, then retains immutable encoded detached DTOs inside this MCP server. Creation returns metadata and a token only. `read_entity_capture` pages that retained observation, preserving tick/time/session; current snapshot status is separate. Paging does not reread game objects. No global simulation/battle-worker transaction is claimed.

Capture protocol 2 uses the same fixed-key mailbox, but requires cursor zero and ID projection, allows 2,000 rows / 100,000 scanned slots / 4,000 projected stat cells and a 2 MiB local response. An incomplete scan, excess matching rows or predicate error fails instead of retaining a partial selection. The server stores at most three captures for 120 seconds each; tokens are server-local, and fresh loaded same-session/version observations are required. Legacy protocol 1 and `query_live_entities` retain their previous smaller bounds and mutable cursor semantics.

Each SCRIPT instance registers its sampler with public `GAME.addAfterUpdate`; its SCRIPT update method performs no sampling. Source/binary review and the copied-game run establish that this callback still runs when a menu pauses simulation with requested speed nonzero. The hook is source-verified public API, not a documented stable script contract. Standalone menu callbacks and instant unload detection remain unavailable.

## Spatial observations — 0.12.0

`query_live_tiles` uses a separate fixed 15-key tile mailbox, sharing the POSIX request lock with entity queries. The IO daemon parses a detached request; only the registered game after-update observer reads terrain, floor, coordinate-aware room, mineral and path APIs. It scans at most 4,096 tiles and returns at most 100 selected rows, with session/tick/time/scene/UI context. Local response and actual MCP tool text are each capped at 64 KiB; protocol framing can add bytes. Oversize responses fail instead of silently truncating.

Coordinates are rectangular, with exclusive upper bounds and row-major rectangle offsets. Each page is a separate mutable observation; entity capture tokens do not retain tile pages. Group-level available/data distinguish missing floor/room/mineral values from getter failures. Predicate errors make matching absence/count unknown. The schema and structured field definitions are exposed through game_query_help.on_demand_tiles. No arbitrary member path, setter, input or rendering call is added.

Public RoomSingleton coordinate getters refresh internal scratch caches. Scalar/string values are copied immediately on the game update thread. Shared room-map records do not identify unique room instances; instance_room_id is populated only for RoomInstance. These are map observations, not UI selection. Path component flags do not establish a route for a specific agent or construction suitability; mineral amounts do not establish production yield or deposit lifetime.

## Required common chat interface and local history

IN_GAME_CHAT.md establishes one in-game composer/transcript/chat list/session log across every supported provider and subscription/API route. A local coordinator should handle durable conversation IDs, event history, asynchronous provider requests and bounded MCP tool orchestration. The exporter session UUID is a runtime observation identity, not a stable save GUID; cross-load continuation must be explicit and historical evidence must retain its original identity/time. DeepSeek requires a first-class API path behind this interface, without making an external coding client a player prerequisite.

This is a required design, not implemented functionality. Public GUI hooks for the mod's own panel still need review/validation; accepting input in that panel does not authorize native input, screenshots, private game UI traversal or gameplay control. Current observation tests do not validate chat/history or authenticated inference.
