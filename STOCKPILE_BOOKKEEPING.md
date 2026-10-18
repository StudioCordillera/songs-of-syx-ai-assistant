# City stockpile bookkeeping

The player exposes a bounded resource table at `resources /stockpile_bookkeeping/rows`. It separates assigned crates, stored items, assigned item capacity, reserved stored goods and reserved incoming capacity. This extends the existing `resources /stockpiles` totals; it does not replace their established meanings. All five getters are explicit public in-process reads on the game after-update thread. The shipped implementation is source/binary verified; no separately documented stable game API contract is claimed.

## Fields and identity

| Field | Meaning / units |
| --- | --- |
| `resource_id` | Installed resource key; joins `resources.stockpiles[].id` and matching production/trade keys in the same observation. |
| `reference_id` | Installed `resource:<key>` help reference. The help describes the resource, not every reservation mechanic. |
| `assigned_crates` | Crates assigned to this resource; not unassigned crates or item capacity. |
| `stored_raw` | Resource items physically recorded in the warehouse tally, including reserved stored items. |
| `capacity_raw` | Assigned capacity for this resource, in resource items; not currently free space or physical floor area. |
| `reserved_stored_raw` | Stored resource items reserved for use; distinct from incoming capacity reservations. |
| `reserved_incoming_raw` | Reserved incoming capacity in resource items; not goods already present or guaranteed deliveries. |

Each row uses the resource's validated installed index and five `StockpileTally.TallyData.total(int)` reads. The observer never obtains a crate handle or invokes reservation, refresh, report, deposit or withdrawal operations. [The static boundary review](STOCKPILE_BOUNDARY.md) explains source anchors, direct-reader bytecode and the excluded shared scratch crate object.

The older `owned` field has broader logistics and player-trade scope. It includes additional locations/incoming goods and subtracts trade promises, so it must not be equated with warehouse stock. The old `stockpile_stored`/`stockpile_capacity` values correspond to the new stored/capacity counters on the tested city, but their existing scene scope is retained. Inspect the new table's availability before comparing it to those legacy rows.

Zero capacity remains **zero**. No fullness ratio or helper's special zero-denominator default is exported. If deriving a ratio, filter/handle zero capacity explicitly and specify whether reserved goods participate. Subtracting a reservation counter does not establish general availability, worker access, route feasibility, future delivery or consumption. Do not combine heterogeneous resource capacities into a physical warehouse-fullness claim.

## Availability, bounds and consistency

The new table is available only with an instantiated completed campaign city. It is unavailable in battlefield/setup contexts even if legacy resource fields still exist. The table then has `coverage=unavailable` and `rows=null`; MCP paged reads return unavailable/null totals and selective counts refuse it. It never becomes an empty city inventory.

At most 1,000 resources are scanned and 1,000 rows emitted. `resource_count_total`, `scanned_resources`, `resource_limit`, `row_limit`, `truncated`, `failed_resources` and at most ten `failure_samples` qualify results. A resource's five-counter row is emitted atomically or omitted on error. Omitted/truncated/failed resources are unknown, not zero. Collection diagnostics accompany selective sources/joins and paging; aggregates count exported rows only. A failure initializing the whole resource domain remains unavailable through the existing domain boundary.

Rows and joins in one cached observation share session, snapshot, tick, timestamp and requested UI context. They are stored bookkeeping sampled at that time, not a global worker-thread transaction or an exact-age guarantee. They are not per-room/crate identities, the UI-selected warehouse, ground inventory or all goods in transit. Room activation does not imply that stored counters vanish: a separate copied-room lifecycle check retains tallies immediately after deactivation, without establishing behavior over time or removal.

## Query example

[stockpile-query-example.json](stockpile-query-example.json) selects resources with positive reserved stored items, projects both reservation counters separately, joins the legacy broader `owned` quantity, sorts by reserved stored items and returns five rows with same-observation UI context. Send its contents as `select_game_state(spec=...)`. For a specific player question, narrow fields and predicates further; inspect `game_status`, field descriptions, scene and diagnostics first. `get_game_api_support("city_stockpile_bookkeeping")` provides discoverable scope/evidence/limits.

## Evidence and limits

[STOCKPILE_BOOKKEEPING_VALIDATION.json](STOCKPILE_BOOKKEEPING_VALIDATION.json) pins the current JAR/source and copied-city checks. Forty-two resources in one warehouse match all five direct counters. The native fixture observed positive assigned capacity for nine resources, stored goods for five, incoming-capacity reservations for one and stored-goods reservations for two. Thirty-three resources had zero assigned capacity. Actual MCP checks cover the authored reservation query/join/sort, a zero-capacity count, field discovery and original UI context over the retained real observation. Per-room arrays remain fixture-only; overload/sum agreement is not an independent physical-crate audit.

[PLAYER_CORE_VALIDATION.json](PLAYER_CORE_VALIDATION.json) records current finite scene checks including unavailable battle/setup rows and refused MCP counts. [USER_TEST_VALIDATION.json](USER_TEST_VALIDATION.json) pins the simple Pro player/provider/distribution checks. Earlier [STOCKPILE_READER_VALIDATION.json](STOCKPILE_READER_VALIDATION.json) belongs to the pre-mapping JAR; its dates/hashes are preserved. Synthetic regression cases check the authored query, distinct meanings, inherited truncation/failures and unavailable counts. They are separate from runtime cap/fault injection, which remains unexecuted.

Large-city costs, actual cap/fault execution, per-room production exposure, removal/inactive-time simulation, exact tally age, reservation completion and complete logistics coverage remain open. This adds observed counters for better questions; it does not prove why a particular delivery is stuck or prescribe storage policy.
