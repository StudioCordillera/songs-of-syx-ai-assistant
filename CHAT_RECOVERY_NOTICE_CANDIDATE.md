# Plain recovery notice candidate

`dev/chat_recovery_candidate.py` adds an unshipped simple Coordinator subclass for the finite gaps found in [helper-process crash checks](CHAT_PROCESS_RECOVERY.md). It keeps the production action parser, durable admission journal, conversation lifecycle, plain IPC2 encoding and database schema. Only caller-owned disposable state and history under repository `runtime/` are accepted, before the parent can create its action journal. Production entry points and the tested player bundle do not import it.

Two short notices accompany the existing connection/error/status text:

- **Earlier reply interrupted; no automatic retry.** The selected chat's latest durable turn has the production `interrupted` status, and no reply task is active. The notice describes stored status, without asserting a crash cause, recovered stream or external billing outcome. A later durable turn supersedes it.
- **Earlier Send outcome unknown; no automatic retry.** The candidate observed a duplicate Send whose request ID is already acknowledged in the journal but has no saved turn. The base dispatcher still handles the duplicate first and creates no task, turn or provider request. The warning belongs only to an existing simple Pro chat. The old journal has no payload/outcome metadata: the original action could have been something else, and acknowledgement does not prove delivery, failure, absence of billing or an exact original question.

The unknown-action observation is kept only in memory, with at most 100 chat entries. A later durable turn supersedes it; an active task temporarily suppresses recovery warnings. A helper restart can reconstruct it from another observed duplicate, but merely opening a history cannot reconstruct a missing journal payload. Eviction or no replay therefore supplies no guarantee of a warning. No original request is resubmitted and no new game/session identity is invented.

The candidate appends the warning to the base notice for encoding, then restores the base value even on write failure. Existing connection and rejection information stays present; repeated writes do not accumulate warnings. History/events are not changed for presentation. Each latest-turn query returns one row but may scan history because the production schema has no new chat-first turn index; large-history/concurrent cost acceptance remains open. This is helper-side presentation, not game-thread work.

[CHAT_RECOVERY_NOTICE_VALIDATION.json](CHAT_RECOVERY_NOTICE_VALIDATION.json) records three candidate process termination/reopen cases and three fresh unchanged-base cases from the shared harness. The parent SIGKILLs only its own child. In separate restart processes, candidate IPC2 notice text round-trips for admission-only and interrupted-stream cases; completed-answer replay produces no warning. Automatic sync selects the original chat, replay creates no provider call, and a new explicit request completes once with a fresh bounded historical context and clears the warning. Synthetic MCP schemas/status and fake inference keep these checks credential/network/game independent.

Eight additional offline cases cover disposable state/history admission before journal creation, unchanged history, chat isolation, completed replay, later turns, active-task suppression, the 100-chat cap, deleted/non-Pro refusal and write-failure restoration. These are finite helper/model/transport-text checks. There is no native panel rendering, readability/notice wrapping, physical input, real provider, actual MCP transport restart, production entry-point lock, every-crash-timing, power-loss or player-release acceptance. Earlier native evidence keeps its original source and scope. Unknown/oversized display stays unread; no badge, target chip or gameplay command is added.

Reproduce without credentials or the licensed game:

```sh
.venv/bin/python dev/check_chat_process_recovery.py --candidate --output runtime/chat-recovery-notice.json
.venv/bin/python dev/check_chat_process_recovery.py --output runtime/chat-recovery-notice-baseline.json
.venv/bin/python -m pytest -q test_chat_recovery_candidate.py test_chat_process_recovery.py
```

Next: bounded peer critique when the CLI lane is available; durable action-outcome design and actual helper/transport lifecycle; native notice layout/readability and scene/race checks; then paired actual-Pro/core/distribution gates before any player promotion. The warning candidate does not complete those goals.
