# Collection and selection cost baselines

## Current published collector — small copied city

[CURRENT_COLLECTION_COST_VALIDATION.json](CURRENT_COLLECTION_COST_VALIDATION.json) measures the live-regional player JAR (`61f88110b48d65add52e94bef3becccac18dde7e52cbd56b4678f3b9521f2ff0`), including the current producer-degradation and stockpile-bookkeeping collector. The game/source hashes match the public API audit. The paused copied city has 295 entity-prefix rows, 36 scanned rooms, eight service rooms, 544 configured service-policy rows, 35 production flows, 203 regions, 42 stockpile resource rows and 834 installed references. Stockpile reads scan all 42 resources without failures/truncation. The regional-output table contains 8,526 cells and 42 schedules, with no resource/cell failures or truncation; all 18 domains remain partial. The snapshot stays below the MCP input bound of 16 MiB in this finite fixture.

| Work | Median ms | Sample p95 ms | Maximum ms |
| --- | ---: | ---: | ---: |
| Warm game-thread collection | 6.317 | 8.594 | 12.157 |
| JSON and UTF-8 encoding | 10.446 | 16.102 | 17.829 |
| Offline snapshot parsing | 21.542 | 25.955 | 76.294 |
| Two offline service queries together | 40.455 | 44.801 | 54.720 |
| Offline regional accrual/region/schedule query | 111.999 | 119.650 | 155.834 |

There are 31 warm samples and one cleared-mod-help-cache sample; the latter collection takes 10.976 ms. Production encodes on its background worker. The fixture's combined median of 17.390 ms measures collection plus encoding on its callback thread and is **not** a measured production game-thread stall. The retained snapshot is 1,797,402 bytes; the two service selections are 4,818 bytes before outer envelopes. Independent service-query parity, five existing selection examples and the regional accrual/region/schedule query pass. The regional query is timed separately for 31 repetitions, excluding parsing and transport. Raw timing samples and descriptive percentile methodology are retained in the report.

These are local descriptive elapsed timings, including host/GC noise. Differences from the historical run below cannot isolate the cost of any added getter: they are separate runs, not a controlled comparison. They establish neither a regression threshold nor large-city/FPS/worst-case acceptance. This run does not time live entity/tile/regional requests, retained capture creation/paging or the world-view faction-panel scan; the copied fixture is paused in its city. Source hashes, actual observation timestamp, zero game exit code, restored copied-profile mod and unchanged copied save are recorded; no provider inference occurs.

Use the reproduction command below for the currently published build. The runner now rejects a mismatched licensed game/source pair, strips provider credentials case-insensitively, validates copied paths, backs up/restores only its copied mod JAR on success or failure and refuses a passing final report if copied-save integrity fails. Its private runtime directory is owner-only. Five offline regressions cover success, fixture failure, changed-save detection and direct/parent symlink escapes. The native fixture runs under the shared machine-wide lock and may be wrapped in `LIBGL_ALWAYS_SOFTWARE=1 xvfb-run -a -s '-screen 0 1280x960x24'` on this host. Normal saves and normal-profile mod files are untouched.

## Historical workforce-factor build

COLLECTION_COST_VALIDATION.json records a native run of the workforce-factor player JAR (`153f37ee51cb47c38ea568c589e3a642c43e1cfaf1a7911070730da0eacb2b1e`) on Songs of Syx 0.71.44, followed by offline parsing and selection of its retained observation. This is a small copied-city baseline, not large-city acceptance or a performance guarantee.

## Observed results

The paused copied city had 295 entity-prefix rows, 36 scanned rooms, 31 employing-room rows with work factors, eight service-room rows, 544 configured service-policy rows, 35 production-flow rows, 203 regional rows and 834 installed references. All 18 domains reported partial coverage; service reads reported no truncation/failures. One sample cleared only the mod's detached help cache, then 31 warm samples followed at least 250 ms apart.

| Work | Median ms | Sample p95 ms | Maximum ms |
| --- | ---: | ---: | ---: |
| Warm game-thread collection | 4.098 | 5.181 | 5.440 |
| JSON and UTF-8 encoding | 4.916 | 5.702 | 7.400 |
| Offline snapshot parsing | 8.857 | 11.934 | 14.201 |
| Two offline service queries together | 22.177 | 23.096 | 66.142 |

