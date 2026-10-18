# Required AI provider support

Added 2026-10-17 at the user's request. These requirements extend the existing OpenAI route; they do not replace the internal/public game-API boundary or the full game-state/UI objectives.

## Connection matrix

| Required choice | Required product route / available development bridge | Credential / entitlement owner | Current project status |
| --- | --- | --- | --- |
| OpenAI subscription | Shared in-game chat through a permitted official subscription route; existing Codex MCP configuration is a development bridge | Official client/account | In-game client/authentication pending; original eligibility caveats remain in REFERENCES.md |
| Claude subscription | Shared in-game chat through permitted official subscription authentication; Claude Code MCP profile is a development bridge | Claude Code/account; plan limits apply | Official route checked; MCP/profile templates added; Claude Code 2.1.296 local stdio health check passed; account/model validation pending |
| Claude API | Shared in-game chat with an Anthropic API adapter; Claude Code profile is a development bridge | User's Anthropic API account | Configuration/profile supplied; paid inference validation pending |
| DeepSeek API | Shared in-game chat with a first-class DeepSeek API adapter; Claude Code profile is a development bridge | User's DeepSeek API account | Configuration/profile supplied; paid inference validation pending |

The required player interface is the shared in-game chat client and per-session/per-chat history specified in [IN_GAME_CHAT.md](IN_GAME_CHAT.md). Existing external-client profiles are development bridges only. They do not complete product support, particularly for DeepSeek. The shared interface, persistence and provider adapters remain unimplemented; template availability is not authenticated model validation.

## Requirements and acceptance gates

| ID | Required behavior | Acceptance evidence |
| --- | --- | --- |
| AI-PROVIDER-001 | Let the user explicitly choose OpenAI, Claude subscription, Claude API or DeepSeek API; retain that selection in the future in-game client | In-game provider picker/config round-trip plus visible active provider/model/authentication route; common chat and session history gates in IN_GAME_CHAT.md |
| AI-PROVIDER-002 | Use the same bounded read-only MCP tools, UI context, freshness/session rules, retained-observation semantics and cited knowledge across providers | Each route completes a real selective game question in the shared in-game client, with source IDs/URLs and observation provenance preserved in its chat log |
| AI-PROVIDER-003 | Support Claude subscription through official client/SDK authentication permitted by current provider documentation | User-authorized login and a successful subscribed model request through the shared in-game chat using the local MCP; no credential scraping or guessed third-party entitlement |
| AI-PROVIDER-004 | Support Claude API-key authentication independently of subscription login | Successful in-game chat/tool-call/result round-trip with an Anthropic API key, persistent chat log and correctly identified account/billing route |
| AI-PROVIDER-005 | Support DeepSeek API authentication and its current tool-calling protocol/model capabilities | Successful tool-call/result round-trip and follow-up through the in-game chat against DeepSeek, with session/chat history; no external coding client required; explicit current model selection |
| AI-PROVIDER-006 | Never silently switch provider, account, subscription/API route or endpoint after authentication, quota, model or compatibility errors | Injected failure tests show a clear error and preserve selection; no request reaches another provider |
| AI-PROVIDER-007 | Keep credentials with the client/credential store, outside game saves, game exports, reference records and committed configuration | Credential-boundary inspection and redacted logging tests; the Java bridge and MCP make no inference calls |
| AI-PROVIDER-008 | Preserve tool-call IDs, error results, context boundaries and untrusted-reference handling when adding embedded adapters | Provider-specific adapter tests plus at least one authenticated end-to-end question per route; unsupported capabilities fail explicitly |
| AI-PROVIDER-009 | Show that chosen game observations/reference text go to the selected inference provider, and distinguish plan entitlements from API usage | Clear connection UI and provider/model metadata; no promise that a subscription covers arbitrary API calls |

AI-PROVIDER-010 additionally requires the common in-game panel and durable per-session/per-chat log for every supported provider/authentication route, with the acceptance gates in IN_GAME_CHAT.md. AI-PROVIDER-011 requires a first-class DeepSeek API adapter behind that interface; external Claude Code profiles alone do not satisfy it.

These gates are added requirements, not completed validation. No paid API request or account login was performed while adding them. The installed official Claude Code 2.1.296 client reported Connected for this server using an isolated test configuration; the normal Claude configuration was checked to contain no test entry. Offline shell checks verified that changing profiles clears conflicting credential variables. These checks do not validate provider inference or subscription entitlements. Retained capture/lifecycle behavior has separate evidence in VALIDATION.md and does not establish provider inference support.

## Development bridge: connect an existing Claude Code client

Install this project's Python environment as in INSTALL.md. Copy `claude.mcp.example.json` to `.mcp.json` in the directory where you start Claude Code (merge with existing servers), replace both absolute paths, and use the same state directory as the game. Review the server through Claude Code's normal MCP approval flow. See [Anthropic's stdio MCP reference](https://code.claude.com/docs/en/mcp#option-3-add-a-local-stdio-server).

Choose exactly one profile in `examples/providers/`, source it in that client's shell, then run `claude`. Subscription users use `/login`; API users supply their own key through the indicated environment variable. Confirm `/status` and `/mcp`, then ask for `game_status`, `game_query_help` and a narrow state query. The profiles only affect that shell; they do not edit credentials or account settings. Managed settings, existing credential helpers/profiles and account restrictions may override environment choices, so client status must confirm the actual route. See [Claude Code authentication](https://code.claude.com/docs/en/authentication).

The DeepSeek profile pins the endpoint to `https://api.deepseek.com/anthropic` and maps model slots to the explicit `DEEPSEEK_MODEL` value (default `deepseek-flash`), following [DeepSeek's Claude Code integration](https://api-docs.deepseek.com/quick_start/agent_integrations/claude_code/). Recheck available models before changing this. Native OpenAI-format API adapters should use the provider's documented `https://api.deepseek.com` service rather than treating it as an OpenAI account; see [DeepSeek's first API call](https://api-docs.deepseek.com/).

## Official authentication evidence

Checked 2026-10-17. [Anthropic's plan/Agent SDK notice](https://support.claude.com/en/articles/15036540-use-the-claude-agent-sdk-with-your-claude-plan) currently describes continued subscription-limit access for the Agent SDK and third-party apps, alongside plan-specific API credits. That supports evaluating an official SDK route for a future embedded client; it does not establish every user's eligibility or unrestricted API access. [Claude API authentication](https://platform.claude.com/docs/en/manage-claude/authentication) separately documents API-key authentication. Recheck these policies and the account's actual entitlement when implementing embedded login.

The MCP transport itself is provider independent. Provider-native hosted MCP support is not required for local tool orchestration; the local client/coordinator invokes the stdio server and returns selected tool results to its chosen model. Existing external clients remain development bridges until the in-game interface is implemented. No game-process access moves into a provider adapter.

For the DeepSeek profile, Claude Code is the MCP/tool client and DeepSeek supplies inference. This is not Claude subscription usage. Embedded adapters must also preserve provider-required reasoning/continuation content and streaming tool-call assembly, without exposing internal reasoning in logs; these require provider-specific tests before release.

## Native chat development implementation

A [native DeepSeek transport, shared conversation/history engine and opt-in panel](CHAT_BACKEND.md) now exist. Mocked protocol and local GUI checks do not establish authenticated inference or complete provider support. OpenAI/Claude routes and in-game account setup remain pending.
