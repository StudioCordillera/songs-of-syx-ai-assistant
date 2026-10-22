# Native candidate status wrapping

The unshipped actual-chat layout now places helper/layout/style notices in a fixed 48-unit scroll area instead of silently keeping only the first line. This matters for connection and interrupted/unknown-action explanations: their last sentence can be the part that prevents an accidental retry. Chat choices and Style controls move down 30 internal units, with the transcript beginning at 250; the proposed 640×560 minimum, composer, Send/Stop and draft behavior remain.

`StatusLines.java` wraps detached plain text at the same conservative font-column estimate used by the candidate panel. It preserves Unicode code-point boundaries, displays control characters as spaces, scans at most 4,096 code points and returns at most 64 rows. Space is reserved for a wrapped **[Long status shortened]** marker when either bound is reached. Empty text has one empty row. These are presentation bounds, not full-message receipt or native Unicode/font acceptance.

The panel initializes its own public `GScrollRows` widget before exposing its scroll range. The first fixture incorrectly checked the range before initialization and was rejected; its private copied-game failure log remains, without passing evidence. The corrected source uses the public own-widget initialization route already present in the pinned shipped source. It does not refresh game-state caches, mutate engine pointer/button state or introduce a new game getter.

[NATIVE_CHAT_STATUS_VALIDATION.json](NATIVE_CHAT_STATUS_VALIDATION.json) pairs exact current source/class hashes with:

- Twenty-two native layout checks, including a long synthetic connection/recovery notice at the 640×560 minimum. Joining the wrapped rows preserves the complete finite notice, its scroll range is positive, own supplied scrolling preserves the same composer/draft, and all top-level controls remain inside the panel. Existing Style control separation, gestures, preferences, legacy records, viewport/focus markers and outgoing Send/Stop checks pass again.
- A separate nine-phase actual production Coordinator/default MCP/SQLite recovery run with fake inference and the same changed panel. It preserves the original real-helper lifecycle/reference behavior. This run uses the base Coordinator; it does not integrate or natively display the separate recovery-notice subclass.
- Detached tests for six column widths (including one), Unicode pair boundaries, control spacing, complete omission markers, row/scan bounds, empty status and rejected widths, plus the full offline suite.

The internal native viewport is 1536×768; supplied layout dimensions do not change the engine/window. Supplied own gesture/scroll values and public own-widget routing are distinct from physical input. Bounds/model rows/render callbacks establish no unobscured visibility, human readability, all-font/scale accessibility or read receipt. Long statuses still require the player to scroll; resets/rebuilds return that status area to its start. Recovery-notice transport semantics retain their separate [candidate evidence](CHAT_RECOVERY_NOTICE_CANDIDATE.md). Actual paid calls, native notices from that subclass, broader scene/race cases and paired player-release acceptance remain open.

No production source or player ZIP changes. The previous tested bundle remains retained. Unknown/oversized replies remain unread; no badge, typed chip or gameplay action is shipped.

Reproduce with the [licensed copied-game/Java/JDK arguments](CONTRIBUTING.md) using `dev/run_native_chat_layout.py`, then `dev/run_read_fixture.py --case layout-recovery`. Each runner takes the shared fixture lock itself. Earlier layout/style/recovery reports keep their historical source/date rather than being relabeled as this source.
