# Collection and selection cost baseline

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
