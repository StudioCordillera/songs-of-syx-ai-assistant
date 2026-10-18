# Game-data coverage and next mappings

This is a routing inventory of the current adapter, not a complete game schema. Every domain is partial. Discover observed paths/types and available meanings through `describe_game_fields`; obtain actual values with bounded selections. Definitions absent from an empty/unavailable observation must not be guessed.

| Domain | Main snapshot query paths | Established content | Principal remaining gap |
| --- | --- | --- | --- |
| population | `/total`, `/by_race_class` | Scene counts by race/class | Growth factors, complete histories and individual attributes |
| resources | `/stockpiles`, `/field_definitions` | Stored/capacity and mixed-logistics owned quantities | Reservations, transit and full storage relationships |
| production | `/resources`, `/room_data/flows` | Campaign ledger plus bounded current scene recipe inputs/outputs and stored quantities | Production modifiers, bucket alignment, retained observations and forecasts |
| employment | `/rooms` | Room identity, shared observed room-instance ID, position and worker counts/targets | Jobs, production relationships and modifiers |
| services | `/statistics` | Selected public aggregate stat collections | Service capacity, demand, provider relationships and explanations |
| housing | `/statistics` | HOME aggregate stats | Home availability, quality and occupancy relationships |
| health | `/statistics` | Disease/environment/food aggregate stats | Causes, disease progression and complete treatment coverage |
| law | `/statistics` | LAW aggregate stats | Individual cases and complete enforcement/punishment factors |
| happiness | `/statistics` | Public collection aggregates | Expectations and causal contribution schemas; individual stats remain separate |
| research | `/technologies`, `/requirements`, `/costs`, `/currencies`, `/field_definitions` | Levels, expanded prerequisite closure, per-currency costs and allocation | Non-technology unlock conditions, effects and forecasts |
| trade | `/resources` | Current-day imported/exported units | Orders, pending shipments, prices, tariffs and policy |
| diplomacy | `/factions` | Active faction identities and stance | Treaties and relationship factors |
| military | `/statistics`, `/scene_armies` | BATTLE aggregates and instantiated scene divisions | Full world-army/order schemas and combat history |
| world | `/regions` | Region IDs, owners, coordinates and siege flags | Typed regional population/economy/army relationships |
| map | dimensions and on-demand tool description | Scene dimensions plus finite tile reads | Broader spatial fields and retained spatial batches |
| entities | `/items`, `/selected_subject` | Prefix IDs/positions and dedicated selected-person public stats | More typed attributes and relationship filtering |
| events | `/registered_event_types`, current event ID/elapsed fields | Registered event types and current scripted event | Complete incidents/history and future-event claims |
| settings | pause/speed/time fields | Current public clock and requested speed | Full settings schema |

Aggregate stat collections are intentionally left in game-defined units until their meaning is established. Counts and normalized values are not automatically satisfaction percentages or causal effects. Population aggregates do not substitute for a selected person's attributes.

## Reads beyond the prefix snapshot

- `query_live_entities`: finite projected fields, IDs, named stat filters and recorded workplace/profession/home/division assignments. Cursor pages are separate observations.
- `capture_live_entities` / `read_entity_capture`: bounded detached observations retained for stable paging, with original session/tick/context. Not a global worker transaction.
- `query_live_tiles`: terrain/floor/room/mineral/path fields in a bounded rectangle, with fixed filters. Coordinate room data does not identify a UI-selected room. Cursor pages remain separate observations.

See QUERY_GUIDE.md for exact limits and query syntax. IDs must share a documented mapping before joins are used: similarly named labels or different composite IDs are not proof of a relationship.

## Mapping order

1. Extend the established same-observation room-instance relationship key to production mappings. Employment/person workplace getter agreement and the selected-worker join now pass in the copied city; indexes are not permanent IDs.
2. Current public producer-room inputs/outputs and recorded quantities are mapped with explicit rate/bucket caveats. Extend production modifiers and bucket-age semantics only where public getters can establish them; validate performance and cap behavior in a larger city.
3. Extend world-region and trade fields where safe public getters and useful units can be established.
4. Broaden UI-selected object/context mappings only through appropriate public accessors; preserve unavailable states when accessors do not exist.

Each mapping needs source semantics, compiler/public access verification, bounded detached output, scene applicability, copied-game getter checks and a small agent-facing selection example. The public declaration catalog is a discovery aid; it does not automatically expose members or count supported variables.
