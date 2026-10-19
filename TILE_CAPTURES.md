# Retained bounded tile selections

`capture_live_tiles(spec)` collects one complete bounded selection through the existing public tile-read callback. `read_tile_capture(capture_id, offset, limit, include_ui_context)` pages encoded detached rows from that observation. Paging does not ask the game to read those tiles again. This adds MCP retention, not new game getters, a game freeze or a full-map snapshot.

## Selection and completeness

Use the fixed `query_live_tiles` fields and AND predicates: terrain, floor, room, minerals, path and optional ground_moisture, with explicit `[x1,y1,x2,y2]` bounds and exclusive upper limits. `game_query_help.retained_tiles.selection` supplies the strict schema.

- Rectangle area must fit `scan_limit`, at most **4,096 tiles**. This is checked before contacting the game.
- `max_rows` is 1–100, default **100**. Cursor must be zero; a capture never combines multiple live pages.
- Both the existing tile response and retained encoded payload have **64 KiB** limits. Wide projections may need fewer tiles/fields even when row counts fit.
- A remaining cursor, incomplete scan, predicate error or byte overflow retains nothing. Narrow the rectangle, add appropriate predicates or increase a smaller `max_rows` up to 100. A failed request does not evict an earlier capture.
- A complete empty result means no matches inside that rectangle/predicate during that callback. It does not establish absence across the game or prove a supplied identifier exists.

`selection_complete=true` describes the matching row selection only. Field-level `available=false` remains unknown data; `coverage` stays partial. Successful `available=true, data=null` preserves an observed absence. No field failure becomes zero or complete variable coverage. Room records can be shared singletons; a coordinate is not a unique building, permanent identity or UI-selected room. Existing path/mineral/floor meanings and construction/route limits still apply.

## Retention, context and lifecycle

Creation returns metadata and a random server-local token, not all captured rows. Metadata includes original request ID, session, game version, tick, time, bounds, scene, selection, scan count and row count. Pages preserve those identities and values. Optional `captured_ui_context` is the original context; `current_state` is separate freshness/status metadata and must not be used as the source of captured values.

Tile and entity captures use **separate pools**, each with three slots. A fourth successful tile capture evicts the oldest tile capture. Each token expires after 120 seconds on the server monotonic clock; suspend/wall-clock-change behavior is not separately validated. The tile pool holds at most three 64 KiB payloads; the existing entity pool retains its separate three 2 MiB payloads. Tokens are not persistent, shared between MCP processes or guaranteed to survive another chat turn/server restart. Private chat history may retain previously returned evidence; it is not the capture store.

Each page is limited to 100 rows and 64 KiB. Reduce the page size or omit UI context if its response is too wide. A fresh loaded same-session/version non-demo game observation is required. Stale status refuses the read; a session/version change invalidates the token. Use the matching read endpoint: tile tokens are not entity tokens. The existing up-to-30-second unload freshness limitation still applies; retention does not add an instant main-menu hook.

The copied rows come from one game after-update callback. This is not a global simulation/battle-worker transaction. Later live queries, captures, game time or UI views are different observations. Never join them silently or present historical captured rows as current state.

## Example

Create:

```json
{"tile_bounds":[0,0,10,10],"fields":["terrain","room"],"max_rows":100}
```

Then call `read_tile_capture` with the returned ID and `limit=20`, following `next_offset` until null. Include UI context only when needed. For a larger rectangle with sparse matches, narrow predicates and ensure the entire area fits 4,096 scanned tiles; more than 100 matches still fails. A 100-tile selection with all six wide projections may exceed the byte limit. Use live tile pages when independent observations are acceptable.

## Validation and limits

[TILE_CAPTURE_VALIDATION.json](TILE_CAPTURE_VALIDATION.json) pins its exact source/JAR and copied-game MCP checks: 100 retained terrain/room rows against independent public getters; ten pages after active simulation and a world-view change; original request/tick/time/UI preservation; concurrent pages without a new tile mailbox request; an empty 4,096-tile selection; an incomplete 110-tile unfiltered selection refused at 100 rows; wrong-kind token rejection and actual session-rotation invalidation. The fixture changes only copied-game view/speed through public APIs. Production capture tools never pause, mutate or control the game.

[ENTITY_CAPTURE_REGRESSION_VALIDATION.json](ENTITY_CAPTURE_REGRESSION_VALIDATION.json) separately rechecks the shared retention path with 1,395 copied-game entities after simulation, added population and view changes. Unit tests cover immutable response copies, partial/predicate/byte failures, expiry/eviction, separate stores, stale status and changed sessions/versions. Synthetic errors are distinct from actual game getter-fault injection.

[USER_TEST_VALIDATION.json](USER_TEST_VALIDATION.json) and [PLAYER_CORE_VALIDATION.json](PLAYER_CORE_VALIDATION.json) pin the player and finite scene/UI follow-up. New retained-tile value parity is a copied-city test, not exhaustive battlefield, all-field/all-scene, large-map, fault or latency acceptance. Larger retained selections would require a separately reviewed protocol/cost change; this implementation deliberately reuses one existing bounded tile callback.

## Reproduce native checks

After preparing the copied save/profile and licensed Java/JDK as in [CONTRIBUTING.md](CONTRIBUTING.md):

```sh
LIBGL_ALWAYS_SOFTWARE=1 xvfb-run -a -s '-screen 0 1280x960x24' \
  .venv/bin/python dev/run_read_fixture.py --case tiles \
  --game-dir '/path/to/Songs of Syx' --save runtime/smoke.save \
  --java '/path/to/java' --jdk-home '/path/to/full-jdk'
```

Use `--case entities` for the separate shared-retention regression. Both fixed cases acquire the shared native lock, extract/check the published JAR, compile test-only public-API fixtures and restore the copied profile's prior mod. They verify the copied save's checksum before emitting a passing final report. Never wrap these runners in another fixture lock. A source-matching unpromoted player can be selected with `--candidate-dir` and `--validation`, following the contributor candidate workflow. Raw fixture data and logs stay under ignored runtime/; reports publish hashes, counts, scope and checks only. No provider request is made by this runner.

The stored-moisture checkpoint reruns live point and separate retained 100-row moisture-only and terrain/room parity with separate base/current fractions, including naturally different values and zero/full base cases. It preserves the existing capture bounds and error/refusal rules. Read [GROUND_MOISTURE.md](GROUND_MOISTURE.md) and exact current reports; the earlier candidate-only moisture reader report retains its prior JAR scope.
