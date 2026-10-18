# Asking for exactly the game data you need

Start with `game_status`. It reports version, session, snapshot ID, freshness and coverage.
Missing/unavailable data does not mean zero. All current domain collectors are **partial**.

## Fast structured queries

`describe_game_fields(domain)` lists observed field paths and types without returning every row.
`query_game_state(domain, pointer, offset, limit)` reads a small subtree.
`select_game_state(spec)` filters, joins and summarizes data locally before returning it to the model.
All queries in a batch use the same cached snapshot, refreshed approximately every two seconds.
Set `expected_snapshot_id` to reject a changed snapshot. A version/session change requires rediscovery.

A query source is `{"domain":"resources","path":"/stockpiles"}`. Discover actual fields first.
For example, to return the five smallest stockpiles:

```json
{"queries":[{"name":"lowest_stocks","source":{"domain":"resources","path":"/stockpiles"},"select":{"resource":{"field":"/id"},"stored":{"field":"/stockpile_stored"}},"sort":[{"field":"/stored","direction":"asc"}],"limit":5}]}
```

Expressions use `{"field":"/path"}`, `{"literal":value}`, scalar constants, or one operator:
`eq`, `ne`, `lt`, `lte`, `gt`, `gte`, `in`, `contains`, `add`, `subtract`, `multiply`, `divide`
with two operands; `and`/`or` with 1–20 expressions; `not`/`is_null` with one expression.
Division by zero and arithmetic with null return null. Missing fields produce errors.

`where` is an expression. `select` maps output names to expressions.
`joins` is a list of `{source,left_key,right_key,as,kind}` with JSON pointer keys and `inner` or `left` kind.
Only join fields with established shared identifiers; similarly named labels do not establish a relationship.
`group_by` maps output names to expressions; `aggregates` maps names to `{op,value}`.
Aggregate operators are `count` (no value needed), `sum`, `avg`, `min`, `max`.
Numeric aggregates ignore null; an empty numeric aggregate is null, while count is zero.
Sort applies after projection/grouping; nulls sort last. `offset`/`limit` paginate results.

Limits: 10 queries/batch, 3 joins/query, 10,000 intermediate rows, 200,000 work units,
32 KiB specification, 64 KiB response, 100 returned rows/query. Narrow the request on a limit error.
No SQL, expressions as code, arbitrary methods or state writes are accepted.

## Public API coverage

Only fields mapped from direct public game APIs are exported. There is no arbitrary/private field exploration.
Discover the exported shape with `describe_game_fields`; use the structured query language for complex selections.
All current domains are partial. See API_BOUNDARY.md for source provenance and documentation limitations.
Use `get_game_ui_context` for active view, known overlays and selected subject identity. Open room blueprint context is available; exact instance, management tab, tooltip text and complete panel ordering are unavailable. Inspect `get_game_api_support` for evidence and limits before assuming a query exists.

## References and advice

1. `search_game_references` searches resource, technology, stat, room and research-currency descriptions loaded by this exact game.
   Cite its reference ID and origin. Active mods can change this text; these are installed-data references.
2. `search_guidance` searches reviewed excerpts with direct URLs, authors, authority, retrieval time,
   version notes and compatibility labels. Results rank by whole-word relevance, with version compatibility and official/developer authority breaking ties. An authority filter restricts the search when needed. A retrieval score is not factual confidence.
3. Combine observed state with supported mechanics and explain the inference. An old forum answer or a
   version-family match does not prove applicability to the current patch. Report gaps instead of inventing evidence.

The initial external corpus is deliberately small. It is not an exhaustive or automatically updated knowledge base.

## UI-aware selections and scope

`{"context":"/selected_subject/entity_id"}` reads a UI context field from the same snapshot. For example:

```json
{"include_ui_context":true,"queries":[{"name":"selected_person","source":{"domain":"entities","path":"/items"},"where":{"eq":[{"field":"/id"},{"context":"/selected_subject/entity_id"}]},"select":{"id":{"field":"/id"}},"limit":1}]}
```

