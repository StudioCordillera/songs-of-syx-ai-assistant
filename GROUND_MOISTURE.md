# Stored tile-moisture queries

The optional `ground_moisture` projection is available in `query_live_tiles` and `capture_live_tiles`. It reads two public stored maps in the same game after-update callback as the other requested tile fields:

| Field | Meaning | Unit / limits |
| --- | --- | --- |
| `base_fraction` | Stored base tile moisture | Four-bit value divided by 15, quantized 0..1. |
| `stored_current_fraction` | Separate stored current tile moisture | Four-bit value divided by 15, quantized 0..1; exact age/convergence is unknown. |

The projection adds two stored-map getters per returned row, at most 200 additional reads under the existing 100-row response bound. This source-level call bound does not measure total request cost.

This is source/binary verified public access, not a separately documented stable mod contract. The pinned source shows current stored moisture approaching a clamped base-plus-water target one raw step per adjustment call. It is distinct from `MOISTURE_TOT`, rainfall, fertility and crop/pasture yield. None of those other quantities, irrigation eligibility, construction suitability or forecasts is established by these two fields.

## Selection and provenance

The snapshot map-domain field list is cross-checked against the query-help schema in the native MCP fixture, so this optional projection is discoverable through both routes.

Request only the fields needed. Default tile-query fields remain terrain/floor/room. Moisture values are read on demand; the regular snapshot updates only its tile-projection discovery list. For example:

```json
{"tile_bounds":[0,0,10,10],"fields":["ground_moisture"],"limit":25}
```

Upper bounds are exclusive. The existing fixed terrain/floor/room/mineral/path predicates can combine with this projection. Moisture thresholds are not live predicates in this version; there is no arbitrary expression/member invocation. Existing limits remain 4,096 scanned tiles, 100 returned rows and 64 KiB. Each live cursor page is a separate observation. Do not combine their values as though one simultaneous sample.

For stable bounded paging, call `capture_live_tiles` with the same bounds/fields and `max_rows:100`, then `read_tile_capture`. A complete rectangle must fit the scan budget and all matching rows/encoded bytes must fit; an incomplete selection retains nothing. Captured rows/time/UI remain historical; `current_state` is separate. Token/session/freshness/expiry rules are in [TILE_CAPTURES.md](TILE_CAPTURES.md).

The bridge validates the requested rectangle against the instantiated map before reading. Although the underlying moisture getters return zero outside their map, the tool rejects such requests; it does not export that default as a valid dry tile. A failed projected group uses `available:false, data:null`; failed reads are not zeros. Successful fractions of zero remain valid observations.

Inspect `scene`, session, request ID, tick/time and original UI context. An instantiated battlefield has its own tile maps; its coordinates/moisture are not the user's city. Setup without an instantiated scene refuses the query. World view can retain a loaded city map: the tool describes that instantiated map, not campaign/world-map tiles. It does not identify a UI-selected tile or room, establish topmost visibility, or bypass the existing up-to-30-second unload freshness limitation.

Protocol 1 and existing request keys/bounds remain unchanged; the projection adds a fixed field name. Older mods reject that unknown field rather than supply it. Install/restart the paired mod and helper from the source-matching player bundle.

## Evidence and limits

[GROUND_MOISTURE_BOUNDARY_REVIEW.json](GROUND_MOISTURE_BOUNDARY_REVIEW.json) pins the source/compiler/selected-bytecode review. [GROUND_MOISTURE_READER_VALIDATION.json](GROUND_MOISTURE_READER_VALIDATION.json) preserves the earlier candidate-only reader test: 4,096 sampled coordinates over 64 samples, all sixteen naturally observed quantized values and 49 base/current differences. Its two overloads share storage, so their agreement is not independent raw-storage truth. That report retains its prior JAR/source scope and is not relabeled as production MCP validation.

[TILE_CAPTURE_VALIDATION.json](TILE_CAPTURE_VALIDATION.json) records the production follow-up against native public linear-reader expectations: live points include zero/full base and naturally different base/current values; separate 100-row terrain/room and moisture-only captures preserve values and original context across simulation/view changes. Concurrent page checks cover the separate terrain/room capture; a fresh moisture token is rejected after real session rotation. Retained paging writes no new tile request. [PLAYER_CORE_VALIDATION.json](PLAYER_CORE_VALIDATION.json) and the tile fixture's scene follow-up distinguish city/tactical HUD, generated battlefield/menu, city reload and unavailable initial/terrain world setup. City point/capture checks use actual stdio MCP; scene follow-ups invoke the production query helper and fixed game mailbox directly. These are finite copied-save cases, not all maps, natural moisture evolution, native getter faults, worst-case cost or every menu.

The existing 64-KiB budget still applies to wide projections. The native follow-up exercises a 100-row terrain/room/moisture request refused by the tool text budget, then preserves all 100 moisture-only rows without increasing that budget. The prior candidate read-loop timings excluded DTO construction/encoding/transport; they are not measured production request latency or an FPS guarantee. [USER_TEST_VALIDATION.json](USER_TEST_VALIDATION.json) pins the current player source/JAR and validation scope; earlier feature reports retain their own source scope.

Reproduce the source review using [the boundary guide](GROUND_MOISTURE_BOUNDARY.md), then use `dev/run_read_fixture.py --case tiles` with the licensed/copied-game arguments in [CONTRIBUTING.md](CONTRIBUTING.md). These fixtures use public test-only view/speed/battle/reload/setup actions in a disposable profile. Production observation remains read-only; no screenshots, reflection, process memory, native input or arbitrary member invocation is used.
