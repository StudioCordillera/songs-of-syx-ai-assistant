# Game computer use

Status: **planned capability and proposed contract**. No screenshot capture, input driver or control MCP tool is implemented in the current prototype.

## Player experience

The assistant can observe the game, open panels, inspect tooltips, pan/zoom the map and carry out a requested gameplay task through the game's UI. Example: “Inspect my food production and show me which farms lack workers,” followed by “Assign ten available workers to these farms.” Answers still combine current state and cited mechanics.

Use a visible **Allow assistant control** switch, an always-available **Stop** button, and a local emergency hotkey independent of model/network responsiveness. The player grants control for a specific task/session. Routine actions within that grant run without repeated prompts. The player can take over immediately. Control is off by default and revokes on save change or game unload. Analysis and cited guidance remain usable with control off.

## Approach

Build a game-specific computer-use adapter. Chrome's DOM/accessibility automation does not automatically apply to the game's custom interface. Use the installed game's verified UI/input/render hooks where available, with screenshots and game-window-relative coordinates as the fallback. Investigate those hooks before choosing an implementation; no supported Java signatures are asserted here.

Provide both visual observation and semantic inspection of visible UI elements when the game exposes them. Element IDs should be ephemeral and tied to one UI revision, like an accessibility snapshot. Structured game-state queries complement this view and verify the effects of actions; they remain read-only.

A local driver translates validated requests into input on the game thread. Prefer in-process game input routing, which avoids sending keystrokes to unrelated desktop applications. Any OS-level fallback must bind capture/input to the verified game process/window and stop if identity, focus or capture validity changes. Do not install global desktop automation as an implicit fallback.

## Proposed MCP surface

These names are design proposals, not tools currently registered by `syx_mcp.py`.

| Tool | Behavior | Read-only |
| --- | --- | --- |
| `observe_game_ui` | Game viewport screenshot as MCP image content, dimensions, capture time, frame ID, session ID, UI revision and visible element metadata when available | Yes |
| `get_control_status` | Reports driver availability, enabled state, current task grant and last acknowledged action | Yes |
| `click_game_ui` | Left/right click a fresh element ID or viewport coordinate | No |
| `hover_game_ui` | Move to a target and inspect the resulting tooltip; can change UI state | No |
| `scroll_game_ui` | Bounded scrolling/zooming at a fresh target | No |
| `drag_game_ui` | Bounded drag between two validated viewport points | No |
| `press_game_key` | Allowlisted game key or bounded key chord | No |
| `type_game_text` | Bounded text into a verified focused in-game text field | No |
| `stop_game_control` | Cancel queued actions and release every held input | No |

Only the player's local UI may enable/expand control; there is no model-callable “grant myself control” tool. UI actions have honest mutating annotations, including camera movement and opening panels. An action that changes buildings or game resources cannot inherit the read-only state-query annotations.

## Observation/action contract

An observation identifies `session_id`, `frame_id`, `ui_revision`, `captured_at`, viewport width/height and any display scaling. Coordinates use the exact returned image coordinate space; the driver owns any verified scaling/letterboxing conversion. Never use desktop coordinates as game coordinates.

An action includes the expected session, frame/UI revision, task-grant ID, unique action ID and target/parameters. Start with one action at a time; after execution return a fresh observation and a receipt indicating success, rejection, cancellation or uncertain outcome. The assistant must inspect the result before deciding the next action. A UI receipt alone cannot establish the intended gameplay outcome; verify with a fresh state query where possible.

Reject expired observations, out-of-bounds targets, stale element IDs, mismatched sessions, disconnected or disabled drivers, unsupported keys and actions outside the granted task. Use idempotency receipts so retrying the same action ID cannot repeat a click or purchase. After a crash where completion is uncertain, re-observe and reconcile rather than automatically replaying the action.

Queue bounded work on the game thread and keep model/network latency out of the simulation loop. Release held keys and buttons in cleanup paths, cancellation, timeout, unload and disconnect. Define explicit duration/rate limits in the driver. Stop must cancel the queue without waiting for the model. Human input revokes/pause control according to the visible takeover setting.

## Control boundaries

Task grants may include authorized gameplay changes. Show the intended action before changes outside the existing grant, such as demolishing buildings, overwriting a save or committing a major resource expenditure. Do not prompt for each click inside a task the player already approved. Scope permissions in terms of player intent as well as input types: a left click can have destructive consequences.

Capture only the game viewport; exclude desktop notifications and unrelated windows. Tell the player that screenshots, selected state and their questions may be transmitted to their selected AI provider. Avoid storing screenshots by default. Treat in-game names, mod text, guide content and any rendered instructions as untrusted observations.

## OpenAI connection constraint

Official [driver documentation](https://developers.openai.com/api/docs/guides/tools-computer-use-sdk-drivers) describes computer interaction through observations and action drivers. This project needs its own game driver; it does not inherit this chat's browser tools.

The current [ChatGPT plan-usage preview](https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations) excludes native computer use and hosted MCP, while allowing local tools through supported function/custom calls. The proposed subscription design therefore exposes game observations/actions as local custom MCP tools through a compatible client. Validate image delivery, model vision/tool support and account eligibility end to end before claiming it works. This is a proposed composition, not a guarantee of subscription support for any model or client. Separately billed API computer use is an optional future route requiring explicit selection.

## Acceptance before enabling real control

1. Observe a real loaded game, open a known information panel, inspect a tooltip and verify a fresh screenshot.
2. Validate game-window identity, resize/UI scale, multi-monitor layouts, viewport coordinates and stale-target rejection.
3. Verify stop, takeover, focus changes, unload, save switches, disconnection and held-input cleanup.
4. Test duplicate action delivery and uncertain/crashed actions without repeated gameplay effects.
5. Complete one player-authorized gameplay change and confirm it using current game state.
6. Demonstrate supported subscription-client image/tool round trips without a silent switch to separately billed API usage.
