# Physical home records and eligibility-weighted ledgers — candidate

This is an **unregistered developer candidate**, outside the player JAR and MCP tools. The tested weather-enabled player remains unchanged. Current housing data still exposes aggregate HOME statistics and recorded per-person home coordinates. No new player housing feature is claimed here.

`dev/candidates/housing/syx/assistant/candidate/HousingObservation.java` reads two fixed concrete types on `GAME.addAfterUpdate`: ordinary `HomeInstance` and noble `ChamberInstance`. It scans up to 10,000 current room slots and returns up to 1,000 supported home rows. IDs are reusable room slots. Service/door coordinates identify the home record's service point, not UI selection or a permanent identity. Arbitrary HOME implementations are outside this candidate's scope.

Each row contains the room/blueprint/type, service coordinates, reported occupant count, configured capacity, count provenance, ordinary-home stored odd-occupant bookkeeping, reported isolation/provenance and a bounded recorded/resolved roster. At most 64 resident IDs are copied per row. A failed roster returns unavailable/null, not an empty list; a truncated roster stays explicit. Failed room reads and incomplete slot scans qualify missing rows. The candidate reports raw configured/stored counters, not universally validated physical quantities or a whole-city vacancy census.

Ordinary `occupants()` reads a stored assignment count. `occupantsOdd()` reads a stored no-employment accounting bucket; it is not an independent current unemployment census. The availability code uses `am - amOdd`, and occupation can evict an odd jobber. A physically full recorded roster therefore does not prove no replacement is eligible. This candidate does not call `availability`, `canOccupy` or mutate assignments.

Chamber occupancy resolves a recorded entity ID into zero/one. A reported zero is not proof that the private raw ID slot is zero. Chamber capacity is constant one. Ordinary isolation is an unsigned eight-bit fraction; chamber isolation is the conditional parent-room value. Neither is full housing quality, current furnishing inventory or a freshly recomputed environment.

## Cohort ledgers do not count unique beds

`ROOM_HOME.total(group)` and `used(group)` read ordinary-home accounting arrays for citizen/slave race cohorts. `total(null)` / `used(null)` return group sums. Source accounting can add the same empty home for multiple eligible cohorts, so these sums must never be labeled physical beds, vacancy or reachable housing for a particular person. Noble chambers are separate from this ordinary-home ledger.

The copied-city fixture observes a group-capacity sum different from the sum over distinct ordinary-home capacities. Its used-group sum happens to agree with distinct recorded occupants in that fixture. These observations do not establish universal equality, exact ledger age or per-home eligibility. Incomplete physical scans or stale counters must not be repaired by forcing them to equal the group ledger.

## Excluded getters and actions

[HOUSING_BOUNDARY_REVIEW.json](HOUSING_BOUNDARY_REVIEW.json) pins public declaration anchors, selected stored/constant reader bodies and manual fixed-call-chain source review. This is shipped-source/selected-bytecode verification for 0.71.44, not a stable documented official housing API contract.

`HomeInstance.resourceAm` calls `resCount` / `unuse`, which can update resource/render timers or lighting. `use` changes light state. `OddHome.has/get` can consume stale search-queue entries. They are excluded, together with occupancy/vacancy/settings/upgrade actions and engine handles.

Policy-bit access can allocate/replace backing data, while occupied-home availability may initialize a group-specific cache. The public policy `copy` route also calls the original object's `is` getter, so it does not independently avoid that normalization. No policy handle, eligibility evaluation, serialization trick, private reflection or process-memory access is used. These selected exclusions are not proof that every possible public eligibility route is absent.

## Finite evidence

[HOUSING_CANDIDATE_VALIDATION.json](HOUSING_CANDIDATE_VALIDATION.json) records 32 unchanged paused-city samples over 36 ordinary homes, 204 resolved assigned residents and 16 cohort rows. All 204 roster links match the existing public recorded home service coordinates in that fixture. Repeated scalar/roster/cohort getters agree, and the candidate output remains unchanged across the samples. This is assignment consistency, not physical presence, sleeping, reachability or a general bidirectional-invariant guarantee.

There are **zero noble chambers in the fixture**. That branch has source/compiler/selected constant-reader evidence only; native noble occupancy acceptance remains open. Source checks also reject eight bad budget cases without initializing a game. After excluding the first sample, 31 candidate-collection intervals have median 0.183881 ms/max 0.219437 ms; output is 18,135 bytes. The interval includes slot scan, DTOs, rosters and cohort reads, excluding independent baselines/encoding. These are small-city descriptive samples, not hard-cap, large-city or FPS acceptance.

The locked disposable host requires exact game/source pairing, candidate/static-review source hashes, explicit clean completion, zero exit, known crash-marker checks, copied-mod restoration and supplied copied-save integrity. No provider request or normal-profile/save change occurs. The existing public `hCoo` scratch coordinate is immediately compared/copied inside the fixture; no engine object crosses to a DTO. Raw resident IDs, coordinates and other game rows stay in private runtime state, not this public report.

## Reproduce and next gates

Use the licensed game/source, copied `runtime/smoke.save`, isolated `runtime/smoke-home`, full JDK and compatible game Java described in CONTRIBUTING.md:

```sh
.venv/bin/python dev/review_housing_boundary.py \
  --game-dir '/path/to/Songs of Syx' --jdk-home '/path/to/full-jdk' \
  --output HOUSING_BOUNDARY_REVIEW.json
xvfb-run -a -s '-screen 0 1280x960x24' .venv/bin/python dev/run_housing_candidate.py \
  --game-dir '/path/to/Songs of Syx' --jdk-home '/path/to/full-jdk' \
  --java '/path/to/game-compatible/java' --save runtime/smoke.save
```

The wrapper uses the shared device fixture lock and explicit legacy scenario/ready-file override; it does not shadow a production housing reader. Before mapping through MCP: validate a real chamber, budget/fault/truncation and lifecycle cases; establish precise field definitions/diagnostics and consistent relationship/selection semantics; then integrate and run source-matched player release gates. Effective per-person eligibility, full furnishing/quality, permanent identities, UI-selected homes and complete game-variable/menu/reference coverage remain unestablished.
