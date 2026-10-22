# Native durable uncertainty notice integration

This is a **developer-only own-panel fixture**, not a player release. The fixed `layout-durable-notices` case instantiates `DurableRecoveryCoordinator` through the existing production MCP/conversation/history boundary, with fake inference and explicitly authored recovery states. [Current evidence](NATIVE_CHAT_DURABLE_NOTICES_VALIDATION.json) pins the sources/classes and separates the thirteen-phase durable case from a fresh eleven-phase plain-parent regression.

The first eleven phases retain automatic native session connection, a resized/themed panel and preserved composer/draft, partial output, unpaused open/closed progress, closed completion/reopen, Stop, graceful Coordinator/SQLite recovery, completed-Send deduplication and interrupted/unknown notice rows. The unknown request is an explicitly refused admission followed by a duplicate ID; the fixture does not simulate provider delivery or billing.

After the native model contains the unknown-request notice, the verifier gracefully stops the owning coordinator task, closes its store and constructs a new durable coordinator against the same history. It checks an initially empty acknowledgement, the retained observation and unchanged turns/events. Normal native auto-sync selects the existing chat. The verifier does **not** replay the uncertain Send. A distinct new frame says "Restored observed uncertainty after helper reopen." beside the neutral uncertainty notice, preventing acceptance from an old pre-restart frame alone.

The twelfth native phase requires that new frame, the same chat/composer object/draft, Parchment theme and resized geometry, with no pending action or provider task. The native fixture acknowledges only that its own model contains those rows. Then the verifier explicitly authors a later completed turn without inference. It requires the observation table to be empty, emits a distinct clearing frame, and the thirteenth phase checks that old unknown/interrupted text is absent while chat/draft remain intact.

Exactly two fake provider instances make four rounds and two original-reference calls, as before. The history contains one inferred completed turn, one cancelled inferred turn, one authored interrupted turn and one authored completed turn. There is one completed assistant answer. The authored completion is not another model reply. The factory refuses a third provider, so restart/notice handling cannot silently trigger more inference.

The local Claude Code Opus 5.5/high [focused review](CLAUDE_RECOVERY_REVIEW.md) informed neutral repeated-request wording, an explicit foreign-key guard and empty-base-notice spacing. Three new offline cases reproduce those fixes; the earlier fourteen durable cases remain. A fresh three-process check retains the post-commit child SIGKILL, restored IPC2 warning without replay and durable clearing. This process check uses no game/MCP/provider and is separate from the graceful native reopen.

## Limits and reproduction

The game, verifier Python process and MCP stay running during native coordinator/store reopens. This is not abrupt native helper death, real network interruption, pending paid work, every crash timing or power loss. Own model rows/render callbacks prove no physical input, unobscured pixels, human reading, accessibility or receipts. The status area can scroll; no player unread clearing or badge is added. Startup index construction, storage-failure UX, reentrant/concurrent writers, typed targets, actual-Pro and paired release gates remain open. Normal saves/configuration and current/previous player bundles are preserved.

Use the licensed copied-game arguments from [CONTRIBUTING.md](CONTRIBUTING.md):

```sh
.venv/bin/python dev/run_read_fixture.py --case layout-durable-notices \
  --game-dir "$SYX_GAME_DIR" --save runtime/smoke.save \
  --java "$SYX_GAME_JAVA" --jdk-home "$SYX_JAVA_HOME"
```

The runner takes the shared fixture lock, allows only fixed own-class overlays with licensed engine precedence, checks exact clean-completion phase counts, rejects source changes during execution and verifies copied-mod restoration/save integrity. No `.env` or key is used. Earlier reports retain their original hashes, notice wording and non-integrated scope. The previous durable-candidate commit's CI completed successfully. Next: actual helper/transport failure presentation, startup migration bounds and target/display integration before player promotion.
