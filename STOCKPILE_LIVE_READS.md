# Live per-warehouse bookkeeping — game 0.71.44

`query_live_stockpiles` retrieves a bounded room/resource matrix directly from public stored getters on `GAME.addAfterUpdate`, independently of cached room prefixes. The paired mod/helper must both be updated and restarted. It is read-only and does not pause the game. [Public reader review](STOCKPILE_LIVE_CONTRACT_REVIEW.json), [MCP/native evidence](STOCKPILE_LIVE_VALIDATION.json) and the paired player report establish different scopes; none establishes every variable, menu or logistics location.

## Select only the data needed

Call `game_status` and `game_query_help` first. Discover installed resource IDs from resources/help; use exact keys. For example, this selection uses `GRAIN`, observed in the tested installation; other mod sets can differ:

```json
{"resource_ids":["GRAIN"],"fields":["stored_raw","capacity_raw","reserved_stored_raw","reference_id"],"filters":[{"field":"capacity_raw","op":"gt","value":0}],"limit":25}
```

An omitted/empty `room_ids` list discovers current warehouse instance slots. Returned rows include mandatory `matrix_position`, `room_id`, `room_blueprint_id`, anchor tile coordinates, `room_active` and `resource_id`. To revisit specific observed warehouses, supply up to 100 unique nonnegative current room IDs; unknown/non-warehouse IDs refuse the entire request. IDs may be reused, so inspect the returned blueprint, anchor, scene, session and observation time. They are not permanent world identities or UI-selected rooms. An optional canonical `expected_session_id` refuses a changed load before dispatch.

Select up to 100 unique exact resource keys and one to six fields. Five counters use the [existing bookkeeping meanings](STOCKPILE_BOOKKEEPING.md): `assigned_crates`, `stored_raw`, `capacity_raw`, `reserved_stored_raw` and `reserved_incoming_raw`; `reference_id` links installed `resource:<key>` help. Raw signed integers and actual zero capacity remain unchanged. Inactive rooms can retain stored counters. None means freely usable stock, all settlement inventory, actual incoming deliveries, physical fullness or a forecast. Counter age is unknown. Resource help describes the resource, not every reservation mechanic.

Up to four fixed AND filters accept a counter `field`, `op` (`eq`, `ne`, `lt`, `lte`, `gt`, `gte`) and signed 32-bit `value`. `active` optionally filters a strict boolean. Filtering is independent of projection; no arbitrary names, expressions or methods run in the game.

## Paging and observations

`cursor` indexes the current room-slot × requested-resource matrix, including filtered/error cells. A callback scans at most `scan_limit` (1–4,096) cells and returns at most `limit` (1–100) matching rows. Keep ordered IDs, resources, fields and predicates unchanged and follow `next_cursor`, even after an empty filtered page. A zero-room city can return an available empty terminal matrix. Errors qualify absence/count; failed cells never become zero rows.

Every page is a separate observation. Implicit slots can shift after removal and explicit room IDs can be reused between callbacks. Even the same session, blueprint and anchor can belong to a different room instance; these attributes do not establish durable identity. No retained warehouse capture, complete cross-page transaction or automatic join to an older cached room is supplied. `request_id`, session/version, tick/time, scene and UI context describe this response; do not substitute a cached snapshot's context or merge timestamps. The current scope is a completed instantiated campaign city, including its underlying bookkeeping while another view is open. Generated battlefield and initial/terrain world setup refuse rather than exporting city defaults.

Requests are canonical ASCII frames with encoded UTF-8 resource keys, at most 8 KiB and an eight-second normal client deadline. The shared POSIX lock serializes entity/tile/regional/warehouse requests. Only detached requests cross to the game thread; only detached DTOs cross back. Serialized game responses exceeding 64 KiB become a correlated unavailable/null result; the Python client also validates bounds, identities, projections, ordering, predicates and output text size. No crate scratch handle, reservation/report/deposit/refresh action, private access or arbitrary invocation is exposed.

## Evidence and limits

The production compiler inventory has 397 public/zero non-public references. The four added references are integer-index per-room tally access, `RoomsMap.max`, `RoomsMap.getByIndex` and `LIST.get`. Source review establishes the concrete `ArrayListResize` behind the final blueprint `all()` getter and the valid stored indexed-read path. Its invalid-index exception path allocates and is explicitly excluded from allocation-free claims. These are shipped-source/binary findings, not separately documented stable official mod contracts.

