# Architecture — 0.6.0

The Java mod implements the shipped SCRIPT interface. Typed collectors read public game APIs on the script update thread and build detached DTOs. A daemon serializes them to an atomic local JSON snapshot approximately every two wall-clock seconds while the update hook runs. MCP validates/caches that snapshot and executes bounded selections locally. Neither the daemon nor MCP traverses game objects.

The snapshot includes version, mods, session, tick, time and 18 partial domains, plus the installed-help catalog. Query batches share one cached snapshot; optional snapshot pins reject changes. See QUERY_GUIDE.md. Missing/unknown values are distinct from zero. Input is limited to 16 MiB and responses to 64 KiB.

Nine read-only MCP tools are registered, including partial UI context and an API evidence inventory. The private raw-field reader and screenshot/input mailbox are removed. No reflection, native callback hook, arbitrary code tool, process-memory access, OS automation or gameplay mutation is included. API_BOUNDARY.md records the documented lifecycle and source-verified public API mappings separately.

The local runtime directory is transport/storage for detached game exports and curated reference summaries. It is not an external screen/process automation adapter. No network listener is opened. The model/client may send selected state for inference according to its configuration.

Installed reference descriptions carry IDs/origins and current version/mods. External reviewed summaries carry direct URLs, authority and version warnings; official/developer evidence ranks first. Retrieved strings are data, never instructions. Broader web discovery and refresh remain unimplemented.

## Lifecycle limits

GameDisposable establishes cleanup on next initialization; JVM shutdown also writes an unloaded snapshot. There is no established official unload-to-menu callback in this adapter. When updates stop, freshness expires after 30 seconds, so recent state can remain labeled loaded during that interval. Public-API UI context is limited to active view, known overlays, selected subject and room blueprint context. No all-state/menu coverage is claimed. Stale observations now report current loaded state as unknown, while retaining the last observed loaded flag.

## OpenAI connection

Use an existing Codex client signed in with ChatGPT and connect the local stdio MCP. The mod/MCP reads no account credentials and performs no inference calls. A custom in-game chat/authentication client remains future work. Existing official references and eligibility/preview caveats are retained in REFERENCES.md.

## Source and context evidence

API_ESTABLISHMENT.md records the reviewed capability matrix. api-audit.json and syx_api_manifest.py contain compiler-resolved public member references, source declaration anchors and hashes. The agent can query this evidence with get_game_api_support. This metadata is not an arbitrary API invocation interface. UiContextCollector reads fixed public getters during the script update and is captured in the same detached snapshot; it neither traverses private fields nor captures the screen.
