# Automatic current-game connection

The paired simple DeepSeek Pro mod/helper use IPC protocol 2. Opening AI chat prepares or selects a conversation attached to the current runtime without New or Attach. The helper must still be running through start-chat.sh; the mod does not manage its process. New chat remains available for a separate conversation.

Before preparing a conversation or sending a question, the helper asks the actual MCP game_status tool for a fresh, live observation matching the requesting panel's runtime UUID. A mismatch, unavailable observation or four-second status timeout refuses admission. This preserves the existing exporter’s up-to-30-second unload/freshness limitation; it is not an immediate unload hook or a multi-process presence registry.

Selecting an older conversation shows its history. Sending the next question automatically connects that conversation to the loaded runtime, records a session boundary and resets provider memory. Original events retain their original sessions; earlier user/assistant text is labeled Earlier game. Running turns and missing keys cannot transfer an attachment. Repeated durable action IDs are not replayed. No request is sent merely by opening, selecting or filtering chats.

This load lists chats currently attached to the runtime; All chats includes earlier runtime attachments. Both SQL filters run before the existing 100-chat cap and select only DeepSeek Pro/API chats. These are independently bounded lists, not a complete history census or permanent world grouping. Reloading the same save creates a new runtime identity. No guessed save name, file identity or world association is introduced.

The simple player has no manual attachment button. Advanced developer mode retains its explicit attachment behavior. A new simple panel refuses protocol 1 or an expired/future helper heartbeat and preserves the unsent draft; update/restart the mod and helper together. Unsent drafts survive authoritative chat selection changes in a bounded in-memory cache of 100 chats. Drafts are not durable across game exit.

## Public API and scope

Production remains read-only with eighteen MCP tools and nine Java classes. The audit adds one public source-verified member: snake2d.util.sprite.text.Str.add(CharSequence), anchored at Str.java line 64 in the pinned licensed source. It appends/resizes the mod-owned composer buffer when restoring a bounded draft. It is not gameplay mutation or a stable documented SCRIPT contract. The retained declaration catalog contains all 385 current references; source/binary pair and catalog checksum were checked without claiming a new full scan.

## Validation

AUTO_CONNECTION_VALIDATION.json records the exact candidate’s copied-city opening, two simulated replies across a real reload, immutable historical events/provider context reset, This load / All chats filters, wrong-session admission refusal, protocol-version refusal/recovery, draft round-trip and visible coordinator errors in an older selected chat. CHAT_FOCUS_VALIDATION.json records current own-widget focus/wrapping, missing-key rejection and view persistence. These fixtures use public mod-owned controls and a copied save, with no operating-system input or screenshots. Simulated provider replies are distinct from USER_TEST_VALIDATION.json’s two real paid Pro turns. Feature reports pin source/JAR/fixture hashes and are published only after copied-mod restoration, save-integrity and clean-completion checks pass.

Unread badges, durable world grouping, managed helper startup, drag/resize/themes, target attachments and gameplay execution remain separate unfinished work in PLAYER_EXPERIENCE_PLAN.md. Finite fixtures do not establish every menu, physical input, screen scale or large-history performance.