Discover the actual entity path before querying. A missing context field is an error; an empty result in `/items` does not prove the person is absent from the game because that list is bounded. Use the dedicated `/selected_subject` object for the selected person. Modal overlays may obscure the underlying selection.

Query results include coverage and scope for each source and join, plus `mixed_scopes`. Inspect `game_status.scene` and these scopes before comparing city, battlefield and campaign values. Resources also provide `field_definitions`: `owned` mixes scene logistics and player trade promises, while `stockpile_stored` describes the instantiated settlement. During world preparation, unavailable domains contain null, not fabricated zero values.

## Selected person's individual statistics

The entities domain's `/selected_subject/stats` path contains the selected person's named public individual statistics. Query it directly, independently of `/items`:

```json
{"include_ui_context":true,"queries":[{"source":{"domain":"entities","path":"/selected_subject/stats"},"where":{"eq":[{"field":"/coverage"},"partial"]},"select":{"stat":{"field":"/key"},"value":{"field":"/value"},"reference":{"field":"/reference_id"}},"limit":10}]}
```

Pass a returned reference ID directly to `search_game_references` to retrieve the installed description. Raw values and getter bounds do not establish semantic units, satisfaction effects or complete personal history. A null selected subject makes this query invalid; inspect context first. Selection may remain behind an overlay.

## On-demand entities across the instantiated scene — 0.7.0

Call `game_query_help` for the complete `on_demand_entities` schema. `query_live_entities` asks the mod to read chosen values on the update thread. It can reach entities outside the prefix snapshot.

```json
{"entity_ids":[12345],"fields":["id","race_id","class_id","humanoid_type_id","tile_x","tile_y","stats"],"stat_ids":[0],"limit":1}
```

Replace these example IDs with observed values. Installed stat search results advertise `stat_id` and `individual_getter_available`; use named individual getters only. Projected stat values provide bounds and a reference ID. Raw integer units are not established merely by reading these values.

Filters combine with AND: `entity_ids`, `race_id`, `class_id`, `humanoid_type_id`, `tile_bounds: [x1,y1,x2,y2]` (upper bounds excluded), `workplace_room_id` (recorded humanoid assignment), and up to four `stat_filters: [{stat_id,op,value}]` using `eq/ne/lt/lte/gt/gte`. Missing individual getters or unknown stat IDs fail explicitly. `predicate_errors` counts entities whose predicate getter failed; nonzero errors mean matching absence/count is unknown.

Explicit IDs use the game's public ID lookup. Without IDs, each request scans up to `scan_limit` scene-array slots, starting at `cursor`, and returns at most `limit` matches. Follow `next_cursor` until null, including after an empty page. With IDs, cursor refers to the ordered requested-ID list; `cursor_kind` distinguishes it from scene slots. Do not substitute the number of matching rows as the next cursor.

Use `expected_session_id` to reject a game replacement. Each response has its own request ID, capture time, tick, scene and UI context; it is not the cached snapshot and cannot be joined as though captured at that snapshot's tick. Cursor pages are separate observations over a changing scene. Large-city performance remains unvalidated. Use the retained capture tools below for consistent bounded entity paging. The tested client transport requires POSIX.

## Bounded popup/section content — 0.8.0

`get_game_ui_context` returns `known_content` from the same cached snapshot as other state. Its roots name the primary popup, secondary popup and section. Nodes carry local IDs/parents, widget kind, visibility flags, internal bounds, mapped control flags and readable `GTextR` text. Opaque content includes a reason; repeated references point to an earlier node. IDs expire with the observation and cannot be used to invoke controls.

Check `truncated`, per-label `text_truncated`, `read_error` and limits before answering a question about displayed content. A blank truncated label is not evidence of blank game text. Flags and known ancestry do not prove final visibility or topmost context. Button/sprite/private-wrapper text can remain opaque even when another label in the same panel is readable. Tooltip text and private input values remain unavailable. Do not assume the user's “this” refers to one of these roots when multiple overlays or background selections exist.

## Scene division data and unknown input consumers — 0.9.0

Discover `military.scene_armies` before querying. Each side's `divisions` list contains scene-local IDs, name, present/configured men, race, raw morale and the engine's published engagement flag. For example, after confirming the player army is at index zero:

```json
{"queries":[{"source":{"domain":"military","path":"/scene_armies/0/divisions"},"where":{"and":[{"gt":[{"field":"/present_men"},0]},{"eq":[{"field":"/engine_engagement_flag"},true]}]},"select":{"division":{"field":"/name"},"men":{"field":"/present_men"},"morale_raw":{"field":"/morale_raw"}},"limit":10}]}
```

This selects rows reporting a published engagement flag, not proof of instantaneous fighting. Worker buffers may lag or remain stale during a conclusion; brief engagement can be missed by periodic snapshots. Morale has no established percentage/range here, and the configured/present difference is not a general casualty count. These armies belong to the current instantiated scene, not every world army. Treat division IDs as observation/scene scoped.

`input_capture.global_hover_consumed` and `active_view_hover_consumed` report the latest public manager flags. `global_hover_consumed_without_known_overlay_flag` can highlight input consumption while all mapped overlay flags are false. It does not identify a private battle-result screen or any other dialog, and its absence does not prove that an unmapped overlay is absent. Exact battle-conclusion content stays unavailable.

## Person relationship projection (0.10.0)

```json
{"entity_ids":[123],"fields":["id","relationships"],"limit":1}
```

Pass this as `spec` to `query_live_entities` after discovering the current session and entity IDs. Each of `workplace`, `profession`, `home_assignment` and `division` returns `{available,data}`. Available with null data means no recorded assignment; unavailable means the getter failed. Recorded profession is separate from current workplace. Home coordinates describe an assignment, not occupancy/current position. Workplace anchors are room anchor tiles, not the person's position or UI selection. Division IDs can be matched with `military/scene_armies` in the same scene, but cross-response reads are separate observations; IDs are not persistent across regeneration. Use paired mod/MCP builds; older mods reject the new projection explicitly. Request fewer rows if a relationship projection exceeds the existing 64 KiB response bound.

The selected-person snapshot also includes `entities/selected_subject/relationships`, so `select_game_state` can inspect these fields with the same snapshot/context as other data.

## Retained entity pages — 0.11.0

For a complex selection that must remain unchanged across pages, pass a specification to `capture_live_entities`:

```json
{"fields":["id","race_id","tile_x","tile_y","relationships"],"max_rows":2000,"scan_limit":100000}
```

Use the same finite predicates/stat IDs as live entity queries. ID projection is required; cursor is zero. Creation returns metadata only, including `capture_id`, original tick/time/session and row count. Then call `read_entity_capture(capture_id, offset=0, limit=20, include_ui_context=true)` and follow `next_offset` until null. Here offset indexes retained rows, not live scene-array slots. Use the original capture provenance when citing data. `captured_ui_context` belongs to that observation; `current_state` separately describes the latest exported status. Other live queries or captures are separate observations.

All matching rows must fit 2,000 rows, 100,000 scanned slots, 4,000 selected stat cells and a 2 MiB local payload. Row/scan/predicate/byte failures retain nothing; narrow the selection on failure. Each server retains three captures for 120 seconds, evicting the oldest when full. Tokens are server-local and do not survive restart. Reads require a fresh loaded observation with the same session/version; expiration, eviction and session changes fail explicitly. Pages allow up to 100 rows and 64 KiB of MCP tool text; reduce limit or omit UI context for wide rows. Protocol framing can add bytes.

Capture reads page copied values and do not reread game objects, freeze/pause the game or synchronize background simulation/battle workers. Full game-state/schema, large-city performance and permanent entity IDs remain unestablished. Install paired updated mod/MCP builds. `game_query_help.retained_entities` provides the exact schema and limits.

## Spatial selections — 0.12.0

Use game_query_help.on_demand_tiles for the exact schema and structured field definitions. `query_live_tiles` accepts an explicit rectangle `[x1,y1,x2,y2]` with upper bounds excluded, fixed field groups and AND predicates:

```json
{"tile_bounds":[100,100,124,124],"fields":["terrain","room","path"],"has_room":false,"throne_component_reachable":true,"limit":20,"scan_limit":4096}
```

