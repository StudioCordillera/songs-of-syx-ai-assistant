# Game-data coverage and next mappings

This is a routing inventory of the current adapter, not a complete game schema. Every domain is partial. Discover observed paths/types and available meanings through `describe_game_fields`; obtain actual values with bounded selections. Definitions absent from an empty/unavailable observation must not be guessed.

| Domain | Main snapshot query paths | Established content | Principal remaining gap |
| --- | --- | --- | --- |
| population | `/total`, `/by_race_class` | Scene counts by race/class | Growth factors, complete histories and individual attributes |
| resources | `/stockpiles`, `/stockpile_bookkeeping/rows`, `/field_definitions` | Bounded global city assigned-crate, stored/capacity and stored/incoming-reservation counters; distinct mixed-logistics owned quantities | Crate relationships, transit/ground goods, exact tally age and effective reachability |
| production | `/resources`, `/room_data/flows` | Campaign ledger plus bounded current scene recipe inputs/outputs, stored quantities and producer-room degradation | Production modifiers, bucket alignment, retained observations and forecasts |
| employment | `/rooms`, `/field_definitions` | Bounded room identity, workforce counts/targets and stored work/travel/fetch/combined factors; shared room-instance key | Jobs/history, exact factor age and complete production modifiers |
| services | `/statistics`, `/room_data/rooms`, `/access_policy`, `/field_definitions` | Aggregate stats, per-room raw service points and configured race/class permission flags, linked to staffing/population/help | Daily capacity, demand, effective individual access/reachability, full provider types and explanations |
| housing | `/statistics` | HOME aggregate stats | Home availability, quality and occupancy relationships |
| health | `/statistics` | Disease/environment/food aggregate stats | Causes, disease progression and complete treatment coverage |
| law | `/statistics` | LAW aggregate stats | Individual cases and complete enforcement/punishment factors |
| happiness | `/statistics` | Public collection aggregates | Expectations and causal contribution schemas; individual stats remain separate |
| research | `/technologies`, `/requirements`, `/costs`, `/currencies`, `/field_definitions` | Levels, expanded prerequisite closure, per-currency costs and allocation | Non-technology unlock conditions, effects and forecasts |
| trade | `/resources`, `/settlement_pipeline/policies`, `/settlement_pipeline/flows` | Campaign current-day ledger; bounded city resource stages by trade reason and raw configured limits | Full order records, non-resource tradables, executable quotes/tariffs, routes/ETA and large-city cost |
| diplomacy | `/factions` | Active faction identities and stance | Treaties and relationship factors |
| military | `/statistics`, `/scene_armies` | BATTLE aggregates and instantiated scene divisions | Full world-army/order schemas and combat history |
| world | `/regions`, `/population_by_race`, `/regional_output_bookkeeping/rows`, `/regional_output_bookkeeping/schedules`, `/field_definitions` | Region identity/ownership/population plus bounded resource-backed stored accruals and cyclic configured offsets | Retained regional selections, other economy/army relationships, actual shipping/arrival, exact counter age, non-resource output and large-world/cap/fault validation |
| map | dimensions, `/weather`, on-demand tool description | Scene dimensions, ten stored weather factors/four flags, finite tile reads and bounded retained tile selections | Broader spatial fields, larger retained batches and all-field/scene/fault costs |
| entities | `/items`, `/selected_subject` | Prefix IDs/positions and dedicated selected-person public stats | More typed attributes and relationship filters beyond recorded workplace |
| events | `/registered_event_types`, current event ID/elapsed fields | Registered event types and current scripted event | Complete incidents/history and future-event claims |
| settings | pause/speed/time fields | Current public clock and requested speed | Full settings schema |

Aggregate stat collections are intentionally left in game-defined units until their meaning is established. Counts and normalized values are not automatically satisfaction percentages or causal effects. Population aggregates do not substitute for a selected person's attributes.

## Reads beyond the prefix snapshot

- `query_live_entities`: finite projected fields, IDs, recorded-workplace room filter, named stat filters and recorded workplace/profession/home/division assignments. Cursor pages are separate observations.
- `capture_live_entities` / `read_entity_capture`: bounded detached observations retained for stable paging, with original session/tick/context. Not a global worker transaction.
- `query_live_tiles`: terrain/floor/room/mineral/path/stored-moisture fields in a bounded rectangle, with fixed filters. Coordinate room data does not identify a UI-selected room. Cursor pages remain separate observations.
- `capture_live_tiles` / `read_tile_capture`: a complete <=4096-tile scan with <=100 matches/64 KiB from one callback, then retained historical pages; incomplete selections retain nothing.

- `query_live_regional_outputs`: explicit active-region/resource matrix with fixed accrued-range/faction filters and projections, independent of cached output rows. Each page is a separate live campaign observation; not a retained/global transaction.

See QUERY_GUIDE.md for exact limits and query syntax. IDs must share a documented mapping before joins are used: similarly named labels or different composite IDs are not proof of a relationship.

## Mapping order

1. Extend the established same-observation room-instance relationship key to production mappings. Employment/person workplace getter agreement and the selected-worker join now pass in the copied city; indexes are not permanent IDs.
2. Current public producer-room inputs/outputs and recorded quantities are mapped with explicit rate/bucket caveats. Extend production modifiers and bucket-age semantics only where public getters can establish them; validate performance and cap behavior in a larger city.
3. Extend world-region and trade fields where safe public getters and useful units can be established.
4. Broaden UI-selected object/context mappings only through appropriate public accessors; preserve unavailable states when accessors do not exist.

Each mapping needs source semantics, compiler/public access verification, bounded detached output, scene applicability, copied-game getter checks and a small agent-facing selection example. The public declaration catalog is a discovery aid; it does not automatically expose members or count supported variables.

