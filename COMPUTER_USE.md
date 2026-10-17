# Optional game computer use

The experimental adapter captures the game's framebuffer and supports hover, left/right click, bounded scroll, allowed key presses and short text entry. These are local MCP tools, not OpenAI's native computer-use API. No desktop, shell, browser or arbitrary code access is exposed.

The player grants control from a persistent in-game panel for five minutes. Physical key presses, mouse presses and scroll revoke it. Stop revokes it immediately. The permission panel cannot be clicked by the assistant. Actions require the correct session, grant ID and a frame captured within five seconds, plus focused settlement view and valid viewport coordinates.

`observe_game_ui` returns an MCP image plus frame/session metadata. `game_ui_action` requires a caller-generated action UUID. Receipts are idempotent: retry with that same ID/parameters after uncertainty, never issue a fresh ID blindly. A new screenshot follows each dispatched action. Dispatch confirms input delivery, not that a game objective succeeded; inspect state and screen afterward.

Live copied-save tests exercised observation, hover, scroll, right click, invalid grants and Stop. Key/text and physical player interactions need further manual checks. Text entry only forwards while a game text listener is active. No drag or held keys are implemented. Permission UI keyboard navigation is excluded.

State queries and reference retrieval are the current development priority. A custom chat UI, richer action planning and full control validation remain future work. [OpenAI driver references](https://developers.openai.com/api/docs/guides/tools-computer-use-sdk-drivers) inform observation/action design; account eligibility and preview limitations require independent verification.