Choose coordinates from observed data and check map dimensions. Optional exact keys are terrain_id, floor_id, room_blueprint_id and mineral_resource_id. An unmatched key can return no matches; it is not an unknown-API error. Follow next_cursor even after empty pages. The cursor is a row-major offset inside this same rectangle, not a global tile index or match count. Keep bounds/filters unchanged while traversing. Each page samples the current scene separately; entity capture tokens do not retain tiles.

At most 4,096 tiles are scanned and 100 rows returned per request. Input is capped at 8 KiB; local response and actual MCP tool text are each capped at 64 KiB. Reduce limit/fields on size errors. Request deadline is eight seconds and the POSIX request lock is shared with entity queries. Use expected_session_id; cite the returned session/tick/time and scene/UI context. No instantiated scene gives an explicit error; initial world setup is not a city.

Every row includes tile_x/tile_y, plus requested groups as `{available,data}`. True/null means no floor/room/deposit reported; false means a getter failure. Nonzero predicate_errors prevents treating matching absence/count as established. Room data belongs to the supplied coordinate, not the UI-selected room. map_record_id may be shared by singleton rooms; instance_room_id exists only for RoomInstance. Anchors and singleton bounding area are engine values, not guaranteed geometric center or usable area. IDs expire with scene/session changes.

Terrain roof/wall flags and floor road/degradation values are engine observations. Mineral amount_raw is a stored 6-bit value, amount_fraction is amount_raw/63, and richness_flag_raw is a stored one-bit flag; retrieve the associated installed resource description using reference_id. These values do not establish extraction yield or lifetime. Path factors and throne-component reachability include adjacent components and do not establish a route for a particular agent, final visibility or construction suitability. Full tile state, fertility, world-map state, global worker consistency and large-city performance remain unestablished.

## Research prerequisites and currency allocation — development checkpoint

The research domain now has four related arrays: `technologies`, `requirements`, `costs` and `currencies`. `describe_game_fields("research")` returns their available field meanings. `requirements` is the game's expanded prerequisite closure, including indirect dependencies; it is not only the visible tree edges.

For up to five unmet prerequisite relationships, with readable prerequisite names:

```json
{"queries":[{"source":{"domain":"research","path":"/requirements"},"joins":[{"source":{"domain":"research","path":"/technologies"},"left_key":"/required_technology_id","right_key":"/id","as":"required","kind":"inner"}],"where":{"eq":[{"field":"/met"},false]},"select":{"technology":{"field":"/technology_id"},"requires":{"field":"/required/name"},"missing_levels":{"subtract":[{"field":"/required_level"},{"field":"/current_level"}]}},"limit":5}]}
```

`technology_requirements_met` checks technology levels only. It does not prove every non-technology unlock condition passes or that the player can afford the research. Cost rows join technology `id` through `technology_id` and currency `id` through `currency_id`. `next_level_cost` excludes missing prerequisites and becomes null at maximum level. Currency `available` is `total - frozen - allocated` and may be negative. The stored `penalty_raw` is not a forecast or a recalculated per-technology penalty. Technology `reference_id` links to installed help via `search_game_references`.

The [coverage inventory](DATA_COVERAGE.md) lists current routes and the next typed mappings. It is not a full game-variable catalog.

## Join a selected worker to employment

Employment rows now include `room_id`, the public room-instance index also used by a person's recorded workplace. The existing composite `id` is retained. Join these numeric `room_id` values only within the same observation; they may be reused when a room is replaced and are not permanent campaign identifiers.

After checking that `/selected_subject` and its available, non-null workplace exist:

```json
{"include_ui_context":true,"queries":[{"source":{"domain":"entities","path":"/selected_subject"},"joins":[{"source":{"domain":"employment","path":"/rooms"},"left_key":"/relationships/workplace/data/room_id","right_key":"/room_id","as":"work","kind":"inner"}],"select":{"person":{"field":"/entity_id"},"workplace":{"field":"/work/name"},"employed":{"field":"/work/employed"},"target":{"field":"/work/target"}},"limit":1}]}
```

This observes a recorded assignment. It does not prove the person is currently working, that this room is selected in the UI, or that the room meets production targets. A missing join is not evidence of unemployment if either source lacks coverage.


