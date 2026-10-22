# Plain recovery notice candidate

`dev/chat_recovery_candidate.py` adds an unshipped simple Coordinator subclass for the finite gaps found in [helper-process crash checks](CHAT_PROCESS_RECOVERY.md). It keeps the production action parser, durable admission journal, conversation lifecycle, plain IPC2 encoding and existing history fields/version. The current candidate adds only a chat-first turn index in disposable history. Only caller-owned disposable state and history under repository `runtime/` are accepted, before the parent can create its action journal. Production entry points and the tested player bundle do not import it.

Two short notices accompany the existing connection/error/status text:

- **Earlier reply interrupted; no automatic retry.** The selected chat's latest durable turn has the production `interrupted` status, and no reply task is active. The notice describes stored status, without asserting a crash cause, recovered stream or external billing outcome. A later durable turn supersedes it.
- **Repeated request ID; original outcome unknown. No automatic retry.** The candidate observed a duplicate Send whose request ID is already acknowledged in the journal but has no saved turn. The base dispatcher still handles the duplicate first and creates no task, turn or provider request. The warning belongs only to an existing simple Pro chat. The old journal has no payload/outcome metadata: the original action could have been something else, and acknowledgement does not prove delivery, failure, absence of billing or an exact original question.

The unknown-action observation is kept only in memory, with at most 100 chat entries. A later durable turn supersedes it; an active task temporarily suppresses recovery warnings. A helper restart can reconstruct it from another observed duplicate, but merely opening a history cannot reconstruct a missing journal payload. Eviction or no replay therefore supplies no guarantee of a warning. No original request is resubmitted and no new game/session identity is invented.

The candidate appends the warning to the base notice for encoding, then restores the base value even on write failure. Existing connection and rejection information stays present; repeated writes do not accumulate warnings. History/events are not changed for presentation. The original candidate query could scan unrelated history on every refresh. The indexed follow-up below addresses that specific read path; startup/concurrent cost acceptance remains open. This is helper-side presentation, not game-thread work.

[CHAT_RECOVERY_NOTICE_VALIDATION.json](CHAT_RECOVERY_NOTICE_VALIDATION.json) records three candidate process termination/reopen cases and three fresh unchanged-base cases from the shared harness. The parent SIGKILLs only its own child. In separate restart processes, candidate IPC2 notice text round-trips for admission-only and interrupted-stream cases; completed-answer replay produces no warning. Automatic sync selects the original chat, replay creates no provider call, and a new explicit request completes once with a fresh bounded historical context and clears the warning. Synthetic MCP schemas/status and fake inference keep these checks credential/network/game independent.

Eight additional offline cases cover disposable state/history admission before journal creation, unchanged history, chat isolation, completed replay, later turns, active-task suppression, the 100-chat cap, deleted/non-Pro refusal and write-failure restoration. These are finite helper/model/transport-text checks. There is no native panel rendering, readability/notice wrapping, physical input, real provider, actual MCP transport restart, production entry-point lock, every-crash-timing, power-loss or player-release acceptance. Earlier native evidence keeps its original source and scope. Unknown/oversized display stays unread; no badge, target chip or gameplay command is added.

Reproduce without credentials or the licensed game:

```sh
.venv/bin/python dev/check_chat_process_recovery.py --candidate --output runtime/chat-recovery-notice.json
.venv/bin/python dev/check_chat_process_recovery.py --output runtime/chat-recovery-notice-baseline.json
.venv/bin/python -m pytest -q test_chat_recovery_candidate.py test_chat_process_recovery.py
```

Next: bounded peer critique when the CLI lane is available; durable action-outcome design and actual helper/transport lifecycle; native notice layout/readability and scene/race checks; then paired actual-Pro/core/distribution gates before any player promotion. The warning candidate does not complete those goals.

## Indexed latest-turn follow-up — developer-only

[CHAT_RECOVERY_INDEX_VALIDATION.json](CHAT_RECOVERY_INDEX_VALIDATION.json) pins the new candidate source/tests, a fresh eleven-phase native notice run and owned-process recovery checks. The isolated candidate creates `recovery_candidate_turns_chat` on `turns(chat_id)` once at construction. Its latest-turn SELECT explicitly requires that index and retains insertion order through SQLite's implicit rowid. A conflicting partial/composite/collated or wrong-table index refuses without replacement. No event/turn payload, history version, production store or player bundle changes.

A synthetic history with one old selected turn and 20,000 newer unrelated turns exercises both an old selected result and no matching turn. SQLite 3.53.4 reports index seeks without a temporary sort; measured VM operations fall from 60,016 to 18 and from 60,012 to 12 respectively. These finite instruction counts describe SELECT work, not elapsed time, game FPS, every history size or concurrent schema acceptance. One-time index construction scans existing turns and may block startup; migration cost/limits require review before any promotion. Reads are uncached and tests observe a second connection's committed status/new-turn writes while refusing its uncommitted state. Reopening through the base store retains schema version 1 and original history.

The seven added offline cases cover populated-history migration/seeks, external commits/rollback, base-store reopen and four conflicting index definitions. Earlier reports remain historical. The new native run retains interrupted/unknown-Send model rows, draft/style/geometry, two fake providers/four rounds, completed/cancelled turns and no external inference. It proves no physical input, unobscured display, receipt, crash/power-loss or paid/player acceptance. The CLI lane still has an existing process not established idle; no new overlapping Claude invocation or model/quota claim is made.

The separate [durable observation extension](CHAT_DURABLE_RECOVERY_CANDIDATE.md) persists a bounded unknown-Send warning only after an observed duplicate. The base candidate remains in-memory. Both now compare the previous/latest turn identity so completing an older turn cannot resolve another admitted Send. Earlier tuple-comparison evidence remains historical.
