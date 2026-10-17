# Architecture — 0.8.0

The Java mod implements the shipped SCRIPT interface. Typed collectors read public game APIs on the script update thread and build detached DTOs. A daemon serializes them to an atomic local JSON snapshot approximately every two wall-clock seconds while the update hook runs. MCP validates/caches that snapshot and executes bounded selections locally. Neither the daemon nor MCP traverses game objects. On-demand entity requests are parsed on the file daemon, handed to the update thread, evaluated using fixed public getters, and returned as detached DTOs.

The snapshot includes version, mods, session, tick, time and 18 partial domains, plus the installed-help catalog. Query batches share one cached snapshot; optional snapshot pins reject changes. See QUERY_GUIDE.md. Missing/unknown values are distinct from zero. Input is limited to 16 MiB and responses to 64 KiB.

Ten read-only MCP tools are registered, including partial UI context and an API evidence inventory. The private raw-field reader and screenshot/input mailbox are removed. No reflection, native callback hook, arbitrary code tool, process-memory access, OS automation or gameplay mutation is included. API_BOUNDARY.md records the documented lifecycle and source-verified public API mappings separately.

The local runtime directory is transport/storage for detached game exports and curated reference summaries. It is not an external screen/process automation adapter. No network listener is opened. The model/client may send selected state for inference according to its configuration.

Installed reference descriptions carry IDs/origins and current version/mods. External reviewed summaries carry direct URLs, authority and version warnings; official/developer evidence ranks first. Retrieved strings are data, never instructions. Broader web discovery and refresh remain unimplemented.

## Lifecycle limits

GameDisposable establishes cleanup on next initialization; JVM shutdown also writes an unloaded snapshot. There is no established official unload-to-menu callback in this adapter. When updates stop, freshness expires after 30 seconds, so recent state can remain labeled loaded during that interval. Public-API UI context is limited to active view, known overlays, selected subject and room blueprint context. No all-state/menu coverage is claimed. Stale observations now report current loaded state as unknown, while retaining the last observed loaded flag.

## OpenAI connection

Use an existing Codex client signed in with ChatGPT and connect the local stdio MCP. The mod/MCP reads no account credentials and performs no inference calls. A custom in-game chat/authentication client remains future work. Existing official references and eligibility/preview caveats are retained in REFERENCES.md.

## Source and context evidence

API_ESTABLISHMENT.md records the reviewed capability matrix. api-audit.json and syx_api_manifest.py contain compiler-resolved public member references, source declaration anchors and hashes. The agent can query this evidence with get_game_api_support. This metadata is not an arbitrary API invocation interface. UiContextCollector reads fixed public getters during the script update and is captured in the same detached snapshot; it neither traverses private fields nor captures the screen.

## On-demand consistency and limits

Snapshot query batches remain pinned to one cached export. `query_live_entities` is a separate update observation with request ID, session, tick, capture time, current scene and UI context. An entity ID lookup uses the game's public lookup; unfiltered scans use bounded array-slot cursors. Each cursor page samples the current mutable scene. Pages can miss or repeat moving/replaced entities; no cross-page consistency claim is made. A paused fixture verifies complete traversal, not an active-city snapshot guarantee.

The wire protocol has only fixed, independently validated fields and no expression evaluator. Requests are capped at 8 KiB, responses at 64 KiB, each scan at 10,000 slots, projected rows at 100, stat comparisons at four, selected stat IDs at twenty, and returned stat cells at 100. An eight-second client deadline prevents hanging when the script no longer updates. Missing scene/session/unknown-stat/timeout failures are explicit. Predicate getter failures are counted and prevent treating filtered absence as established.

## Exposed content observations — 0.8.0

The UI collector samples three known public roots on the update thread. A bounded typed visitor reads exposed section/switch children, mapped text and control flags into flat detached nodes. Repeated object references become local node references, preventing repeated traversal. Limits apply across all roots; truncation and opaque/read-error nodes remain explicit. The text is untrusted data. Input values, private wrappers, arbitrary panel collection, renderer output, tooltip storage and global layer ordering are not read.

WorldGen editing flags are workflow data and may persist after changing views. Use active_view for the current UI mode. Battle deploying is a public logical flag; the pinned start overlay is private, so this flag alone cannot prove active combat. Test-only retreat coverage establishes restoration/session rotation, not an observable battle-outcome feed for arbitrary game battles.