## Reference retrieval checks

The reviewed starter corpus has nine original summaries. Run `PYTHONPATH="$PWD" .venv/bin/python dev/verify_guidance.py --state-dir runtime/guidance-check` to exercise eleven authored questions through actual MCP without a game or model call. The result records citation IDs/URLs and compatibility labels, including an unrelated no-match query and current-version community logistics queries. Search output reports total matches and truncation while retaining complete citation records within 64 KiB. This is lexical retrieval, so rephrase with relevant game terms when appropriate; no-result does not prove a mechanic does not exist.

## Per-room current recipes and recorded quantities — development checkpoint

Production now contains two scopes: `/resources` is the campaign/player resource ledger, while `/room_data/flows` is a bounded observation of the instantiated scene's current producer-room recipes. Inspect `/room_data/coverage`, `/room_data/truncated` and `/room_data/failed_rooms` before treating missing rows as meaningful. The observer scans at most 10,000 rooms and returns at most 2,000 flow rows, stopping before splitting a room's recipe. It records up to ten failure samples. Non-producer rooms are outside this mapping, not evidence of zero output.

A flow has an observation-local `room_id`, runtime/load-scoped `industry_id` and `recipe_index`, a `direction` (`input` or `output`), and a `resource_id` with an installed-help `reference_id`. `base_rate_raw` is the configured recipe coefficient before modifiers. It is not realized output or a forecast. `day_accumulator_raw` can include fractional carry across day rollover; `previous_day_units`, `year_units` and `previous_year_units` are stored game ledger values. The observer does not refresh buckets. An inactive or paused room can retain an older bucket; do not assume every stored bucket is aligned with the global clock.

For five output rows with current employment and warehouse storage in the same observation:

```json
{"include_ui_context":true,"queries":[{"source":{"domain":"production","path":"/room_data/flows"},"joins":[{"source":{"domain":"employment","path":"/rooms"},"left_key":"/room_id","right_key":"/room_id","as":"work","kind":"inner"},{"source":{"domain":"resources","path":"/stockpiles"},"left_key":"/resource_id","right_key":"/id","as":"stock","kind":"inner"}],"where":{"eq":[{"field":"/direction"},"output"]},"select":{"room":{"field":"/work/name"},"resource":{"field":"/resource_id"},"recorded_previous_day":{"field":"/previous_day_units"},"employed":{"field":"/work/employed"},"warehouse_stored":{"field":"/stock/stockpile_stored"}},"limit":5}]}
```

`source_scope` reports mixed scene production/campaign ledger for the production domain. Inspect its field definitions and the joined sources: warehouse storage is not the amount inside a producer's own storage, and a worker count does not establish actual time worked or causality. An inner join omits records absent from the joined mapping; use a left join when that distinction matters and handle null explicitly.


## Room and research-currency help links

Employment `reference_id`, production `room_reference_id`, research currency `reference_id` and supported `ui_context.open_room_blueprints[].reference_id` link directly to the installed help catalog. Pass the returned ID to `search_game_references`, optionally restricting `category` to `room` or `research_currency`. IDs beginning `room:` identify blueprint descriptions; they do not resolve an exact selected instance or hidden tooltip. A null room reference means no mapped description was established for that blueprint type.

Descriptions come from this installation's public data and can be changed by mods or translation. Empty text is not evidence that a mechanic does not exist. Keep the returned game-version/mod provenance with the citation. Reference lookup is bounded to 64 KiB and reports truncation without cutting individual citation records. The latest copied-city run verifies 111 room and three currency titles/descriptions against public-getter hashes, plus the eleven sampled UI/lifecycle phases in INSTALLED_HELP_VALIDATION.json.

## Reproducible selective-query examples and timing

`selective-query-examples.json` batches five bounded selections: the five least positive warehouse stocks, five recorded output rows joined to current workforce/storage, output buckets grouped by resource, the largest positive populations in player-owned regions, and incoming city goods joined to storage and configured buy caps. `dev/benchmark_selective_queries.py` checks each result against independent filter/join/group calculations on a preserved real copied-city snapshot and measures the local query engine without refreshing its timestamp. SELECTIVE_QUERY_VALIDATION.json records exact hashes, row counts and byte/timing measurements.

