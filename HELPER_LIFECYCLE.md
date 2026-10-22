# Production helper entry-point lifecycle regression

`dev/check_helper_lifecycle.py` exercises the actual `python -m syx_chat_service` entry point, file IPC, SQLite startup recovery, history lock and newly created stdio MCP processes. It uses explicit private state/history/scratch directories, an authored snapshot and no provider key. No provider factory is injected. The production missing-key guard prevents inference; no licensed game, native UI or paid call is involved. This complements the separately scoped [native candidate notices](NATIVE_CHAT_NOTICES.md) and [owned-process crash checks](CHAT_PROCESS_RECOVERY.md).

The fixture establishes these finite outcomes:

1. A real helper starts with one explicitly authored running history row. Its normal startup recovery marks that row interrupted. A fresh protocol-2 sync passes through the actual MCP status call and selects the persisted Pro chat despite missing provider credentials.
2. While that helper owns the history lock, the fixture authors a second running row without an inference task. A competing production helper, using the same history and a different private state directory, exits with the expected lock refusal. The running row and all events remain unchanged: refusal occurs before startup recovery.
3. The fixture identifies only the direct stdio child of its task-created helper using kernel PID metadata. The installed MCP SDK creates that child in a **separate session**, so killing the helper's process group alone would not establish transport termination. The fixture explicitly SIGKILLs the owned MCP child, then sends SIGINT to the helper if needed so the production async context closes/reaps it. Child removal is verified before restarting. This is abrupt transport loss plus helper cleanup, not abrupt helper death or a general pipe-EOF test.
4. A different helper process starts against the same history/state and creates a new stdio MCP child. It recovers the second authored row. The action file still holds the old sync ID: its durable acknowledgement leaves the new coordinator unselected. A **new** sync selects the original chat through the actual fresh MCP status route; it creates no extra chat or fabricated permanent world identity.
5. A keyless Send is durably acknowledged but rejected with the existing missing-key notice, before any turn/event/inference. The test retains the action-versus-outcome distinction rather than treating acknowledgement as delivery.

[HELPER_LIFECYCLE_VALIDATION.json](HELPER_LIFECYCLE_VALIDATION.json) records exact source/test and installed MCP stdio-module hashes/version, three entry-point invocations, two successful helper/MCP startups, lock ordering, recovered authored rows, cleanup, full offline checks and unchanged player bundles. The helper and its child have different PIDs after restart. The snapshot keeps its original DEMO-unverified version and synthetic qualifiers; clearing its demo admission flag is an explicitly authored positive control, **not native game truth**.

The subprocess environment is allowlisted, with explicit private state/history arguments; HOME is not reassigned. No provider credential environment or env-file flag is supplied; the normal credential-file route is not selected. This is configuration evidence, not a filesystem trace of every imported library. Only the fixture's own helper/direct child is signaled; no game, Claude, unrelated helper, arguments/environment of other processes, process memory or screenshots are inspected. The fixture cleans its own directories and process handles. It uses no shared native profile and therefore does not take or interfere with the native-game fixture lock.

These checks do not establish recovery of a paid stream/tool round, external billing outcome, all concurrent SQLite writers, every crash timing, power-loss durability, native draft/scene/reconnect/display behavior or human reading. The helper's selected chat is intentionally in memory; a retained sync acknowledgement alone cannot reconstruct it. The current player bundle is unchanged, and the separate recovery-notice redesign remains unshipped. Unknown/oversized replies remain unread.

Reproduce on the supported Linux/POSIX environment without a key or licensed game:

```sh
.venv/bin/python dev/check_helper_lifecycle.py --output runtime/helper-lifecycle.json
.venv/bin/python -m pytest -q test_helper_lifecycle.py
```

The fixed wait bounds and owned-child checks fail rather than claiming success if startup, lock refusal, IPC or cleanup do not finish. Prior native/fake-provider reports retain their original scopes and hashes. Next: durable action-outcome design, native helper/transport failure presentation, stable preferences, target/display integration and paired actual-Pro/core/distribution gates before player promotion.
