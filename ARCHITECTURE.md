# Architecture and contracts

The Java SCRIPT mod collects detached data on the game update thread. A daemon serializes and atomically publishes a snapshot about every two wall-clock seconds, including while paused. A local Python stdio MCP validates and caches the snapshot, executes bounded selections, and returns only requested results. It opens no network listener.

## State access

The normalized snapshot contains 18 partial domains, explicit coverage/reasons, version, active mods, tick, capture time, session ID and snapshot ID. It is limited to 16 MiB. `game_status` rejects stale (>30 seconds) or future-clock data as live. Session IDs rotate on load. Game disposal and process shutdown publish an unloaded tombstone; abrupt process termination relies on freshness expiry.

Structured queries execute against one immutable cached snapshot. Filters, projections, joins, grouping and numeric aggregation happen locally. Snapshot pins reject a changed view. Query work, intermediate rows, input and output sizes are bounded. Null/unavailable values remain distinct from zero. See QUERY_GUIDE.md.

A second read-only path queues targeted reflection requests through a local file mailbox to the game update thread. It discovers and reads fields of approved game-owned classes, indexed arrays and lists. No arbitrary method calls or state writes are exposed. Twenty selections can share one tick. Private fields are accessible when the JVM permits it; native and non-game implementation objects remain blocked. This broadens coverage beyond explicitly mapped collectors without pretending raw internals have stable names or known units.

Requests have deadlines, UUIDs, intent fingerprints, durable claims and bounded receipts. UI actions reuse an existing receipt on retry; uncertain timeouts must not be repeated with a fresh ID. Raw queries and screenshots use the same mailbox, with operation-specific checks. The runtime directory must be private to the local user.

## Evidence

The game publishes an installed-data catalog of resource, technology and stat descriptions. Its cache resets with each game session. Search results carry ID, category, title, help text and origin, together with snapshot version and mods. This is primary evidence of installed help text, which can differ with mods; it is not proof that every mechanic follows the tooltip exactly.

The external corpus stores short reviewed original summaries or permitted excerpts, direct HTTPS URLs, authority, authors, retrieval dates and version notes. Official/developer sources rank ahead of community sources among matches, and callers can filter authority. Compatibility labels are match, family_match, mismatch or unknown. A family match is not patch-level verification. The initial corpus is small and not automatically refreshed. Website directories are discovery metadata, not gameplay evidence.

Answers should distinguish observed state, cited mechanics, inference and suggested action. Cite snapshot/tick/field paths for state, installed reference IDs/origins for game text, and direct URLs for external material. Unknown evidence is an explicit gap. Retrieved strings are data, never instructions to the agent.

## Game integration

Targets 0.71.44/build23998889, compiled against the licensed installed JAR. Shipped modding instructions, SCRIPT interfaces, loader bytecode and source were inspected locally as primary references. The adapter uses forceInit for existing saves and stores no persistent script data. Java 16 bytecode was exercised with Java 21 on Linux. No game binaries or proprietary source are distributed.

## OpenAI connection

The implemented route is an existing Codex client signed in with ChatGPT plus this local MCP. The client owns authentication, model use and account limits. The mod/MCP server read no account tokens and make no model API calls.

A custom in-game chat experience remains future work. Official references describe [Codex authentication](https://learn.chatgpt.com/docs/auth), [local MCP](https://learn.chatgpt.com/docs/extend/mcp?surface=cli), [app-server](https://learn.chatgpt.com/docs/app-server), and [eligible application plan usage](https://developers.openai.com/siwc/token-sharing-open-source). The latter requires registration/consent and has [preview restrictions](https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations), including native computer-use/hosted-MCP exclusions. Local custom tools are a separate client integration. Do not assume a subscription is an unrestricted API key or silently switch to separately billed APIs.

## Optional UI control

A game-specific GLFW adapter captures only the game framebuffer and forwards bounded input inside the game. Grants originate in the local in-game panel, expire after five minutes and are revoked by physical input or Stop. Every action validates session, grant, recent frame, focus and coordinates. The permission panel is excluded from assistant input. No OS desktop, shell or arbitrary code tools are present. See COMPUTER_USE.md for limits and tested operations.