These are examples of reducing returned data, not a live performance guarantee. Timings exclude collection, file parsing, MCP transport and inference; the full snapshot also includes installed references. The grouped stored buckets are not guaranteed calendar-aligned daily production. A live MCP call still requires a fresh loaded game and proper coverage, even though this offline developer benchmark can inspect preserved evidence.

See PRODUCTION_PERIODS.md for the source/binary review of stored production periods and the remaining exact-age limitation.

## Campaign region population

The world domain now exposes `regions[].population_total`, `population_coverage`, `player_owned`, `capital` and `area_world_tiles`. `population_by_race` is a flat table of `{region_id,race_id,population}` for the game's playable regional race counters, including zeros. Discover meanings with `describe_game_fields("world")` before using them. These are stored **regional** inhabitants; they are not the instantiated settlement census or a forecast. Population update timing can differ from the current observation time. A shared `race_id` establishes race identity, not interchangeable population scopes.

For the five largest positive race populations in player-owned regions, with region names:

```json
{"include_ui_context":true,"queries":[{"source":{"domain":"world","path":"/population_by_race"},"joins":[{"source":{"domain":"world","path":"/regions"},"left_key":"/region_id","right_key":"/id","as":"region","kind":"inner"}],"where":{"and":[{"gt":[{"field":"/population"},0]},{"eq":[{"field":"/region/player_owned"},true]}]},"select":{"region":{"field":"/region/name"},"race":{"field":"/race_id"},"regional_inhabitants":{"field":"/population"}},"sort":[{"field":"/regional_inhabitants","direction":"desc"}],"limit":5}]}
```

Inspect `region_truncated`, `population_truncated`, `population_failed_regions` and each region's `population_coverage`. The region cap is 1,023; demographic reads accept at most 64 race entries per region and 10,000 rows in total, without splitting a region across that row cap. On a demographic getter failure or cap skip, its total is null and no partial race batch is emitted. This is not zero population. `capital` is a realm relationship, not a selected-region UI flag. `area_world_tiles` is neither settlement tiles nor farmland.

WORLD_VALIDATION.json checks public-getter agreement and actual MCP paging/joining for a copied campaign; cap-exceeding mods and large-world performance remain untested.

## City resource trade stages and configured limits

Inspect `describe_game_fields("trade")` and `/settlement_pipeline/coverage`. The campaign daily ledger remains at `/resources`; city stage counters and policies have a distinct scope and are unavailable on battlefields. See TRADE_PIPELINE.md for precise public getter meanings, caps and remaining gaps.

For up to five incoming resource/reason rows joined to warehouse storage and the configured buy cap:

```json
{"include_ui_context":true,"queries":[{"source":{"domain":"trade","path":"/settlement_pipeline/flows"},"where":{"gt":[{"field":"/inbound_total_units"},0]},"joins":[{"source":{"domain":"resources","path":"/stockpiles"},"left_key":"/resource_id","right_key":"/id","as":"stock","kind":"inner"},{"source":{"domain":"trade","path":"/settlement_pipeline/policies"},"left_key":"/resource_id","right_key":"/resource_id","as":"policy","kind":"inner"}],"select":{"resource":{"field":"/resource_id"},"reason":{"field":"/trade_type_name"},"incoming":{"field":"/inbound_total_units"},"warehouse_stored":{"field":"/stock/stockpile_stored"},"configured_buy_cap":{"field":"/policy/buy_price_cap_raw"}},"limit":5}]}
```

All trade reasons are retained. If the question concerns market trade only, first inspect the installed reason IDs/names and filter the observed ID; do not assume a translated label or index is permanent. Incoming stage counters are not completed imports and must not be summed with daily ledger quantities as independent arrivals. A configured price cap is not an executable quote. Inspect resource help using the policy's returned `reference_id` when an explanation needs installed descriptions.

### Nested unavailable observations

