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

1. `search_game_references` searches resource, technology and stat descriptions loaded by this exact game.
   Cite its reference ID and origin. Active mods can change this text; these are installed-data references.
2. `search_guidance` searches reviewed excerpts with direct URLs, authors, authority, retrieval time,
   version notes and compatibility labels. Prefer official/developer evidence; community guides are secondary.
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

Filters combine with AND: `entity_ids`, `race_id`, `class_id`, `humanoid_type_id`, `tile_bounds: [x1,y1,x2,y2]` (upper bounds excluded), and up to four `stat_filters: [{stat_id,op,value}]` using `eq/ne/lt/lte/gt/gte`. Missing individual getters or unknown stat IDs fail explicitly. `predicate_errors` counts entities whose predicate getter failed; nonzero errors mean matching absence/count is unknown.

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
