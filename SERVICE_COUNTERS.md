# Per-room service counters — game 0.71.44

The services domain retains aggregate `/statistics` and adds bounded `/room_data/rooms`. The reader enumerates instantiated room blueprints/instances, includes only instances implementing public `ROOM_SERVICER`, and calls `service().total()`, `available()` and `reserved()`. It copies primitive counts on the game thread. Production performs no service reporting, reservation, load/refresh, finder request or save operation.

These mappings are **shipped-source-verified public APIs**, not separately documented stable mod contracts. The compiler audit provides declarations and production call sites. `dev/verify_service_contract.py` independently checks the three getter bodies in the installed binary: each returns one stored short counter directly. A scoped source scan also finds 24 concrete public `RoomServiceInstance service()` declarations, all simple stored returns. This does not prove exhaustive inheritance or mod compatibility. Its output contains hashes and conclusions, not game code. Source anchors are `settlement/room/service/module/ROOM_SERVICER.java:8` and `RoomServiceInstance.java:74`, `:78`, `:82` in the pinned source archive.

| Field | Meaning and limit |
| --- | --- |
| `room_id` | Public room-instance index; joins employment and recorded person workplaces **within the same observation**. Can be reused after replacement; does not identify the UI-selected room. |
| `blueprint_id`, `reference_id` | Room type and matching installed help. Descriptions can be changed by installed mods. |
| `active` | Public activation flag. Inactive rooms can retain stored counters. |
| `total_slots_raw` | Stored configured service-point count for this room. Meaning depends on the room implementation; not a people-per-day or throughput estimate. |
| `available_slots_raw` | Stored reported reservable service points. This does not establish whether a particular citizen can reach or use them. |
| `reserved_slots_raw` | Stored reported reserved service points. Unavailable points can have other causes, so `total - available` must not be labeled reserved. |

`RoomServiceInstance.report` updates counters according to room-specific reservability/reservation reports. The adapter does not call it. No counter refresh timestamp, full demand model, permission schema, all service providers or causal explanation is established here. Do not label these raw fields satisfaction, daily capacity or actual customers. A missing room/interface is not a zero count.

The reader stops at 10,000 scanned instances or 2,000 successful rows. It reports both limits, truncation, failed-room count and at most ten failure samples. A row is added only after all its reads succeed. Failed rooms are omitted with diagnostics; they do not receive invented zeros. A domain-level getter error remains unavailable. Without an instantiated settlement scene the domain is unavailable. Battlefield observations describe their instantiated scene, which can legitimately contain no matching services.

`service-query-example.json` filters positive configured service counts and left-joins employment, retaining at most five rows plus context from the same snapshot. It projects the joined staffing object: some services have no employment row, so that object remains null. Reading `/work/employed` through a null join is a missing-field error under the existing query contract. Null staffing does not establish zero workers or zero service.

The copied-city fixture uses only direct getters and pauses the game without writing a save. The current validation checks all eight matching rooms, including nonzero available/reserved values, against actual MCP paging, a staffing join, field meanings and installed help links. See SERVICE_VALIDATION.json for the exact candidate and finite runtime scope. Larger cities, cap/fault injection, every room type, and citizen-specific access remain unvalidated.
