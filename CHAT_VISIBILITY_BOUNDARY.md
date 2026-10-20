# Native reply visibility boundary

This is a finite developer probe against shipped 0.71.44 source/binary, **not an official documented visibility contract**. [Static review](CHAT_VISIBILITY_BOUNDARY_REVIEW.json) pins selected source/disassembly hashes and four external compiler probes. [Native evidence](CHAT_VISIBILITY_VALIDATION.json) pins the published player JAR, exact fixture/verifier sources, copied-save integrity, copied-mod restoration and explicit clean completion. No new production getter or badge is shipped.

Three own-widget phases in a disposable copied city demonstrate concrete limits:

- A tooltip's own drawing callback executes, then the public tooltip box can already be empty when the panel renders. The engine clears its normal box after drawing; emptiness queried later cannot prove that no tooltip covered text.
- An overlapping own popup and reply both execute render callbacks while the public popup flag is true. A callback and activated panel do not prove an unobscured reply.
- With UI hidden, the panel remains activated while its reply callbacks stop and game updates continue. Activated is not visible.

Actual read-only MCP verifies the existing popup/hidden flags during held phases. It does not expose a new tooltip/occlusion or focus contract. The fixture uses public own UI actions, no operating-system input, screenshots, provider calls, gameplay commands or saves. Render-thread GUI sampling here is a test boundary probe, not approval for production game-state traversal outside the update callback. Normal profiles/saves are untouched.

Selected public routes include `IMouseMessage.get`, `GBox.emptyIs`, `VIEW.hideUI` and own `Interrupter.isActivated`. The inspected `IMouseMessage.isOn` is package-private and rejected by external compilation; no private workaround is used. Source review of render order and manager layers explains the observations without copying proprietary source into this repository. This is not an exhaustive proof that no public visibility route exists.

The [detached display candidate](CHAT_DISPLAY_CANDIDATE.md) therefore requires an explicit conservative visibility gate. It cannot derive that gate from these negative signals. Automatic clearing remains unimplemented; an explicit player read policy or a separately reviewed conservative adapter is needed. Continue independent core/UX work while that contract is unresolved.

Reproduce with the licensed-game, copied-save, Java and full-JDK arguments described in [CONTRIBUTING.md](CONTRIBUTING.md), using `dev/run_read_fixture.py --case chat-visibility`. The runner takes the shared native fixture lock, checks source/JAR provenance and requires all three phases plus clean completion, no known crash markers, restoration and unchanged copied save. Run `dev/review_chat_visibility_boundary.py --help` for the separate static review. No general all-menu, pixel, human-read or physical-input acceptance is claimed.
