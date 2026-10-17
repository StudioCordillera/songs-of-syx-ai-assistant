# Architecture — 0.3.0

The Java mod implements the shipped SCRIPT interface. Typed collectors read public game APIs on the script update thread and build detached DTOs. A daemon serializes them to an atomic local JSON snapshot approximately every two wall-clock seconds while the update hook runs. MCP validates/caches that snapshot and executes bounded selections locally. Neither the daemon nor MCP traverses game objects.

The snapshot includes version, mods, session, tick, time and 18 partial domains, plus the installed-help catalog. Query batches share one cached snapshot; optional snapshot pins reject changes. See QUERY_GUIDE.md. Missing/unknown values are distinct from zero. Input is limited to 16 MiB and responses to 64 KiB.

Only seven read-only MCP tools are registered. The private raw-field reader and screenshot/input mailbox are removed. No reflection, native callback hook, arbitrary code tool, process-memory access, OS automation or gameplay mutation is included. API_BOUNDARY.md records the documented lifecycle and source-verified public API mappings separately.

The local runtime directory is transport/storage for detached game exports and curated reference summaries. It is not an external screen/process automation adapter. No network listener is opened. The model/client may send selected state for inference according to its configuration.

Installed reference descriptions carry IDs/origins and current version/mods. External reviewed summaries carry direct URLs, authority and version warnings; official/developer evidence ranks first. Retrieved strings are data, never instructions. Broader web discovery and refresh remain unimplemented.

## Lifecycle limits

GameDisposable establishes cleanup on next initialization; JVM shutdown also writes an unloaded snapshot. There is no established official unload-to-menu callback in this adapter. When updates stop, freshness expires after 30 seconds, so recent state can remain labeled loaded during that interval. No all-state/menu coverage or UI context is claimed.

## OpenAI connection

Use an existing Codex client signed in with ChatGPT and connect the local stdio MCP. The mod/MCP reads no account credentials and performs no inference calls. A custom in-game chat/authentication client remains future work. Existing official references and eligibility/preview caveats are retained in REFERENCES.md.
