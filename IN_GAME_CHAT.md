# Required in-game chat client and session history

Added 2026-10-17 at the user's request. **Required feature; experimental implementation in progress, acceptance gates remain open.** See [the development implementation](CHAT_BACKEND.md). The user must have a usable chat client inside Songs of Syx for every supported provider and authentication choice. An API connection, MCP configuration or external terminal client alone does not complete provider support.

This includes DeepSeek: connecting a DeepSeek API account must lead to the same in-game conversation interface, without requiring the player to find a separate compatible client. Existing Claude Code/Codex configurations are development bridges, not the finished player experience. See [PROVIDERS.md](PROVIDERS.md) for authentication requirements and pending account tests.

## Player experience

Open the assistant in the game, choose a provider/model and subscription or API route, and connect using the supported official authentication flow. The panel shows the active connection in plain language. Create a named chat, ask a question, see the answer arrive, inspect its game observations and citations, and continue the conversation. Previous chats remain accessible under their game-session history.

The same message composer, transcript, chat list and session log work across providers. Switching provider must not change whether a client exists, erase history, silently change billing, or silently send an earlier transcript to another provider. A deliberate switch offers a new chat or explicit continuation with the new provider and records that choice.

## Requirements and acceptance gates

| ID | Required behavior | Evidence required before completion |
| --- | --- | --- |
| AI-CHAT-001 | Provide one in-game chat panel for every supported provider/authentication route, including DeepSeek API | Complete the same connect, ask, follow-up and history flow in the game for each route; an external client demonstration is insufficient |
| AI-CHAT-002 | Offer a composer, send/stop, readable streamed answers, a scrollable transcript and visible connection/generation/error status | Real replies and cancellation work without freezing game updates/rendering; failed/interrupted replies remain distinguishable from completed replies |
| AI-CHAT-003 | Support multiple separate chats: create, name, select and reopen them without mixing messages | Two interleaved chats in one game session preserve independent histories and model context |
| AI-CHAT-004 | Associate each chat and log event with explicit game-session and chat identities | Separate UUIDs distinguish runtime game sessions and durable conversations; two games/chats cannot overwrite or silently share context |
| AI-CHAT-005 | Keep a durable local transcript and session log, accessible from the in-game interface | Restart/reopen tests recover chats, messages, timestamps, provider/model/authentication route and completed/failed/cancelled turn status, including recovery from an interrupted write |
| AI-CHAT-006 | Record useful, expandable evidence for each answer: selective tool requests/results, observations and cited references | The player can inspect bounded tool evidence with request/capture/session IDs, original tick/time and coordinates/paths where applicable; errors and unavailable data are retained explicitly |
| AI-CHAT-007 | Read fresh game status and relevant UI context when answering; preserve historical provenance in logs | A reload/new game rotates the observation session; old chat data is labeled historical and never presented as freshly observed state; ambiguous UI references remain explicit |
| AI-CHAT-008 | Use a provider-independent conversation/tool loop and the same bounded read-only MCP tools | A real DeepSeek API question invokes selective game tools and returns a cited answer through the in-game panel, then a follow-up uses that chat's context; repeat for the other required routes |
| AI-CHAT-009 | Provide an in-game connection/setup experience with explicit provider, model and subscription/API billing route | A player can configure, connect, verify status and understand an authentication/quota/model error without needing an external coding client or terminal workflow; eligibility restrictions remain visible |
| AI-CHAT-010 | Keep histories outside game saves and live game exports; exclude credentials and provider-internal reasoning from logs | Storage inspection finds no keys, tokens, authorization headers or hidden reasoning; safe local export/delete controls act on the selected chat/session, with clear retention behavior |
| AI-CHAT-011 | Keep UI, network and tool execution responsive and bounded | Provider/network work runs outside the game update/render thread; disconnect, retry, timeout and stop do not stall play or silently duplicate a submitted message |
| AI-CHAT-012 | Handle game UI focus and lifecycle transitions through supported in-process APIs | Typing/clicking the mod's own panel does not trigger unrelated game actions; supported city/world/battle/menu transitions preserve chat identity and recover or clearly report panel unavailability; unsupported standalone menus remain a tracked API gap |
| AI-CHAT-013 | Render citations and untrusted model/game/reference text safely | References display their source/URL, version compatibility and observation age; text is data, not an instruction to invoke game setters or arbitrary code |
| AI-CHAT-014 | Preserve explicit provider/account boundaries on switching and errors | Changing provider or billing route requires a deliberate user choice, shows whether prior conversation context will be sent, and logs a provider-change event; quota/authentication errors never trigger another route silently |

Mocked replies, setup profiles and local MCP health checks do not satisfy the authenticated in-game acceptance gates. Current 0.12.0 tests establish public game observation behavior, not this chat interface or history feature.

## Session and conversation model

The exporter's `session_id` identifies one loaded runtime observation session. It changes on creation/reload and is not a permanent save-file identity. No stable public save GUID has been established. The interface must not invent one or silently merge different loads because their names match.

A durable `chat_id` identifies a particular conversation independently of provider-side conversation IDs. A local session record groups chats and events by observed runtime session, start/end information when available, and an optional player-supplied label. Each turn records the runtime session it actually observed. After reload/restart, history remains accessible; continuing an old chat in a new runtime session is explicit, records the boundary, and reacquires current observations. Different chats never share provider context implicitly.

Log events include a stable event/turn ID, chat ID, observed runtime session ID when known, timestamp, role/event kind, provider/model/route, text or bounded tool evidence, citations and status. A new-game/unloaded state can have no current loaded-game identity. Store visible assistant output and useful tool evidence, not provider-internal reasoning or unrestricted full game dumps. Retention and size limits must preserve a clear distinction between retained, summarized and unavailable evidence.

## Intended implementation boundary

The game mod owns its chat panel and uses appropriate public game GUI/script APIs. Rendering and accepting player input in this panel are different from controlling the game's existing UI: no screenshots, native input, private UI traversal or gameplay automation is introduced. An opt-in prototype now uses a separate source-verified public GUI section and widgets; broad input/lifecycle validation and product completion remain pending.

A local chat coordinator should own conversation persistence, cancellation and provider adapters. It obtains game observations through the existing bounded MCP interface. Provider inference and supported SDK/client authentication belong there, outside the game update thread; credentials are excluded from game saves, snapshots, reference records and committed configuration. The game-state bridge and MCP remain observational and make no inference requests.

DeepSeek requires a first-class API adapter behind this interface. A Claude Code configuration is useful for development but must not be the player's only way to use DeepSeek. Subscription adapters must follow the provider's permitted official authentication and entitlement route; where an eligible route is unavailable, show the limitation rather than scraping tokens or silently billing an API account. Provider-specific streaming/tool-call/continuation behavior must be verified independently.

Implement the shared panel, local history and provider-independent conversation loop together with a usable DeepSeek API path. Do not defer the interface indefinitely while counting backend configurations as completed support. Broader game-state/public-API coverage remains an independent continuing objective.

## Current authenticated implementation checkpoint

The shared panel now completes two-turn questions for DeepSeek API and Claude subscription in separate chats, including actual selective queries and guide URLs. Rename/evidence/export/confirmed deletion and explicit attachment after reload pass isolated GUI tests. Claude API is implemented with a missing-key/no-subscription-fallback gate, without authenticated API-key evidence. OpenAI, in-game connection setup, multiline/keyboard work and broad scene coverage remain open. See [current evidence](CHAT_VALIDATION.json) and [implementation limits](CHAT_BACKEND.md).
