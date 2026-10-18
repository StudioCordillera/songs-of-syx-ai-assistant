# Regional scheduled-output candidate boundary

This is a reviewed candidate for expanding the world domain, **not an implemented MCP counter table**. The current player remains the world-faction-context build. [REGIONAL_OUTPUT_BOUNDARY_REVIEW.json](REGIONAL_OUTPUT_BOUNDARY_REVIEW.json) pins the licensed game/source pair, public declaration catalog, selected method fingerprints and a successful ordinary-mod compilation probe. [REGIONAL_OUTPUT_READER_VALIDATION.json](REGIONAL_OUTPUT_READER_VALIDATION.json) adds finite copied-game reader evidence. Neither changes source-verified members into separately documented stable official contracts.

## Public stored-reader route

For a loaded resource, `TR.get(resource)` identifies its tradable wrapper; `RD.OUTPUT().get(tradable)` identifies the resource output. `yearlyAccumilation.get(region)` reads its stored integer. The inherited `DataAbs` reader decodes packed region data; the reviewed region data provider indexes the stored region array. The selected reader bodies have no direct write, allocation or backward branch. Compiler accessibility and selected bodies do not prove arbitrary transitive purity, third-party overrides, all resource kinds or every scene.

The counter is accrued scheduled output. It is not warehouse inventory, a delivered annual total, daily production, regional income, a complete output forecast or an arrival estimate. The native candidate covers resource-backed outputs only; non-resource tradables and the separate MONEY output are outside it. `resource_id` can use the existing resource key; `region_id` can use the existing world-region index, qualified by session/observation. Do not equate a tradable key with a resource key without the explicit wrapper mapping.

The source update paths establish:

- `Shipper.count` adds the yearly-part boost scaled by elapsed game days, with stochastic rounding of fractions. The variable's name alone does not establish an annual delivered quantity or an exact accumulation period.
- The accumulator contributes to the candidate shipping amount on its configured cyclic day. Clearing follows positive load/reservation into a created shipment and is conditional on that day. This is not proof that the shipment arrives.
- Shipping can be skipped for unowned or besieged regions, regions without a faction capital, and the player's capital. Failed shipment creation does not establish delivery or clear the stored accumulator through the reviewed path.
- The owner-change callback resets accumulators. Exact update/accumulation age is not publicly established; updater timers are private. Source reset-path review is separate from testing ownership transfer or seasonal rollover.
- `daysUntilDailydelivery()` computes a cyclic day offset, using a growable's seasonal offset where applicable. It does not establish whether shipping is currently possible, when a caravan will depart, or an actual arrival ETA.

Broad boost computations, `getDelivery`, `loot`, `squeze`, shipping/building actions and `RDBoostCache.get` are excluded from the stored-reader candidate. In particular, the cache getter invokes a setter/refresh path despite its read-like name. No observer should invoke it to fill missing fields.

## Finite native evidence

The paused copied world contains 203 active regions and 42 loaded resources: 8,526 cells, including 363 naturally positive and 8,163 zero values. Thirty-two repeated read matrices remain identical. The public resource/tradable/output identity route agrees for all 42 resources, and 42 configured day offsets agree with an independent clock/season calculation.

Test-only public setters temporarily place 0, 37 and `Integer.MAX_VALUE` in one disposable counter. Each read agrees, every other counter stays unchanged, and the original value is restored in the same game callback with a complete-matrix equality check. The fixture never saves, changes ownership, runs a shipping/boost/cache action or directly invokes private game methods. Raw matrices and IDs remain private under ignored runtime/. The published report contains shape, checks, hashes and timing metadata only.

Read-and-array-allocation timing across 32 warm samples is median 0.132 ms, descriptive p95 0.474 ms and maximum 0.789 ms. The percentile uses sorted index floor(0.95 × (n−1)). These samples follow initial/control reads and are not cold-start measurements. They exclude DTO maps, encoding, disk, MCP, model latency and normal game rendering. They are not a full collector, large-world, FPS or worst-case acceptance test.

Actual MCP selections verify the existing region/resource identity rows that a future table could join. **They do not verify MCP access to these unimplemented counters.** The runner reports a zero game exit code, restores its copied-profile mod, checks copied-save integrity and pins the exact published player JAR/source used for the probe. Existing player production code and both tested ZIPs remain unchanged.

Reproduce the static check:

```sh
.venv/bin/python dev/review_regional_output_boundary.py \
  --game-dir "$SYX_GAME_DIR" --jdk-home "$SYX_JAVA_HOME"
```

Then run the finite candidate probe with the copied-save/profile setup in CONTRIBUTING.md:

```sh
.venv/bin/python dev/run_read_fixture.py --case regional-output \
  --game-dir "$SYX_GAME_DIR" --jdk-home "$SYX_JAVA_HOME" \
  --java "$SYX_GAME_JAVA" --save runtime/smoke.save
```

The runner requires the matching passing static review, shares the machine-wide fixture lock, strips provider credentials and restores only its own copied mod. On this host, the command can be wrapped in `LIBGL_ALWAYS_SOFTWARE=1 xvfb-run -a -s '-screen 0 1280x960x24'`. No provider call is made.

## Production gate still open

Implement an explicit typed regional-output table or fixed selective request with bounded region/resource/cell scans, atomic rows, null/unavailable behavior, failures/truncation diagnostics, scope/units/age definitions and existing resource/region references. Check campaign applicability in city/battle/setup, actual DTO and MCP counter parity, selected joins and complete collector/payload cost before promotion. Keep unsupported non-resource outputs, boost forecasts, private timestamps and actual shipment/arrival claims excluded. A finite native reader probe alone does not complete this gate or prove all variables/states/menus.
