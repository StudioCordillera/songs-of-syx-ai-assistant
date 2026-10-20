# Per-warehouse live query candidate

The historical draft below is **developer-only**, outside `mod/src/main/java`, with no player dispatch, mailbox or MCP tool. The draft checkpoint retained its then-current playable ZIP and predecessor. A later production mapping now exists separately: see [the current live reads](STOCKPILE_LIVE_READS.md). Historical candidate evidence below keeps its original source/JAR scope. [Validation](STOCKPILE_LIVE_CANDIDATE_VALIDATION.json) establishes compilation against the paired licensed 0.71.44 JAR, detached protocol checks and two narrow room-lookup readers; its scope excludes runtime collector correctness and release acceptance. The separate [native candidate check](STOCKPILE_LIVE_NATIVE_VALIDATION.json) now establishes finite getter/page/filter parity described below, with player integration still pending.

## Intended selective access

`dev/candidates/stockpiles/syx/assistant/StockpileReadRequest.java` sketches an update-thread stored-counter page independent of the cached warehouse prefix. An empty room-ID list traverses current warehouse instance slots; an explicit list binds up to 100 current room IDs and refuses missing/non-warehouse IDs. Required resource keys select up to 100 installed resources. Projection chooses the five raw bookkeeping counters and/or a resource-reference ID. Up to four AND comparisons and an optional active-room predicate filter rows.

The cursor indexes the room/resource matrix, including nonmatches and failed cells. Each proposed callback scans at most 4,096 cells and returns at most 100 matching rows. An empty filtered page can still have a next cursor. Separate pages can change; there is no retained snapshot or cross-page transaction. Returned identity includes room slot, blueprint, anchor, active status and resource key. Room IDs can be reused, and neither IDs nor anchors establish permanent world identity or a UI-selected room.

Counter semantics follow [the established stockpile boundary](STOCKPILE_BOUNDARY.md): assigned crates, stored items, assigned item capacity, reserved stored items and reserved incoming capacity. Zero capacity is a real zero; inactive-room stored bookkeeping is not automatically zero. Counters are not freely usable stock, promised delivery, physical fullness or a yield forecast. Negative raw integer readings must not silently become zero. Exact counter age remains unknown.

## Established static and codec evidence

The paired declaration catalog and source anchors establish public `RoomsMap.max()` and `getByIndex(int)`. Selected shipped bytecode reads the array length or one array slot, with no calls, direct writes, allocations or backwards branches. Lookup itself does not range-check or promise a non-null room; the candidate checks bounds and warehouse type/blueprint before an explicit lookup is accepted. Source allocation/removal paths reuse slots, so treating a slot as a permanent identity would be incorrect. These are shipped-source findings, not separately documented stable mod contracts.

The candidate and unchanged production sources compile together at Java release 16. The standalone harness accepts seven representative frames, refuses 41 malformed/oversized/unknown inputs, and checks 150 signed-int comparisons including minimum/maximum boundaries. It covers duplicate keys/IDs/projections, Unicode resource keys with embedded newlines, invalid UTF-8/base64, UTF-16 length parity, noncanonical integers/UUIDs, framing, deadlines and fixed selection bounds. JVM initialization logs are checked for absence of GAME and SETT initialization; no collector or native fixture runs.

The commands below reproduce the historical candidate from a separate checkout of `8da6798`, with licensed files and no provider key. The legacy verifiers refuse the current production checkout to avoid shadowing the packaged reader or relabeling its evidence. Use STOCKPILE_LIVE_READS.md for current checks.

```sh
.venv/bin/python dev/verify_stockpile_candidate.py \
  --game-dir '/path/to/Songs of Syx' \
  --jdk-home '/path/to/jdk' \
  --catalog build/game-api-catalog.json \
  --output runtime/stockpile-candidate-validation.json
```

## Finite copied-city candidate evidence

`dev/run_stockpile_candidate.py` compiles the unregistered request and an explicit replacement of the test-only stockpile scenario into private fixture classes. The published player JAR stays unchanged. A separate [current player regression](STOCKPILE_CURRENT_REGRESSION_VALIDATION.json) reruns the original global getter/DTO and retained-observation MCP checks against that JAR; it does not expose the new per-room query. The runner reuses the shared device lock, isolated-home/copied-save path checks, sanitized environment, clean-game-log guard and copied-mod restoration. No provider key is required.

Thirteen native cases execute 72 requests across one warehouse and 42 resources. All 8,170 reported counter comparisons match the separate resource-overload public getters. Fourteen small pages reproduce the complete 42-cell matrix; nine empty filtered pages advance to the terminal cursor. Combined predicates retain original positions, projections preserve mandatory identities without extra fields, zero capacity stays zero, and explicit lookup agrees. Missing/non-warehouse IDs, an unknown resource, expired/cross-session requests and past-end cursors refuse explicitly. Immediate deactivate/reactivate verifies retained stored counters and active predicates, then restores the room. Actual world-view access reads the underlying instantiated city.

Two temporarily changed public scope flags test the refusal branches and are restored within the callback; this does **not** prove actual battle/setup transitions. No room removal/reuse, absent-city, malformed-registry or per-cell exception test is claimed. The maximum observed response is 19,097 bytes, not proof of a general byte-bound refusal policy. Thirty-one warm combined request-frame/parse/collect/encode samples have median 0.490 ms and maximum 1.166 ms in this paused fixture; this is not standalone collector, transport, concurrent-load, large-city or FPS acceptance.

The first native attempt passed its checks but was refused by an overbroad new log check that mistook ordinary captured shutdown stderr for a failure. The runner now reuses `native_game_completion.require_clean_game_log`; two subsequent native runs complete cleanly, including the final projection/zero-capacity follow-up pinned in the report. Passing acceptance requires fixture results, zero process exit, the finite known-crash-marker check, copied-mod restoration and unchanged copied save together.

```sh
xvfb-run -a -s '-screen 0 1280x960x24' .venv/bin/python dev/run_stockpile_candidate.py \
  --game-dir '/path/to/Songs of Syx' \
  --jdk-home '/path/to/jdk' --java '/path/to/game-compatible/java' \
  --save runtime/smoke.save
```

## Acceptance backlog recorded at this candidate checkpoint

1. Extend the finite native parity above to multi-room ordering, removal/reuse, actual unsupported scene/lifecycle transitions, absent-city, per-cell exceptions and hard scan/row limits. Do not generalize the one-room result to complete logistics or all menus.
2. Implement the strict Python selection/response validator and serialized 64 KiB all-or-error bound, then paired fixed mailboxes under the existing shared request lock. Never move game traversal onto the I/O thread. Verify actual MCP parity and corruption/refusal paths.
3. Measure collector/encoding/transport cost and real cap/fault paths. Add capability discovery, field provenance and an agent-facing example. No unbounded resource registry, arbitrary member invocation or crate scratch handles.
4. Only then integrate production, refresh the public-member audit and run exact-source player/provider/core/distribution gates before promoting once and retaining the actual prior ZIP.

The management-tab route remains open. Inspection of `IManager` and `IFullView` found the stored current view private and no established public current-tab reader in that route. GUI construction/render selection is not a safe substitute. This finite inspection does not prove that no other public route exists; no private access or inferred selection is added.