An enclosing observation can be unavailable even when its overall domain is partial. A battlefield's city-trade pipeline is one example. `select_game_state` refuses an unavailable nested source or join, so aggregating it cannot produce a misleading zero. Field projections of its container return null. `query_game_state` reports the effective unavailable coverage and reason, with null data/total for a container, while scalar diagnostic metadata remains readable. Replies and source records retain `subtree_coverage`, `subtree_scope` and `subtree_reason` where supplied; the existing domain scope remains separate. An observed, available empty table can still legitimately count as zero.

## Service points and staffing

Use `describe_game_fields("services")`, then select `/room_data/rooms`. The runnable example in [service-query-example.json](service-query-example.json) filters positive configured service counts and left-joins staffing by the same-observation `room_id`, with five result rows and shared UI context. Some services have no employment row: the projected staffing object remains null. Reading a nested field through that null object is a missing-field error under the query contract; do not replace it with zero.

`total_slots_raw`, `available_slots_raw` and `reserved_slots_raw` are stored room-specific service-point counters. They do not establish people/day, demand, citizen permissions or reachability, and total minus available need not equal reserved. Read [SERVICE_COUNTERS.md](SERVICE_COUNTERS.md) and the returned coverage/limits before using these values in advice. The existing aggregate `/statistics` table remains separate.

## Configured city service policy

`services /access_policy/service_types` identifies registered service types and installed room help; `/access_policy/cohort_rules` holds concrete race/class configuration flags. Inspect field definitions before using them: these are not effective individual permissions or visits, and a registered type can have no built instance. Battlefield city-policy defaults are unavailable, so nested table pages/counts cannot be interpreted as an empty valid city policy.

[service-policy-query-example.json](service-policy-query-example.json) selects configured false flags and joins population on race, then explicitly filters class equality. Both conditions are needed to match the cohort; matching race alone multiplies other classes. The returned `scene_population` is a cohort count, not a count of individuals actually denied service. The same observation supplies UI context. See SERVICE_PERMISSIONS.md for caps, batch/failure behavior and individual-rule exceptions.

## Collection diagnostics on table reads

`query_game_state` now includes `collection_diagnostics`. Each selective result's `sources` includes the same field for its main source and every join. It carries a small allowlist of scalar collector flags, counts and limits from the requested node and its ancestors. Each entry's `path` is relative to that domain's data root; an empty path means the root. Failure sample text and unrelated game values are not copied.

For example, a source at `/access_policy/cohort_rules` retains its parent's `truncated`, `failed_service_types`, scan counts and row/type/race/class limits. Paging to the end does not clear those collection flags. `total`, `matched_total`, aggregate counts and pagination describe the **exported rows**, even if collection omitted rows. A missing configured policy after truncation/failure is unknown. Joins retain diagnostics separately for each input; a successful join cannot restore omitted source rows.

Ancestor flags keep their original names and scope. For example, `population_truncated` does not assert that the separate region table was truncated. A false truncation flag does not establish complete coverage: inspect failed-read counts, coverage, source meaning and known API gaps as well.

Diagnostics follow the source/pointer path; they do not scan all descendants of a projected container. Choose the actual table as a source or paged pointer when checking its collection limits. Selecting `/access_policy/cohort_rules` as a field from the whole services object does not automatically attach that nested table's diagnostics. This metadata does not bypass unavailable-source refusal, snapshot pinning or existing query budgets.

`dev/verify_collection_diagnostics.py` exercises synthetic cap/failure observations through MCP and checks source/join/work limits. Synthetic flags are deliberately authored; this is not game collector cap/fault injection or large-city performance evidence. Native service checks separately compare flags/limits with the copied game's actual untruncated export.

## Stored workforce factors and production records

`employment /rooms` now includes `work_factors` with stored efficiency, travel/fetch factors, a blueprint flag selecting whether fetch participates, and the game's combined employment factor. Run workforce-query-example.json for a bounded staffed-room selection and a same-observation output/staffing left join. Projecting the whole staffing object preserves null when a join is unmatched; do not traverse a nested field through null without a guard.

