# Helper-process crash boundaries

This developer-only regression terminates an owned Python subprocess with SIGKILL and reopens its disposable SQLite history in a different Python process. It uses the production simple Coordinator, action parser, ChatStore and 21-tool BlueprintConversation with synthetic MCP schemas/status and fake inference. There is no native game, stdio MCP process, credential access, network inference or changed production source. It complements the separately scoped [native graceful recovery](NATIVE_CHAT_RECOVERY.md); neither report substitutes for the other.

Three fixed checkpoints establish different outcomes:

| Termination point | Recovery outcome |
| --- | --- |
| Action admission committed, before current-game validation/turn creation | The action ID is acknowledged on replay, with no turn, user event or inference. Acknowledgement proves durable admission only, not delivery or a completed answer. |
| Provider emitted a partial fragment while its turn is running | Startup marks the turn interrupted. The volatile fragment is lost; it is absent from reopened history, the replacement UI frame and new provider context. No cancellation/error event is fabricated by abrupt termination. |
| Completed answer and turn committed, before any UI frame/ack is written | Exactly one durable completed answer survives. Replaying the old Send does not create another turn or provider request. |

Each restart first parses/dispatches the identical original Send ID before selecting a chat. The durable journal prevents new work. Automatic current-load sync then selects the existing chat. Only a **new explicit request with a new ID** creates one fake provider call, with a fresh provider context and the bounded historical user/completed-answer text appropriate to that checkpoint. No previous assistant/tool-role continuation is replayed. The fixed current-game callback hold controls the first checkpoint; the other checkpoints execute the real conversation task. The harness does not run the production `serve(args)` entry point or test its history lock, credential setup, transport startup or polling lifecycle.

[CHAT_PROCESS_RECOVERY_VALIDATION.json](CHAT_PROCESS_RECOVERY_VALIDATION.json) records exact source/test hashes, the three process outcomes, full offline checks and unchanged player bundles. The parent kills only the subprocess it created, verifies its PID checkpoint and SIGKILL exit, bounds waits and cleans up. Children receive an allowlisted environment and only a fresh mode-0700 temporary directory; the internal worker refuses normal history paths. No discovered game, Claude or helper process is interrupted.

The current simple UI does not have a dedicated crash-recovery notice for the interrupted database status or admission-without-turn gap. These are remaining player-experience issues, not successful transparent recovery. A durable acknowledgement must never become a promise that a paid request ran, and automatic retry could duplicate external billing. Pending paid calls, network outcomes, all crash timings, power-loss/filesystem durability, history-lock contention, native draft/reconnect races and display/read receipts remain unvalidated. No badge, target chip, drag/resize redesign or gameplay action is shipped by this work.

Reproduce without credentials or the licensed game:

```sh
.venv/bin/python dev/check_chat_process_recovery.py --output runtime/chat-process-recovery.json
.venv/bin/python -m pytest -q test_chat_process_recovery.py
```

This SIGKILL regression targets Linux/POSIX. Its three cases also run in the ordinary offline suite. The tested player ZIP and historical native reports retain their own source/date and acceptance scopes.