The earlier [candidate check](STOCKPILE_LIVE_NATIVE_VALIDATION.json) compared 72 requests/8,170 counters in one paused copied city. The production [live check](STOCKPILE_LIVE_VALIDATION.json) separately verifies actual MCP rows/pages/projections/predicates/refusals, three concurrent callers and eight real scene phases including reload and generated battle/setup. Public test-only scene controls run only in the validated disposable profile/save. Offline tests add strict schema/corruption/byte-bound/cross-language allowlist cases. The simple Pro client and current production-source-matching bundle keep separate release/provider/core/distribution evidence.

The separate [lifecycle follow-up](STOCKPILE_LIFECYCLE_VALIDATION.json) now verifies one actual distinct-instance ID reuse and complete removal through MCP. One warehouse and 42 resources still do not prove multi-room ordering/reuse combinations, real 4,096-cell/100-row caps, injected registry/cell faults, native byte overflow, unusually large UI-context budgets, large-city latency/FPS or full menu/lifecycle coverage. Main-menu identity/instant unload remains unestablished, with the existing freshness fallback. Older candidate/global reports retain their dates/hashes and finite scope.

Reproduce with licensed files, a copied `runtime/smoke.save`, isolated `runtime/smoke-home`, a full JDK and compatible game Java:

```sh
xvfb-run -a -s '-screen 0 1280x960x24' .venv/bin/python dev/run_read_fixture.py \
  --case stockpile-live --game-dir '/path/to/Songs of Syx' \
  --jdk-home '/path/to/jdk' --java '/path/to/game-compatible/java' \
  --save runtime/smoke.save
```

The runner owns the shared device fixture lock, checks game/source pairing, rejects known crash markers, restores the copied mod and verifies the copied save unchanged. This command makes no provider calls. For an unpublished candidate add its `--candidate-dir` and matching `--validation`; do not bypass freshness checks.

A local Claude Code Opus 5.5/high, tool-free focused critique attempt ended at our 180-second runtime window without final text. CLAUDE_UX_COLLABORATION.json records the incomplete outcome and source hashes. No peer approval or model/credit rejection is inferred, no credits were purchased and the route was not retried. Source/compiler/offline/native/MCP/player checks remain independent.


## Removal and ID reuse follow-up

`StockpileLifecycleScenario.java` and `dev/verify_stockpile_lifecycle.py` exercise three held phases against the unchanged published player JAR: an active warehouse baseline, a distinct reconstructed inactive instance with the same room ID/blueprint/anchor/session, and no warehouse after removal. Nine successful MCP pages match independent public getters and active filters; removed explicit IDs and a former nonempty-matrix cursor fail for the expected reasons. The empty discovered matrix returns available/empty, with zero scanned cells and a terminal cursor.

The [manual shipped-source review](STOCKPILE_LIFECYCLE_SOURCE_REVIEW.json) pins the public test routes and relevant internal implementation hashes. Only public methods run in the fixture, on the update thread. Source inspection shows ordered removal shifts later discovery slots, but the one-room native fixture does not validate multi-room ordering. This is additional finite lifecycle evidence, not a new stable official contract or a gameplay tool.

An initial fixture assumption that the first replacement always gets the removed ID was rejected by a real run: the loaded save can have earlier free indexed slots. That run is excluded from acceptance. The final fixture first reconstructs once to normalize the allocator, then measures actual ID reuse on a subsequent reconstruction. Zero-default construction costs and copied statistics are test inputs; crate disposal/construction may scatter or collect disposable-city goods. In-memory changes are discarded without saving, rather than claimed restored. Clean completion, known crash-marker checks, copied-mod restoration and copied-save integrity pass. The full 580-test offline suite and unchanged player-source freshness checks pass; no provider inference or release rebuild is needed for this developer-only follow-up.

Reproduce using the command above with `--case stockpile-lifecycle`. The same licensed-source pairing, private copied-save/profile and shared-lock requirements apply. Full caps/faults, multi-room cases, larger-city costs and broader UI/lifecycle/reference coverage remain next.
