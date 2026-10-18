# Regional resource-output bookkeeping

The world domain adds `/regional_output_bookkeeping/rows` and `/regional_output_bookkeeping/schedules`. These are explicit public in-process observations of campaign regional data, collected on the game after-update thread and exported as detached values. They remain campaign observations in a generated battlefield; they are not that battlefield's inventory. Initial world setup/generation makes the world domain unavailable. A failed table read returns unavailable/null rather than an empty census.

Each counter row contains `region_id`, `resource_id`, installed-help `reference_id` and `accrued_output_raw`. Each schedule row contains a resource ID/help reference and `days_until_configured_output`. Use [regional-output-query-example.json](regional-output-query-example.json) to select positive stored accruals, join region identity/ownership and configured schedules, and return the same observation's UI context. Region indexes and resource IDs must come from the same session/observation; no selected region is inferred from UI panels.

`accrued_output_raw` reads the game's resource-backed `yearlyAccumilation` counter. It is raw accrued resource items, not warehouse stock, an annual delivered total, daily production, income or a forecast. Ownership changes can reset it; exact accumulation/update age is unknown. `days_until_configured_output` is a cyclic configured day offset, with a growable's seasonal offset where applicable. Zero is a real configured offset. It is not a departure/arrival ETA, shipping permission or guaranteed delivery. Shipping can be skipped, and creation/load/reservation does not establish arrival. Source semantics and excluded boost/cache/shipping actions are in [REGIONAL_OUTPUT_BOUNDARY.md](REGIONAL_OUTPUT_BOUNDARY.md).

`describe_game_fields("world")` exposes these meanings under `field_definitions.regional_output_bookkeeping`. The original nested `/regional_output_bookkeeping/field_definitions` remains directly queryable. References identify installed resource help and its game/mod version, not a separately documented stable contract for every getter.

## Bounds and unknown values

Resource bindings/schedules scan at most 1,000 loaded resources. Output rows visit at most 1,023 active regions and attempt at most 10,000 cells, with at most 10,000 rows. Each cell is emitted atomically or omitted on failure; each failed resource binding is omitted from schedules and all its cells. Negative counter/offset observations are refused instead of clamped or replaced with zero. Non-resource tradables and MONEY outputs remain excluded.

The table reports `scanned_resources`, `resource_count_total`, `failed_resources`, `resource_limit`, `resource_truncated`; `scanned_regions`, `region_count_total`, `region_limit`, `region_truncated`; and `scanned_cells`, `cell_limit`, `row_limit`, `failed_cells`, `cell_truncated`. `scanned_regions` counts visited regions, including a partly scanned region if the cell budget ends. `truncated` combines the three cap flags. At most ten failure samples are retained. Missing cells are unknown; a reported zero is an observed zero. The cell cap produces a prefix; paging or filtering the exported table cannot recover cells beyond it. [On-demand regional reads](REGIONAL_LIVE_READS.md) provide a separate fixed active-region/resource route independent of cached rows; each live page has its own observation identity.

Paged/selective results retain ancestor scalar diagnostics for sources and joins. Counts/sums describe exported rows, and joining a missing region/schedule can remove a row from an inner join. Complete pagination does not remove collector limits or establish all game variables. Rows/schedules share one cached snapshot, session/tick/time and UI context; this is not a global worker transaction.

## Evidence and limits

[REGIONAL_OUTPUT_VALIDATION.json](REGIONAL_OUTPUT_VALIDATION.json) pins actual DTO equality for every finite copied-world cell/schedule, installed-help links, field-meaning discovery and MCP positive-filter/sort/region/schedule joins plus aggregates. It checks natural data, controlled 37 and max-int values, then restored data. These public writes belong only to an isolated test fixture and are not packaged/exposed as actions. [PLAYER_CORE_VALIDATION.json](PLAYER_CORE_VALIDATION.json) separately checks sampled city, battlefield and generation contexts on the paired build. [CURRENT_COLLECTION_COST_VALIDATION.json](CURRENT_COLLECTION_COST_VALIDATION.json) measures the full collector, snapshot bytes/encoding and offline selections with its own exact source/JAR pins.

The original candidate-reader [report](REGIONAL_OUTPUT_READER_VALIDATION.json) retains its earlier JAR/source hashes and getter/array-only timings; those are not full new-collector timings. Source review is shipped-source/binary verification, not an official stable API guarantee. Natural seasonal rollover, actual ownership transfer, shipment/arrival behavior, non-resource output, native cap/fault injection and large-world/large-city worst-case performance remain unvalidated. Exact selected-room/region identity, tooltip text and immediate menu-unload gaps remain open.

Reproduce the new feature fixture with the copied setup and licensed game arguments in CONTRIBUTING.md:

```sh
.venv/bin/python dev/run_read_fixture.py --case regional-output-export \
  --game-dir "$SYX_GAME_DIR" --jdk-home "$SYX_JAVA_HOME" \
  --java "$SYX_GAME_JAVA" --save runtime/smoke.save
```

Use `--candidate-dir` and `--validation` for an unpublished matching candidate. The runner locks the shared fixture, strips provider credentials, restores its copied mod and checks copied-save integrity. It makes no provider requests and never drives native input, captures screenshots or reads process memory.
