# On-demand regional resource-output reads

`query_live_regional_outputs` reads explicit active-region IDs and loaded resource keys directly in `GAME.addAfterUpdate`. It does not use the cached `/regional_output_bookkeeping/rows` as its data source. It can therefore serve requested cells omitted from a partial export. The existing cached table remains useful for same-snapshot joins/aggregates; [REGIONAL_OUTPUTS.md](REGIONAL_OUTPUTS.md) describes that separate route.

Example request:

```json
{
  "region_ids": [0, 17],
  "resource_ids": ["<exact loaded resource key>"],
  "fields": ["accrued_output_raw", "days_until_configured_output", "reference_id", "faction_id"],
  "min_accrued_output": 1,
  "cursor": 0,
  "limit": 25
}
```

Discover actual region IDs from world `/regions` and resource keys from the installed resource catalog or resources `/stockpiles`; the example IDs/key are placeholders, not a claim that they exist in a particular game. Region IDs must be active in the current campaign. An unknown/inactive region or unknown resource fails the request rather than returning zero. IDs are session scoped; use optional `expected_session_id` to require a particular session.

## Fixed selection and paging contract

Select 1–100 unique region IDs (0–1022) and 1–100 unique resource keys (1–100 Unicode code points). All supplied predicates combine with AND: inclusive `min_accrued_output`, inclusive `max_accrued_output`, and optional campaign owner `faction_id`. The four optional projection names are fixed. Bindings use the public active-region registry, matching the cached table rather than assuming every allocated slot is active. That getter may rebuild its ordinary membership cache; no explicit boost/RDBoostCache refresh or gameplay action is invoked. Region/resource IDs always appear in each row. Filtering can read a value without projecting it; this is not an arbitrary Java member/query interface.

The cursor is the zero-based position in the requested **ordered** `region_ids × resource_ids` matrix, resources varying fastest. It is not a global world slot or matching-row count. Continue with identical ordered IDs, fields and predicates and the returned `next_cursor`; follow it even after an empty filtered page. Requesting the matrix end returns a successful empty remainder. Change the selection only by starting a new query.

Each request scans at most 4,096 cells and returns at most 100 whole rows. Binding scans are separately limited to 1,023 active-region entries and 1,000 loaded resources. There is an 8-KiB framed request, 64-KiB response/tool-text limit and eight-second client deadline. Large UTF-8 key batches can exceed the byte budget even when their item counts are valid. Unknown/duplicate fields, malformed encoding/UUIDs, duplicate IDs, invalid cursors/ranges and oversized requests are refused.

Cell read/projection failures omit the entire cell and increment `cell_errors`; absence/count is unknown for failed cells. No failed value becomes zero. Registry ambiguity or missing requested bindings makes the whole request unavailable. `scanned_cells` and `next_cursor` describe attempted matrix positions; the reply also reports the separate binding scan counts. Client validation checks scope, identities, matrix order/cursors, projection/value bounds and byte limits. The transport uses the existing POSIX request lock shared with entity/tile reads, with a separate fixed regional mailbox; it does not share caller-controlled paths.

## Meaning, observation identity and lifecycle

`accrued_output_raw` is the stored resource-backed accrual, not city inventory, an annual delivered total, income or a production forecast. `days_until_configured_output` is a cyclic configured offset, not actual departure/arrival ETA or shipping permission. `faction_id` is the observed campaign owner or null for no owner; it is not the UI-selected faction/region. Exact accumulator age and non-resource/MONEY output remain unexposed. Source semantics and excluded boost/cache/ship actions are in [REGIONAL_OUTPUT_BOUNDARY.md](REGIONAL_OUTPUT_BOUNDARY.md).

Each reply carries its own `request_id`, session, game version, tick, capture time, campaign scope, scene and UI context from that callback. It has **no cached snapshot ID**. Pages are separate live observations; neither a retained regional selection nor a global worker transaction is implemented. Do not silently merge pages' times or join them to old cached world/city rows. A modal or hidden UI can obscure underlying panels; exact selected-region identity remains unestablished.

Use the paired installed mod/helper build and restart after installation. An older mod may not poll this new channel and can time out; the client does not substitute cached rows. A completed campaign world is required. City and generated battlefield views can read campaign counters; initial generation is unavailable. Session/version changes, stale/demo/disconnected snapshots, expired requests and missing game callbacks fail explicitly. Standalone menu identity and instant unload notification are still unestablished; the existing freshness limitation remains, and an unanswered live request can time out before the cached observation expires.

## Evidence and remaining gaps

[REGIONAL_LIVE_VALIDATION.json](REGIONAL_LIVE_VALIDATION.json) pins the finite native getter/MCP/projection/predicate/paging/concurrency and scene checks. The copied-world fixture holds a test-only max-int counter at the final cell of a 4,200-cell selection, restores it before scene follow-up and never saves. It checks 42 ordinary pages, an empty 4,096-cell filtered page followed by the matching last cell, exact projections, combined predicates, unknown/inactive refusal and three concurrent callers.

A separate **test-only authored partial-cache view** clones real snapshots, keeps their real timestamps/session/ticks, exposes only the first 100 cached rows and marks truncation. Actual MCP selection must show the target missing from that cache, while the live tool retrieves it from the real game callback. It changes no game data or normal exporter files. This proves independence from cached row contents; it is not an actual production 10,000-cell cap fixture, a larger generated world or a refreshed/live replacement snapshot.

The pure Java codec accepts the valid frame/end cursor and rejects 19 malformed/unsupported variants without game bootstrap. Offline transport tests reject mismatched/tampered responses and demonstrate observed zeros despite missing cached rows. Current player/core reports pin the paired build; earlier regional table/candidate reports keep their own whole-build scopes.

Public getter implementations are verified against shipped source/binaries and compiler declarations, not separate official stable contracts. Native registry/cell faults, an actual larger-world export-cap case, all mods/menu combinations, retained regional captures and large-world latency/FPS remain open. The live route does not establish every game variable or every lifecycle/menu state.

Reproduce with the isolated copied setup in CONTRIBUTING.md:

```sh
.venv/bin/python dev/run_read_fixture.py --case regional-live \
  --game-dir "$SYX_GAME_DIR" --jdk-home "$SYX_JAVA_HOME" \
  --java "$SYX_GAME_JAVA" --save runtime/smoke.save
```

The runner uses the shared fixture lock, restores its copied mod and checks copied-save integrity. It makes no provider requests. Its public in-process test controls/scene actions are never packaged or exposed through MCP. No private reflection, process memory, screenshot or native input/automation is used.