The single cleared-mod-cache collection took 5.800 ms. It does not represent cold game, JVM or filesystem caches. Percentiles use sorted index floor(0.95 × (n−1)); raw samples are retained, including outliers. Host scheduling and garbage collection can affect elapsed times.

**Production encodes in its background export worker.** The fixture measures encoding on its callback thread to isolate the cost. Its combined collection/encoding median of 9.018 ms is not a measured production game-thread stall. Native timings exclude disk I/O, loading, MCP transport and model calls. Offline parsing excludes disk reads; offline query timing excludes parsing, freshness validation, MCP/status/UI envelopes and model latency.

Two service selections independently matched expected filters, nullable staffing joins, configured-policy/population joins, row ordering and total counts. Five existing selection examples also matched independent filter/join/aggregate calculations across 31 repetitions. Those five together had a 12.259 ms median offline engine time. This checks query behavior on one retained observation, not current live API availability.

The full retained snapshot was 935,490 bytes, including installed reference material. The two service results were 4,818 bytes; the five other results were 6,782 bytes. Result counts include query metadata but exclude outer MCP/status/UI context, so these sizes do not establish end-to-end network savings.

## Reproduction and evidence boundary

```sh
.venv/bin/python dev/profile_collection_cost.py \
  --game-dir '/run/media/kali/New Volume/SteamLibrary/steamapps/common/Songs of Syx' \
  --save runtime/smoke.save \
  --java .tools/java21/usr/lib/jvm/java-21-openjdk-amd64/bin/java \
  --jdk-home .tools/jdk/usr/lib/jvm/java-25-openjdk-amd64
```

The runner requires the licensed installation and existing isolated smoke profile/copied save. It extracts and hash-checks the tested JAR, compiles development fixtures, strips provider credentials from the child environment, validates fixture paths, pauses the copied game using the public speed API and exits after verification. No inference requests or save writes occur. Collection uses the production collector's public entry point. Clearing the mod's detached help cache changes no game setting.

The last observation retains its real timestamp and a separate profiling session/sequence. It is private runtime evidence, never substituted for the active bridge snapshot. Only timing/shape metadata and hashes are published; game binaries, saves, DTO values and installed help text are not published. The report pins fixture, query, production Java and Python source hashes and a zero game exit code.

All 168 Python tests and player release freshness checks pass for the workforce build. This run measures the workforce-factor collector/JAR and Python hashes recorded in the report; earlier measurements remain historical evidence in Git. An additional offline check of the SHA-matching retained observation confirms 31 employing-room rows with factors and no employment read failures/truncation. No timestamp is refreshed by this check. Larger settlements, cap/fault behavior, all scenes, sustained FPS and worst-case latency still require separate evidence.


The subsequent workplace-filter checkpoint changes on-demand entity selection, not `StateCollector`. Its JAR and paired Python hashes differ. The timing report retains the earlier whole-build hashes and is not relabeled as a new benchmark. Workplace-filter correctness evidence does not establish its cost in a large city.


The later producer-degradation checkpoint changes `StateCollector` itself. These older measurements are not timings of that new collector/JAR. Correctness and bounded reads are checked separately, with no refreshed performance or large-city claim.


The subsequent city stockpile-bookkeeping collector adds bounded stored/reservation reads. This older timing report is not a benchmark of that collector/JAR; the new checkpoint establishes finite correctness and scene availability, not refreshed collection or large-city latency.

## Automatic-connection player checkpoint

CURRENT_COLLECTION_COST_VALIDATION.json pins JAR 73b44c55… and its paired production/Python source to 31 warm paused-small-city samples: collection median 6.199 ms, maximum 10.987 ms; separate JSON/UTF-8 encoding median 11.391 ms, maximum 13.320 ms. The observation is 1,798,020 bytes. Copied-mod restoration, copied-save integrity and finite crash checks pass. These descriptive samples do not demonstrate a speed improvement, largest-city/world behavior, optional request cost or FPS acceptance. Earlier timings retain their own hashes/scope.
