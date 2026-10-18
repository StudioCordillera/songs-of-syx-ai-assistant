# Stored room workforce factors — game 0.71.44

The `employment /rooms` table retains its existing workforce counts and shared room-instance key and adds `work_factors`. These are source-verified public readers, not separately documented stable mod contracts. All reads run on the game update thread and return detached values.

| Field | Public getter | Meaning / limit |
| --- | --- | --- |
| efficiency_stored_raw | RoomEmploymentIns.efficiency() | Stored work-report factor; can be smoothed, defaulted or reset. Not instantaneous idle time or an optimal staffing estimate. |
| proximity_stored_raw | RoomEmploymentIns.proximity() | Stored travel-related factor, not distance, elapsed minutes or a current path test. |
| fetch_proximity_stored_raw | RoomEmploymentIns.fetchProximity() | Stored fetch-related factor. Its presence does not establish whether the combined factor uses it. |
| fetch_factor_applies | RoomEmploymentSimple.countInput() | Blueprint flag selecting the conditional fetch factor. Does not establish input availability or active fetching. |
| combined_efficiency_raw | RoomEmploymentIns.totEfficiency() | Efficiency × proximity, additionally × fetch proximity when countInput is true. Not the complete production modifier stack. |

The factor values are dimensionless. The observer preserves finite raw values without clamping them into a percentage range; nonfinite values become null. Exact sample age is not returned by these mapped getters. Inactive or unstaffed rooms can retain default/reset values, including apparently favourable ones. Combine them with active/staffing flags, installed help and same-observation recipe/resource records. Do not equate these factors with resource throughput, inputs, complete room/individual/race/technology bonuses or guaranteed future work duration. Recorded production buckets have separate age/carry limits in PRODUCTION_PERIODS.md.

Employment now scans at most 10,000 instantiated rooms and emits at most 2,000 employing-room rows. Failed rows are omitted and counted, with ten bounded diagnostic samples; skipped non-employing rooms are not a claim of zero workforce. Root truncation, failures and limits follow `/rooms` through MCP `collection_diagnostics`, including joins and aggregates. Completing pagination does not establish a full city census.

Use workforce-query-example.json for staffed-room factor selection and a recorded-output left join. The nullable staffing object preserves unmatched production rooms. Room IDs are load/scene scoped and can be reused; join only in the same observation. Setup data is unavailable without an instantiated settlement. A battlefield's scene-local employing rooms are not campaign workforce.

The adapter calls no work/fetch/travel reporting, employee enumeration, staffing setter, reset, update or production-rate utility. Static source/binary review is scoped evidence about the five mapped readers; it does not establish general purity or a complete production model. WORKFORCE_CONTRACT_REVIEW.json pins the static review; WORKFORCE_VALIDATION.json and PLAYER_CORE_VALIDATION.json pin the finite copied-game checks. Larger-city costs, employment cap/fault branches and complete production modifiers remain unvalidated.
