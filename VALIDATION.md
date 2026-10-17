# Foundation validation

Verified locally on 2026-10-17 with Python 3.14 and official MCP Python SDK 2.3.0.

`python -m pytest -q`: **10 passed**.

Checks cover missing state, demo labeling, live freshness and unloaded state rejection, future-clock rejection, snapshot consistency, unavailable domains, pagination and escaped JSON pointers, schema/corruption handling, result size bounds, corpus citation/version metadata, and a real stdio MCP client/server session. The transport check initializes a client, discovers all three tools and their read-only annotations, executes status and state queries, and verifies an invalid query returns a tool error.

Not verified: compilation or installation of a Java game mod, live game-state extraction, full game-state coverage, real guide/forum retrieval, subscription authentication/inference, in-game UI, Windows/macOS behavior, and large-city performance. These remain roadmap items.

Computer-use update: documentation-only design change. No screenshot/input implementation is present or validated. The existing 10-test result applies to the read-only MCP prototype, not game control.
