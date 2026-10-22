# Completed local recovery-notice peer review

A bounded, tool-free local Claude Code invocation completed on **claude-opus-5-5**, requested through the `opus` alias at high effort. It returned one successful result in approximately 63 seconds. The two supplied coordinator sources were pinned before subsequent fixes; [invocation evidence](CLAUDE_UX_COLLABORATION.json) records input/source/final-text hashes and actual outcome. No file editing tools, additional CLI job, credits purchase, fallback or limit bypass was used. This was a focused critique, not a full UI generation or native game audit.

## Accepted changes

- The journal cannot prove that an original action was Send, or identify its original chat from a changed duplicate payload. The visible warning is now **Repeated request ID; original outcome unknown. No automatic retry.** A new case first journals Select in one chat, then repeats its ID as Send in another; no turn or provider task is created and the warning makes no Send claim. The warning belongs to where the duplicate was observed, not a proven original action/chat.
- The durable subclass now explicitly refuses construction when the history connection has foreign keys disabled. It leaves the setting and existing observations intact. Ordinary ChatStore already enables foreign keys; this check makes the deletion-cascade assumption explicit.
- An empty base notice no longer adds a leading space to the warning. Encoding preserves the base notice after writing.

The reviewer also confirmed the turn-identity clearing rule, active-task suppression and matching 100-entry/position bounds. These observations are peer findings, with independent tests and native integration reported separately.

## Findings retained as limits

The proposed automatic deletion of malformed/orphan/unsupported observation records was not adopted. This developer candidate deliberately refuses invalid persisted state; silently repairing it would require a separate migration/data-loss policy. Provider/route/model retargeting and concurrent live writers are unsupported. Foreign-key enforcement covers normal owned chat deletion, without proving hostile or corrupt database behavior.

A pre-await memory snapshot could become stale if a caller injects nested `write_ui`/notice mutations during dispatch. The actual parent serial serve/dispatch implementation does not call `write_ui` inside dispatch. This review supplied only the two candidate classes, and explicitly treated hidden base behavior conditionally. Reentrant wrappers and concurrent writers remain outside the accepted seam; this is not a general concurrency fix. The suggested one-refresh lag likewise depends on a nested base UI write absent from the inspected implementation.

Observation persistence can fail during UI refresh. The candidate propagates that failure instead of asserting successful persistence or retrying inference; a useful player-facing storage failure policy remains a promotion gate. Full notice bounds, startup index costs, actual helper/transport interruption, physical input, visibility/read receipts and paid/player acceptance remain separate work. The new native durable-notice fixture establishes only its finite authored-state/model checks.
