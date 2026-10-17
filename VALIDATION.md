# Validation — 2026-10-17

## Automated checks

- 29 Python tests pass: snapshot validation/freshness, demo isolation, unload, paging, bounded results, corpus provenance/version labels, MCP transport/tool annotations, mailbox retries, screenshot validation, structured filters/joins/projections/grouping/aggregation/nulls/limits and invalid specifications.
- Java policy/JSON tests pass, including nine rejection cases.
- Java raw field reader/parser fixture tests pass, including private fields, field projection, indexed array selection, cycles and seven invalid-request cases.
- All mod sources compile against the installed game with Java 16 target bytecode.

## Live copied-save validation

Installed game: 0.71.44, Steam build23998889. Linux, isolated user profile, Java21. The test bootstrap uses a copy of an existing save; no original save was modified. The loaded settlement had 216 counted residents and 31 employment records. All 18 domain collectors returned explicitly partial data.

The exporter produced 720 installed reference records. Live raw root discovery returned 11 roots; reading player field definitions, a resource's private/internal attributes, resource collection size (42), and clock definitions succeeded through the actual mailbox. Structured ranking of stockpile values succeeded after using the discovered `stockpile_stored` field. Missing `/amount` was correctly rejected rather than invented.

Previous live runs validated screenshot MCP image content, hover, scrolling, right click, fresh post-action screenshots, invalid-grant rejection, Stop, and unloaded tombstones after graceful shutdown. The control test harness grants only within its isolated test process; production requests cannot self-grant. Physical enable/stop interaction, key/text behavior and other platforms need further manual validation.

## Practical limits

This is a working experimental adapter, not complete state mapping or a finished game assistant. Raw reflection exposes reachable permitted game objects, with bounds, cycles and blocked-object descriptors. Units/encodings are not inferred. There is no measured frame-time budget, large-city stress test, save/reload matrix, or cross-platform certification. The external corpus has two reviewed summaries, one historical developer reply and one version-family community guide; broader official coverage and automated refresh remain work.

No in-game chat/login or end-to-end autonomous advisory quality evaluation has been completed. Existing Codex+MCP is the supported prototype connection.