Inspect `describe_game_fields("employment")` for meanings and periods. These dimensionless values may be smoothed/defaulted/reset; exact sample age is unknown. They are not current productivity percentages, complete room/person/technology modifiers, input availability or future output. Production ledger buckets have their own age/carry limits. Employment root scan/row limits, failures and truncation follow `/rooms` into each query source's `collection_diagnostics`. A missing workforce row remains unknown. See WORKFORCE_FACTORS.md and WORKFORCE_VALIDATION.json.


## Select people assigned to an observed room

`query_live_entities` and `capture_live_entities` share the optional strict integer `workplace_room_id`. It combines with other predicates using AND, whether or not relationships are projected. Discover the current room index from observed employment or workplace data; do not invent an ID or infer the selected instance from an open blueprint. For example, pass this as the live tool's `spec` after replacing the example ID:

```json
{"workplace_room_id":123,"fields":["id","relationships"],"limit":25}
```

Follow `next_cursor` with the same filter even after an empty page. For stable bounded paging, use the same selection with `capture_live_entities`, replace `limit` with `max_rows`, then page the returned capture. Inspect the returned original session/tick/time/context. `game_query_help.on_demand_entities.workplace_filter` and WORKPLACE_FILTER.md explain limits and compatibility.

This selects recorded assignments, not active work, profession, room occupancy or UI selection. Unassigned people and non-humanoids do not match. Room indices can be reused even within a session: a separately cached room row and a later live selection are separate observations, and `expected_session_id` does not make those observations simultaneous. Check returned blueprint/anchor identities; do not silently join separate observations as one. Live predicate errors mean completeness is unknown; capture predicate errors fail without retaining rows. Existing row, scan, byte, deadline and retention bounds apply. Older mods reject the optional wire key explicitly; install the paired current player build.


## Producer-room degradation and recorded output

`production /room_data/flows` now includes `room_degradation_raw`. Retrieve meanings from `describe_game_fields("production")`; `degradation-query-example.json` selects output/resource rows, this dimensionless stored value and nullable staffing in one observation. Sort paths refer to projected names (`/degradation` in that example). Each resource flow repeats its room's value, so do not sum degradation across rows or count those rows as unique rooms.

The shipped base decoder hides initial wear below a threshold: zero does not prove no wear or no maintenance need. Exact last wear/maintenance time, required resources, full production modifiers and actual current throughput remain unknown. Nonfinite values are null; failed rooms are omitted/counted by existing production diagnostics, not replaced with zero. Source/ancestor truncation/failure limits remain attached to these selections. Observe scene/session/time and same-observation room IDs; battlefield room data describes that scene, and setup without a settlement is unavailable. See ROOM_DEGRADATION.md for the reviewed producer boundary and third-party override caveat.


## Retained tiles

Use `capture_live_tiles` and `read_tile_capture` for a complete small selection retained from one existing update callback: rectangle area <=4096, max_rows <=100 and payload <=64 KiB. Incomplete scans, remaining cursors, predicate errors and oversized results retain nothing. Original request/session/tick/time/scene/UI stay historical; current_state is separate. Tile tokens have their own three-slot, 120-second server-local pool and cannot be read as entity tokens. Field-level availability remains explicit unknown data. See [TILE_CAPTURES.md](TILE_CAPTURES.md) and `game_query_help.retained_tiles`; live tile cursor pages still have no cross-page consistency guarantee.

## Consistent regional output pages

Use `capture_live_regional_outputs` and `read_regional_output_capture` when a selection must remain unchanged across pages. These tools select the same fixed public active-region/resource fields and inclusive amount/owner predicates as the live regional tool. The entire requested matrix must fit one callback (100 IDs/100 keys, at most 10,000 cells); up to 2,000 matches and 2 MiB are retained. Creation returns a server-local token and original observation metadata; read by matching-row offset, <=100 rows/64 KiB. Incomplete, row/scan/cell-error/byte failures retain nothing. Three regional tokens/120 seconds form a separate pool; freshness and same session/version remain required. Captured fields/context/time are historical, and current_state is separate. Never stitch live pages or mix captures as one transaction. See [REGIONAL_CAPTURES.md](REGIONAL_CAPTURES.md) for an example and native evidence. Stored accruals/offsets still do not establish inventory, forecasts, shipping ETA or UI selection.