## Stored production periods

[Production-period review](PRODUCTION_PERIODS.md) establishes the pinned source/binary rollover behavior and the absence of an exact public age getter in the inspected classes. The protected marker and opaque storage are not used by the adapter. Existing stored-bucket caveats remain required; this review does not convert a bucket into a calendar-aligned rate.

## Service availability and staffing

[SERVICE_COUNTERS.md](SERVICE_COUNTERS.md) records public getter meanings and boundaries for the new room service table. [service-query-example.json](service-query-example.json) retains services without an employment row as a null staffing object. Stored points are not people/day, and missing interfaces/failures do not imply zero service. The copied-city evidence is finite; large-city caps and all provider types remain open.

Configured city permissions now have a separate bounded [policy mapping](SERVICE_PERMISSIONS.md) and [cohort query example](service-policy-query-example.json). Flags apply to registered service types, including unbuilt ones; individual nobles/tourists/children can follow different rules. Missing policies are unknown, not denial. Battlefield/setup policy defaults are not exported as campaign-city settings.

[Stored workforce factors](WORKFORCE_FACTORS.md) extend employment with source-backed public readers and an output/workforce join example. The factors are stored/defaulted/smoothed and are not current productivity percentages or a complete modifier stack. Employment now reports 2,000-row/10,000-room-scan limits, failures and truncation; missing joined rooms remain unknown. Both fetch-participation branches have finite copied-city getter/arithmetic evidence; larger-city and cap/fault branches remain open.


The workplace-filter checkpoint selects assigned humanoids through the existing public recorded-workplace getter, including stable retained-capture paging. WORKPLACE_FILTER_VALIDATION.json compares 14 matching workers with native getters in a paused copied scene containing 1,395 entities, checks other-room/unassigned exclusions and combined ID/race/stat predicates, and repeats actual prefix-cap diagnostics. It does not establish current activity or permanent room identities. PRODUCTION_MODIFIER_BOUNDARIES.md records why generic employee-cache/production-rate helpers remain outside the bounded observer; the full modifier stack remains open.


[Producer-room degradation](ROOM_DEGRADATION.md) adds a thresholded stored room value to each current recipe flow, with same-observation staffing joins and explicit zero/age/row-grain limits. It does not establish instantaneous productivity, maintenance cost or a full bonus stack. Non-producer chamber and construction semantics remain outside this producer mapping. Larger-city costs and cap/fault cases remain open.


## City stockpile reservation bookkeeping

`resources /stockpile_bookkeeping/rows` adds five bounded global counters per resource: assigned crates, stored items, assigned item capacity, reserved stored items and reserved incoming capacity. It is city-only, not per-room or ground/in-transit coverage. Zero capacity is retained without a fullness default; failures/truncation qualify missing rows. RESOURCE.owned keeps its broader scope. See [field meanings, query and validation](STOCKPILE_BOOKKEEPING.md). The earlier stockpile reader report is a pre-mapping checkpoint, not current release evidence.


## Retained spatial selections

Small tile selections can now be retained in one callback through `capture_live_tiles`, then paged with `read_tile_capture`. Rectangle area <=4096, max_rows <=100 and payload <=64 KiB; incomplete/predicate/byte failures retain nothing. This improves cross-page consistency for that finite selection, not full-map/all-variable coverage or UI-selected-room identity. [TILE_CAPTURES.md](TILE_CAPTURES.md) records original-context/token/lifecycle limits and city-only value-parity evidence.

Regional outputs additionally support complete bounded retained selections through `capture_live_regional_outputs` / `read_regional_output_capture`. This adds consistency across pages, not new game variables: the same explicit public output/owner getters and meaning limits apply. Matrix <=10,000 cells, matches <=2,000, payload <=2 MiB; any incomplete/error/overflow result retains nothing. See REGIONAL_CAPTURES.md and its exact source/JAR evidence. Native faults/largest-world cost and full UI/lifecycle coverage remain unestablished.

The optional `ground_moisture` tile projection exposes separate quantized base/current fractions from public stored maps. It does not export MOISTURE_TOT, precipitation, fertility or crop/pasture yield. Bounds, instantiated scene/session, per-field availability and original live/captured time remain explicit; see [GROUND_MOISTURE.md](GROUND_MOISTURE.md).

Cached viewport geometry is additionally available in same-observation UI context, outside the eighteen data domains. Four active-window routes export primitive cache rectangles/zoom/map bounds with explicit city/battlefield/world scene provenance, null/unavailable guards and unknown age/visibility. CACHED_VIEWPORT.md and VIEWPORT_VALIDATION.json retain the getter/MCP limits; this is not a hovered/selected object or a complete visible-tile census.

## Live warehouse/resource selections

`query_live_stockpiles` supplies per-room raw stored/capacity/reservation/crate counters independently of cached room prefixes. Explicit IDs or typed warehouse-slot discovery, exact resource keys, fixed AND predicates/projections and bounded mutable pages are described in STOCKPILE_LIVE_READS.md. This is a separate observation; room IDs can be reused, slots can reorder, and zero capacity/inactive stored values are not missing data. The cached resources domain above still contains global totals. No crate handle, all-logistics census, UI-selected room, exact counter age or multi-page transaction is established.


[Weather](WEATHER.md) is completed instantiated-city bookkeeping under map /weather, including underlying city data in other views. Weather data/definitions share the snapshot/context; battle/setup or failures are unavailable/null. Legitimate zero remains zero. Game factors are not physical units, tile moisture, regional weather, crop yields or forecasts; cached ripeness flags may use the previous factor during engine update.
