# Current handoff

Use `python3 dev/collaboration_status.py` for actual remote/local state at every run; this file is a handoff, not a live branch/working-tree assertion. Read AGENTS.md and reconcile newer collaborator work before editing.

## Latest production checkpoint

The stockpile-bookkeeping checkpoint adds `resources /stockpile_bookkeeping/rows`: five bounded city-wide counters for assigned crates, stored items, assigned capacity, reserved stored goods and reserved incoming capacity. Existing `owned` and warehouse-total fields retain their meanings. USER_TEST_VALIDATION.json and releases/latest-user-test.json identify exact payload hashes; do not infer coverage from the package version string alone.

The checkpoint records 206 Python tests, two actual Pro turns, seven native core groups, eight sampled supported capability probes plus two explicit gaps, and 37 guidance cases. Forty-two resources in one copied warehouse match public getters and actual MCP reservation joins/sorting/zero-capacity counts. Positive incoming/stored reservations and 33 zero-capacity resources are observed. Battle/setup bookkeeping is unavailable and selective counts refuse it. Per-room arrays remain fixture-only; actual cap/fault execution, large-city cost, removal/inactive-time behavior and complete logistics remain open. Static inventory: 364 public production references, zero non-public references; this is not a variable-coverage percentage.

The simple Pro interface is preserved and the tested predecessor retained. Normal-profile mod files are not replaced while the user's game is running; install the new tested bundle and restart to use the new counters. A future run may update only our own installed mod once the game is closed, preserving profile backups and saves.

## Collaboration follow-up

Claude runs on the same local device. Separate checkouts and a shared advisory native-fixture lock coordinate concurrent work. Shared AGENTS/CLAUDE instructions, portable contributor tests, repository/documentation maps, remote-drift/overlap reporting and an explicit Pro test runner using the ignored local .env (--env-file .env) are now provided. Current guides distinguish delivered simple chat from deferred/older provider experiments. COLLABORATION_VALIDATION.json records developer-tool/docs follow-up; the unchanged player payload keeps its own prior test count and evidence. These earlier collaboration additions did not change application source; subsequent production checkpoints have separate evidence.

## Next useful core work

1. Retained bounded spatial selections: live tile pages currently observe different moments. Preserve strict caps, original context/session and explicit incomplete-selection failure as with entities.
2. Larger representative copied settlements and other room/service/world cap/fault cases. Existing small-city timings retain older collector hashes and do not establish the current collector's large-city cost.
3. Broader reviewed current-version reference coverage around food, services, storage/logistics and production; retain exact supporting passages/authority/version caveats and evaluate representative player questions.
4. Storage/logistics candidate review is now recorded in STOCKPILE_BOUNDARY.md and STOCKPILE_BOUNDARY_REVIEW.json: five public stored tallies, distinct reservation/zero-capacity semantics and a scratch-handle exclusion. STOCKPILE_READER_VALIDATION.json now adds a finite 42-resource/one-room copied-city check: 420 overload comparisons, per-room/global sums, naturally nonzero incoming/stored reservations, 33 zero-capacity resources and controlled immediate deactivation/reactivation. Existing production stored/capacity fields pass actual retained-observation MCP selection parity. The subsequent STOCKPILE_BOOKKEEPING.md / STOCKPILE_BOOKKEEPING_VALIDATION.json maps bounded global reservation counters with actual DTO/MCP parity and unavailable battle/setup checks; per-room arrays remain fixture-only. Next, validate actual caps/faults, other lifecycle cases and cost before extending per-room exposure. The earlier reader report keeps its original JAR/source scope. Additional useful typed production/resource/world relationships still require public route, meaning/units/thread/cost review. Do not expose generic production helpers or turn the declaration catalog into an invocation API.
5. Missing UI accessors: exact selected room, tooltips/tab hierarchy and immediate unload-to-menu hook remain unestablished. Preserve same-observation context and the up-to-30-second freshness limitation.

Provider/account/sign-in expansion remains deferred. Keep the simple Pro client, stable tested download, previous bundle, credentials and normal saves. Do not claim all variables/menus or completion of the roadmap. Update this handoff when priorities, delivered behavior or decisive evidence change; fetch before assuming another agent has not already implemented the next item.
