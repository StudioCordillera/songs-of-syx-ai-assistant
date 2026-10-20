# Housing selective-query integration — developer candidate

The housing reader is still unregistered. No new player field/tool or gameplay action is shipped. [HOUSING_CANDIDATE.md](HOUSING_CANDIDATE.md) describes its source, units, room/roster/ledger scope and separate native chamber/scene/fault evidence.

[HOUSING_QUERY_CANDIDATE_VALIDATION.json](HOUSING_QUERY_CANDIDATE_VALIDATION.json) adds actual stdio MCP checks over a developer-augmented native observation. The fixture calls the current production collector and unchanged housing reader synchronously in one public after-update callback, appends only detached candidate DTOs to its own detached snapshot, and writes that private observation. A separate retained directory serves it through the unchanged MCP/query implementation with the original snapshot/session/UI context. No candidate data is spliced into an older observation or the live player's mailbox. This is a test seam, not existing production housing support.

The five actual MCP calls establish:

- Observed-shape discovery can locate candidate home rows and attributes. This is not authoritative field-meaning or public-contract discovery.
- One pinned batch matches independent native-row expectations for grouped home-kind counts, reported-assignment sums, configured-capacity sums, and filtered/projected/sorted occupied-home rows. Sums describe only observed rows and their source scope; configured capacity does not establish reachable vacancy.
- The batch returns the original UI context and session. A different snapshot pin is refused.
- A raw data-node query preserves the full candidate diagnostics. This is distinct from selective-query metadata propagation.
- A deliberately one-row native scan result produces a count of one through the real selective engine, but its metadata omits seven housing-specific diagnostics.

## Demonstrated integration gap

The existing selective collector-diagnostic allowlist retains `row_limit`, while omitting `room_slots_scanned`, `room_map_size`, `scan_limit`, `room_scan_complete`, `failed_room_reads`, `failed_rosters` and `truncated_rosters`. The candidate data itself retains these values; selective result metadata does not. A one-row count alone cannot establish that the current registry scan stopped early. Partial coverage and a configured row limit do not replace the actual scan/failure/truncation values.

This is a failed **production readiness condition**, deliberately recorded as `production_integration_ready=false` and `select_diagnostics_complete=false`. The report's `passed=true` means the experiment reproduced its asserted positive and negative findings; it does not override those conditions or approve promotion. Asking callers always to fetch the entire raw candidate is not an accepted fix.

## Next production change and gates

1. Preserve housing's named scan/room/roster diagnostic semantics in selective source metadata. Use a fixed reviewed scalar allowlist or an equally explicit schema; do not export arbitrary descendants, errors, rows or engine handles. Verify capped and failed-room selections retain the correct scope and diagnostics, including joins/aggregates.
2. Define the production home and cohort-ledger envelopes, field meanings, units and source anchors. Keep ordinary stored assignment counts distinct from chamber resolved-ID counts. Unknown eligibility, resource use, exact age, permanent identity and UI selection stay explicit. Null is unavailable; zero must remain an observed zero. The existing group-null cohort sums are eligibility-weighted ledgers, not unique beds or vacancy.
3. Decide the queryable resident relationship table/representation and its bounds without inventing entity-prefix completeness or merging observations. The current nested roster can be returned, but the query engine does not automatically expand its IDs into a join table. This candidate does not claim person/home joins or current physical presence.
4. Integrate the reviewed mapping into production and validate actual getter/DTO/MCP parity in city, controlled chamber/fault cases and real scene transitions. Rerun affected audit, discovery, guidance, cost, offline, explicit Pro, core and fresh distribution gates against the exact source/JAR. Promote once with the real predecessor retained. Full variables/menu coverage remains open.

The [authored candidate example](housing-query-candidate-example.json) uses provisional `/physical_home_candidate/data/rooms` paths. It is executable only against the augmented developer observation; it must not be advertised as a current player query. No new guide citation, model recommendation, provider integration or official stability promise is implied.

## Reproduce

Use the licensed paired game/source, disposable copied save/profile, full JDK and game-compatible Java described in [CONTRIBUTING.md](CONTRIBUTING.md):

```sh
xvfb-run -a -s '-screen 0 1280x960x24' .venv/bin/python dev/run_housing_query_candidate.py \
  --game-dir '/path/to/Songs of Syx' --jdk-home '/path/to/full-jdk' \
  --java '/path/to/game-compatible/java' --save runtime/smoke.save
```

The runner uses the shared device lock and requires source/binary pairing, exact candidate/reviewer hashes, explicit clean completion, zero exit, known crash-marker checks, copied-mod restoration and supplied copied-save integrity. No housing mutation, inference or normal-profile change occurs. One paused 36-home/204-assignment city does not validate chamber-specific queries, fault-query metadata, broad lifecycle/cap/load cases or provider advice. Those remain separate gates.
