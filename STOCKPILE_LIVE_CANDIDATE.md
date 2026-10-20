# Per-warehouse live query candidate

This is **developer-only**, outside `mod/src/main/java`, with no player dispatch, mailbox or MCP tool. The current playable ZIP and its predecessor remain unchanged. [Validation](STOCKPILE_LIVE_CANDIDATE_VALIDATION.json) establishes compilation against the paired licensed 0.71.44 JAR, detached protocol checks and two narrow room-lookup readers; it does not establish runtime collector correctness or release acceptance.

## Intended selective access

`dev/candidates/stockpiles/syx/assistant/StockpileReadRequest.java` sketches an update-thread stored-counter page independent of the cached warehouse prefix. An empty room-ID list traverses current warehouse instance slots; an explicit list binds up to 100 current room IDs and refuses missing/non-warehouse IDs. Required resource keys select up to 100 installed resources. Projection chooses the five raw bookkeeping counters and/or a resource-reference ID. Up to four AND comparisons and an optional active-room predicate filter rows.

The cursor indexes the room/resource matrix, including nonmatches and failed cells. Each proposed callback scans at most 4,096 cells and returns at most 100 matching rows. An empty filtered page can still have a next cursor. Separate pages can change; there is no retained snapshot or cross-page transaction. Returned identity includes room slot, blueprint, anchor, active status and resource key. Room IDs can be reused, and neither IDs nor anchors establish permanent world identity or a UI-selected room.

Counter semantics follow [the established stockpile boundary](STOCKPILE_BOUNDARY.md): assigned crates, stored items, assigned item capacity, reserved stored items and reserved incoming capacity. Zero capacity is a real zero; inactive-room stored bookkeeping is not automatically zero. Counters are not freely usable stock, promised delivery, physical fullness or a yield forecast. Negative raw integer readings must not silently become zero. Exact counter age remains unknown.

## Established static and codec evidence

The paired declaration catalog and source anchors establish public `RoomsMap.max()` and `getByIndex(int)`. Selected shipped bytecode reads the array length or one array slot, with no calls, direct writes, allocations or backwards branches. Lookup itself does not range-check or promise a non-null room; the candidate checks bounds and warehouse type/blueprint before an explicit lookup is accepted. Source allocation/removal paths reuse slots, so treating a slot as a permanent identity would be incorrect. These are shipped-source findings, not separately documented stable mod contracts.

The candidate and unchanged production sources compile together at Java release 16. The standalone harness accepts seven representative frames, refuses 41 malformed/oversized/unknown inputs, and checks 150 signed-int comparisons including minimum/maximum boundaries. It covers duplicate keys/IDs/projections, Unicode resource keys with embedded newlines, invalid UTF-8/base64, UTF-16 length parity, noncanonical integers/UUIDs, framing, deadlines and fixed selection bounds. JVM initialization logs are checked for absence of GAME and SETT initialization; no collector or native fixture runs.

Reproduce with licensed files, without a provider key:

```sh
.venv/bin/python dev/verify_stockpile_candidate.py \
  --game-dir '/path/to/Songs of Syx' \
  --jdk-home '/path/to/jdk' \
  --catalog build/game-api-catalog.json \
  --output runtime/stockpile-candidate-validation.json
```

## Next acceptance work

1. Independently compare candidate rows, ordering, filters, empty pages and cursor/error behavior with direct getters in the disposable copied city. Cover explicit unknown/non-warehouse IDs, active/inactive rooms, session/deadline changes and unavailable scenes; establish removal/reuse behavior rather than assuming it.
2. Implement the strict Python selection/response validator and serialized 64 KiB all-or-error bound, then paired fixed mailboxes under the existing shared request lock. Never move game traversal onto the I/O thread. Verify actual MCP parity and corruption/refusal paths.
3. Measure collector/encoding/transport cost and real cap/fault paths. Add capability discovery, field provenance and an agent-facing example. No unbounded resource registry, arbitrary member invocation or crate scratch handles.
4. Only then integrate production, refresh the public-member audit and run exact-source player/provider/core/distribution gates before promoting once and retaining the actual prior ZIP.

The management-tab route remains open. Inspection of `IManager` and `IFullView` found the stored current view private and no established public current-tab reader in that route. GUI construction/render selection is not a safe substitute. This finite inspection does not prove that no other public route exists; no private access or inferred selection is added.
