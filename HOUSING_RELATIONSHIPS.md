# Recorded home relationships and field meanings — developer candidate

`dev/housing_query_view.py` is an unshipped adapter over the detached [housing candidate](HOUSING_CANDIDATE.md), not a game API reader or player module. It defines home/assignment/cohort field meanings and a bounded assignment table that the existing selective query engine can join. It performs no game calls, file access, provider calls or mutation. The current player continues to expose its existing aggregate housing statistics; these richer paths are provisional.

`build_view` keeps the original `home_records` observation and derives `home_assignments` from its recorded/resolved roster IDs. Each relationship contains `room_id`, `resident_id` and `roster_index`. Room IDs join only to the same observation's home rows. Both room/entity IDs can be reused, and roster order is observation-local. Multiplicity is retained, not silently deduplicated into a population census. Links do not establish physical presence, sleeping, reachability, effective eligibility, current UI selection or permanent world/person identity. A cached entity prefix need not contain every linked resident; no automatic entity-prefix join/completeness claim is added.

The default relationship bound is 10,000 rows, with an absolute 2 MiB detached-view budget. Each home roster is added as a complete observed batch or omitted when the relationship bound would be exceeded. A source roster can already be truncated at 64; that truncation remains explicit. An unavailable roster contributes no invented IDs, while its original failure diagnostics qualify missing links. Source room-scan bounds/failures remain separate from the derived relation bound. In particular, `room_scan_complete=true` can coexist with relation `truncated=true`: the underlying room enumeration completed, but the relationship table hit its own cap. An exact relation bound can complete if all remaining home batches are empty. In this derived table, `scanned_rooms` counts attempted relation batches (including an omitted over-budget batch), not source registry enumeration or the adapter's structural validation pass.

The adapter validates its selected detached shape, uniqueness of home IDs, row/scan extents, resident ID/count/truncation structure and diagnostic lower bounds. It refuses diagnostics that understate an observed failed/capped roster. It does not coerce malformed values, synthesize absent homes/residents, repair stale counters or normalize raw game counts. This is not exhaustive validation of every housing variable or the whole source call graph. Unavailable housing yields null relationship data, not zero relationships. Outputs own their copies; later edits to the input or a description dictionary do not change a previously built view.

## Source-backed meanings

The field definitions explicitly attribute the fixed 0.71.44 public shipped-source/binary routes reviewed in HOUSING_BOUNDARY_REVIEW.json. These are not separately documented stable official housing contracts. Ordinary homes report stored assigned counts; chambers resolve a recorded entity ID to zero/one. Configured per-home capacity is not effective vacancy. Stored odd-occupant bookkeeping is not a fresh unemployment census. Service coordinates are door/service points, and isolation is the reviewed stored/conditional value, not full housing quality.

Ordinary cohort-ledger definitions preserve citizen/slave race/class keys and eligibility-weighted accounting. Null-group sums and sums across cohort capacities are not unique physical beds, reachable housing or per-person eligibility. The adapter does not evaluate policy bits, resource use, lights, queues, or any other excluded getter/action.

## Finite validation

[HOUSING_RELATIONS_VALIDATION.json](HOUSING_RELATIONS_VALIDATION.json) records five actual stdio MCP calls over 36 observed home rows and 204 derived assignment rows. The existing native fixture collects the unchanged candidate and current production snapshot synchronously in one after-update callback. The adapter adds deterministic detached tables/descriptions to a private retained copy outside the game thread; original snapshot ID, time, tick, UI and scene stay intact. This is developer augmentation, not a shipped collector field or live-player mailbox write.

The [authored candidate example](housing-relations-candidate-example.json) actually runs through MCP. Its two queries join assignment rows to homes, then check grouped roster counts and filtered/projected first-roster entries with ordering. Results match the original native roster data, and both sources retain their own scan/failure/limit metadata and scopes. Field descriptions are returned by real discovery. A separate real smaller relation cap omits the next home batch, returns `truncated=true` and preserves the complete underlying room scan. A raw relationship read agrees with the detached view; a different snapshot pin is refused.

Twenty-two synthetic cases cover ownership, caps/exact bounds, unavailable housing/rosters, incomplete source scans, malformed/duplicate IDs, diagnostic understatement and the byte bound. Native valid housing did not exercise every synthetic fault or the 64-ID, 10,000-row or 2 MiB maxima. The full local offline suite is recorded separately in the current handoff; the unchanged player's release keeps its own source-matched earlier test count. A single detached-build interval is descriptive and outside the game thread, not a game/FPS/worst-case benchmark.

The locked native host requires paired source/binary and candidate hashes, explicit clean completion, zero exit, known crash-marker checks, copied-mod restoration and supplied copied-save integrity. No save, inference or normal-profile change occurs. No native chamber/fault/unavailable relationship-view acceptance, live reassignment, broad lifecycle, production API-support inventory, provider advice or player release acceptance is claimed here.

## Reproduce and integrate

```sh
.venv/bin/python -m pytest -q test_housing_query_view.py
xvfb-run -a -s '-screen 0 1280x960x24' .venv/bin/python dev/run_housing_relations.py \
  --game-dir '/path/to/Songs of Syx' --jdk-home '/path/to/full-jdk' \
  --java '/path/to/game-compatible/java' --save runtime/smoke.save
```

Use the licensed paired game/source and disposable profile from [CONTRIBUTING.md](CONTRIBUTING.md). Candidate bundle/validation arguments are optional. Production integration must choose the actual collector/adapter placement and caching, retain these semantics and diagnostic bounds, register the field/source inventory, and validate getter/DTO/MCP, chamber/fault/scene, cost, discovery, guidance and paired player release gates. The current schema/examples are developer-only and must not be advertised as current player query paths. Broader variables, menus, immediate unload, reference and player-experience work remains active.
