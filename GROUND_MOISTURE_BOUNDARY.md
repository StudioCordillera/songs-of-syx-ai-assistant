# Stored tile moisture: prior candidate review

Two public in-process readers are now source/binary reviewed and exercised in a disposable copied city. This historical candidate checkpoint preceded the production mapping in [GROUND_MOISTURE.md](GROUND_MOISTURE.md). Its report preserves its own source/JAR scope; native candidate agreement alone did not establish MCP exposure.

| Public route | Established meaning | Important limits |
| --- | --- | --- |
| `SETT.GROUND().MOISTURE_BASE.get(x,y)` | Stored four-bit base tile moisture multiplied by 1/15 | Quantized fraction 0..1, not unquantized soil water, precipitation, fertility or yield. |
| `SETT.GROUND().MOISTURE_CURRENT.get(x,y)` | Separate stored four-bit current tile moisture multiplied by 1/15 | The engine adjusts this toward a clamped base-plus-water target, one raw step per adjust call. Exact age, convergence and update cadence are not established. |

These are shipped-source/binary verified public accessors, not separately documented stable mod contracts. Runtime code invokes public `MAP_DOUBLE.get` methods; it never names anonymous implementation classes, accesses their storage or calls setters. The anonymous readers and private storage declarations are inspected statically to establish meaning, as distinct from runtime access.

The coordinate wrappers return zero outside the map. A future adapter must validate instantiated-scene bounds before querying them: zero cannot distinguish valid dry terrain from an invalid coordinate. Do not infer a valid tile from getter success alone. Both maps use the current instantiated settlement scene, which is not automatically the city the user means during a battle or a transition.

`MOISTURE_TOT` is a different derived expression: base plus twice an environmental sweet-water value, without a final clamp in that expression. It calls the broader environmental reader and is excluded from this candidate route. Weather precipitation and its growth factor are separate again. This review does not expose environmental water, rainfall, crop/pasture yield, irrigation requirements, placement eligibility or forecasts. Do not rename any of these values “fertility.”

## Static and runtime evidence

[GROUND_MOISTURE_BOUNDARY_REVIEW.json](GROUND_MOISTURE_BOUNDARY_REVIEW.json) pins the licensed source/JAR pair, retained declaration catalog, positive external-package compiler probe and selected disassembly hashes. Direct checks reject heap writes, allocations and backward branches; the inspected chain includes base/current coordinate and linear readers, packed storage reads, bounds dispatch and rectangle accessors. This is a finite pinned implementation review, not formal whole-game purity, stability or third-party override acceptance. Source bodies are not redistributed.

[GROUND_MOISTURE_READER_VALIDATION.json](GROUND_MOISTURE_READER_VALIDATION.json) records 4,096 distinct coordinates on a uniformly spaced 64×64 grid spanning a 768×768 copied map, over 64 native samples. The 524,288 coordinate/linear comparisons agree; both stored maps naturally exhibit all sixteen quantized values, and 49 sampled tiles have different base/current values. All sampled values remain unchanged over this paused test. Four out-of-map probes confirm the zero default. No moisture, weather or irrigation value is written, and no game is saved.

The two overloads share the same backing implementation; their agreement is **not independent validation against private raw storage**. Four actual MCP calls independently check the unchanged terrain endpoint at sampled map corners and the expected session/scene. They do not return or validate moisture via MCP. The candidate report marks `moisture_mcp_calls: 0` explicitly.

For 8,192 coordinate getter calls per timed loop, the 63 subsequent samples have median 0.118 ms, p95 0.664 ms and maximum 4.029 ms. The first sample is 2.143 ms, not a cold-JVM benchmark. Timings include loop/preallocated array stores and exclude overload comparisons, DTO/JSON construction, requests, transport and the model. They are not full collector, large-map, concurrent-load, FPS or latency guarantees. All-state/cap/fault behavior and natural moisture evolution remain unvalidated.

The runner requires paired current review, the shared native fixture lock, copied save/profile paths, a clean completion marker, no known engine crash/failure markers, restoration of the copied mod and unchanged copied save. The finite marker checks supplement process exit, not detection of every possible engine failure. Production source, simple Pro interface, latest/previous ZIPs and their provider evidence remain unchanged. The developer follow-up passes 302 offline tests without paid inference.

## Next production acceptance

Add a fixed optional tile projection such as `ground_moisture` with separate base/current fractions and these exact limits. Preserve current tile scan/row/byte bounds, existing request compatibility, detached update-thread reads, per-field errors and scene/session provenance. Do not add either field to every default snapshot or use raw declaration invocation.

Before shipping it, audit the new public references, test actual live-tile and retained-capture MCP value parity, reject invalid coordinates, exercise additional instantiated/unavailable scenes, and verify budgets/failure behavior. Run the required current-build core/Pro/distribution gates and promote a source-matching candidate while retaining the previous tested ZIP. The candidate-only report is not proof these steps happened. The subsequent production guide and exact-hash reports record their own acceptance.

## Reproduce

Use licensed game/JDK paths and copied-save setup from [CONTRIBUTING.md](CONTRIBUTING.md):

```sh
.venv/bin/python dev/review_ground_moisture.py \
  --game-dir "$SYX_GAME_DIR" --jdk-home "$SYX_JAVA_HOME"
.venv/bin/python dev/run_read_fixture.py --case ground-moisture \
  --game-dir "$SYX_GAME_DIR" --save runtime/smoke.save \
  --java "$SYX_GAME_JAVA" --jdk-home "$SYX_JAVA_HOME"
```

The static review never initializes game classes. The native fixture uses only public in-process methods in a path-validated disposable profile. It does not use screenshots, reflection, process memory, native input or provider inference. Raw sampled values/logs remain private under ignored `runtime/`.
