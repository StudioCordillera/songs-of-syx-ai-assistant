# Unread receipts and runtime history — developer candidate

`dev/chat_history_candidate.py` implements an isolated SQLite candidate for UX-01/UX-10 in [the player plan](PLAYER_EXPERIENCE_PLAN.md). It is not imported by the coordinator, included in the release whitelist or connected to the game's panel. No badge, automatic attachment, durable world grouping, IPC change or gameplay command is shipped. Normal histories, credentials and saves were not opened by these tests; all databases are disposable pytest fixtures.

## Why individual event receipts

The base store has global integer event sequences that can be reused after deletion. A cumulative high-water sequence can also lose a reply whose final event was saved earlier but whose turn finishes later. This candidate instead acknowledges an explicit bounded list of unique event UUIDs, with the chat and original observed session. Each UUID must be that completed turn's latest nonblank visible final assistant event in the specified chat/session. A mixed wrong-chat/session/stale batch fails atomically. The caller remains responsible for proving actual display; receipt validation alone cannot prove that the player saw a reply.

The persisted receipt key is `(chat_id, turn_id)`: repeated acknowledgement or a duplicate final event for an already read turn cannot add another unread reply. No other turns are implicitly marked read. Empty/whitespace answers, partial/tool events, running, failed, cancelled and interrupted turns are excluded from successful unread counts. Failures still need a separate attention/error design; suppressing a successful-reply count is not an instruction to hide errors. Text/provenance are not rewritten or copied into the receipt table.

`initialize()` is explicit and owns one transaction. It creates separately versioned extension tables/indexes while preserving base `user_version=1`, then baselines already completed visible replies so an upgrade does not flood the badge. A saved final event on a still-running turn is not baselined; later completion becomes unread. Repeated initialization never re-baselines new replies. Ordinary base-store opens do not initialize this extension or mark anything read. Unsupported versions, nested transaction ownership or scan overflow fail without pretending to establish complete counts.

This is an evaluated extension-table approach, not a selected production migration contract. Existing base methods with their own transactions are not nested inside migration/admission. An injected SQLite authorization failure after schema creation rolls back the entire candidate migration. Actual Python store implementations extracted from both the current and retained previous player ZIP can open, recover interrupted turns, create/delete chats and return to the candidate without foreign-key failures. That finite compatibility test does not establish compatibility with arbitrary future clients, schema tampering or retention tools.

Those legacy clients do not send display acknowledgements. New completed replies created during a legacy-client interval remain unread on return to the candidate, even if the player may have viewed them there. The candidate cannot reconstruct that visibility and does not silently mark them read.

## Bounded semantics and current limits

- Completed-assistant scans refuse beyond 10,000 rows or 2 MiB of UTF-8 payloads, rather than returning partial/zero counts. Acknowledgements accept 1..100 event UUIDs and use one write transaction. Unread metadata uses one SQLite read transaction. These are explicit candidate budgets; larger-history migration, performance, concurrency across independent writers and production admission remain open.
- `chats()` applies simple DeepSeek Pro and runtime filters in SQL before the existing 100-chat limit. `attached` matches the current mutable runtime attachment; `history` also matches recorded event sessions after reattachment. It does not infer a stable world from names, associate reloads or reconstruct every empty historical attachment. A permanent identity or explicit player-labeled group is still needed for cross-load world filtering.
- No implicit oldest-unseen acknowledgement, automatic game switch, retry or provider request is performed. A versioned display protocol, real visible/scrolled/hidden-UI acknowledgement, unread aggregation across all chats/worlds, presence/admission routing and the game-native numbered launcher remain to be implemented and validated.

## Reproduce and evidence

Run `.venv/bin/python -m pytest -q test_chat_history_candidate.py` without any key or game installation. Twelve authored cases cover legacy baselining/pending completion, correct and wrong-chat/session receipts, atomic rejection, duplicate/restart persistence, out-of-order completion, event-sequence reuse, ordinary non-recovery opens, failure/empty/partial exclusions, exact UTF-8 boundaries, migration rollback, actual latest/previous-client compatibility and filtering before the cap. Budget failures use deliberately reduced candidate limits; they are not a representative large-history performance workload.

[CHAT_HISTORY_CANDIDATE_VALIDATION.json](CHAT_HISTORY_CANDIDATE_VALIDATION.json) pins the tested source and bundle hashes. The full repository suite passes 317 tests; the unchanged production payload retains its earlier exact-source Pro/native evidence and runnable latest/previous ZIPs. No game/provider/native fixture rerun is claimed for this developer-only SQLite addition.

## Later player-pair compatibility recheck

The automatic-connection release ran the full 356-test suite again after promotion, including these twelve candidate cases against the actual new latest and retained previous bundled store code. CHAT_HISTORY_CANDIDATE_VALIDATION.json preserves the original 317-test checkpoint and adds subsequent_player_pair_recheck with exact source/ZIP/store hashes. This does not ship receipts or establish native visibility/world identity.
