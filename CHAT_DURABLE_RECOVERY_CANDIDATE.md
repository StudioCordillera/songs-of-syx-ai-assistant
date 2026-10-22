# Durable unknown-Send notice candidate

This is **developer-only**, with no production import or player migration. `dev/chat_durable_recovery_candidate.py` extends the [plain recovery notice candidate](CHAT_RECOVERY_NOTICE_CANDIDATE.md) in caller-owned disposable state/history under `runtime/`. The tested player and native notice fixture still use their existing coordinators. [Evidence](CHAT_DURABLE_RECOVERY_VALIDATION.json) separates the new helper/process checks from the shared parent's native regression.

The old action journal stores admission IDs, without original payloads or delivery outcomes. This extension persists only an **observed uncertainty notice** after the parent sees a duplicate Send ID with no corresponding turn. It does not reconstruct a missing original question, assert that the original action was Send, infer provider delivery/billing, resubmit an action or create a provider task. A journal gap that has never been observed as a duplicate still supplies no such notice.

The separate `candidate_unknown_sends` table retains at most 100 chat entries in observation order. Each entry contains its chat ID and the selected chat's previous latest-turn ID/status, or a null pair when no turn exists. It stores no question, response, credentials, provider payload or new world identity. Existing history fields and `user_version=1` remain unchanged. Positions have an integer primary key constrained to 0..99; chat IDs are unique and deletion cascades with the existing chat foreign key. Loading is limited to 101 rows and validates canonical identities, supported Pro chat ownership and complete prior-turn/status pairs before replacing memory. Invalid data refuses; no automatic repair is attempted.

A new coordinator reads the committed observations without replaying the request. Its acknowledgement remains empty until an actual action arrives. The warning still says **Earlier Send outcome unknown; no automatic retry.** An active reply suppresses presentation without deleting the record. A different latest turn supersedes it; deleting the chat removes it. Reobserving a duplicate refreshes its place in the 100-chat limit. Eviction remains a disclosed limit, including after restart.

This work also fixes the shared parent's comparison: a status update to the same older turn cannot resolve a different unknown Send. The comparison now uses turn identity. The recorded status remains the original observation; it is not silently relabeled. Completing that older turn preserves the warning across reopening, while a genuinely different latest turn clears it.

Changed observation sets replace at most 100 rows in one SQLite transaction. Failure rolls back both deletion and insertion, restores the previous memory map and propagates the error. It never falls back to retrying inference or claiming that the observation was durably saved. Unchanged refreshes read bounded rows but do not rewrite them. The seam assumes one owning coordinator; concurrent live coordinators/writers are not supported. Commit-to-notice gaps, startup index construction cost, hostile filesystems, storage failure and power-loss durability are not generally resolved.

## Validation

Fourteen offline cases cover restart without replay, unobserved admission gaps, later-turn clearing, original session provenance, durable capacity/eviction order, chat deletion, unchanged-refresh writes, transaction failure/rollback, disposable-path admission, two malformed persisted records, a three-process boundary, finishing an older turn and active-task suppression.

`dev/check_durable_recovery.py` creates a private synthetic history and runs three directly owned child processes with no inherited provider credentials, game, MCP or inference. First, a duplicate of an explicitly authored journal gap commits the observation and writes the existing IPC2 notice. The parent SIGKILLs that child only after its committed checkpoint marker. The second process restores the same plain notice with no action dispatch/acknowledgement, then authors one later turn without inference and clears the observation. A third process verifies that clearing persists. This is one post-commit crash boundary, not a pending paid request, every crash timing, power loss or production helper-entrypoint acceptance.

A fresh eleven-phase native notice run exercises the changed shared parent, preserving draft/style/geometry and existing interrupted/unknown text with four fake provider rounds and two real reference calls. **That native fixture does not instantiate the durable subclass.** New native durable transport/notice acceptance, physical input, rendered/unobscured/readable text, receipts, paid inference and player-release gates remain open. Unknown/oversized replies stay unread, and no badge, chip or gameplay action ships.

Reproduce the new helper/process checks without credentials:

```sh
.venv/bin/python dev/check_durable_recovery.py --output runtime/durable-recovery.json
.venv/bin/python -m pytest -q test_chat_durable_recovery_candidate.py test_chat_recovery_candidate.py test_chat_process_recovery.py
```

The source-pinned report records the full offline suite and unchanged current/previous player bundles. The previous index checkpoint's CI completed successfully. One existing Claude CLI process was not established idle; no overlapping invocation, new peer critique or model/quota/credit diagnosis is claimed. Next: bounded peer critique, native integration with actual helper/transport failures, startup migration bounds, typed targets/display and exact-source Pro/core/distribution gates before promotion.

## Native and peer-review follow-up

[Native durable integration](NATIVE_CHAT_DURABLE_NOTICES.md) now exercises the subclass in a fixed thirteen-phase own-panel case, separately from the original non-integrated evidence above. [Completed Claude critique](CLAUDE_RECOVERY_REVIEW.md) led to neutral repeated-request wording, a foreign-key guard and spacing fixes. The current warning is **Repeated request ID; original outcome unknown. No automatic retry.** This does not identify the original action type/chat from a changed duplicate payload. The original fourteen-case/process report remains historical; current evidence adds three focused cases and source-matched native/process regressions.
