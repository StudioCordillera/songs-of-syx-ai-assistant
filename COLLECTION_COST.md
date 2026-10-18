# Collection and selection cost baseline

COLLECTION_COST_VALIDATION.json records a native run of the exact shipped player JAR on Songs of Syx 0.71.44, followed by offline parsing and selection of its retained observation. This is a small copied-city baseline, not large-city acceptance or a performance guarantee.

## Observed results

The paused copied city had 295 entity-prefix rows, 36 scanned rooms, eight service-room rows, 544 configured service-policy rows, 35 production-flow rows, 203 regional rows and 834 installed references. All 18 domains reported partial coverage; service reads reported no truncation/failures. One sample cleared only the mod's detached help cache, then 31 warm samples followed at least 250 ms apart.

| Work | Median ms | Sample p95 ms | Maximum ms |
| --- | ---: | ---: | ---: |
| Warm game-thread collection | 4.286 | 5.507 | 7.655 |
| JSON and UTF-8 encoding | 5.059 | 6.619 | 9.320 |
| Offline snapshot parsing | 8.515 | 9.477 | 55.293 |
| Two offline service queries together | 21.456 | 22.866 | 27.962 |

The single cleared-mod-cache collection took 6.069 ms. It does not represent cold game, JVM or filesystem caches. Percentiles use sorted index floor(0.95 × (n−1)); raw samples are retained, including outliers. Host scheduling and garbage collection can affect elapsed times.

**Production encodes in its background export worker.** The fixture measures encoding on its callback thread to isolate the cost. Its combined collection/encoding median of 9.454 ms is not a measured production game-thread stall. Native timings exclude disk I/O, loading, MCP transport and model calls. Offline parsing excludes disk reads; offline query timing excludes parsing, freshness validation, MCP/status/UI envelopes and model latency.

Two service selections independently matched expected filters, nullable staffing joins, configured-policy/population joins, row ordering and total counts. Five existing selection examples also matched independent filter/join/aggregate calculations across 31 repetitions. Those five together had a 12.151 ms median offline engine time. This checks query behavior on one retained observation, not current live API availability.

The full retained snapshot was 928,493 bytes, including installed reference material. The two service results were 3,517 bytes; the five other results were 5,000 bytes. Result counts include query metadata but exclude outer MCP/status/UI context, so these sizes do not establish end-to-end network savings.

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

All 160 Python tests and release freshness checks pass. Production source and both tested ZIPs remain unchanged. Earlier player/core reports retain their historical fixture hashes; adding the profiling branch to LiveSmoke does not relabel those earlier runs. Larger settlements, cap/fault behavior, all scenes, sustained FPS and worst-case latency still require separate evidence.

The subsequent collection-diagnostics change keeps this native collector/JAR unchanged but adds Python response metadata. This report retains its original Python hashes and offline timing scope; it is not a fresh timing acceptance of that later query layer.
