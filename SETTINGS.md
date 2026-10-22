# Source-verified configured game settings

The production collector adds sixteen fixed configured UI-setting rows under `settings /configured_options`. These supplement the existing clock/speed fields. [Public-API boundary review](SETTINGS_BOUNDARY_REVIEW.json), [paired production evidence](SETTINGS_VALIDATION.json) and [tested player evidence](USER_TEST_VALIDATION.json) pin the implementation and test scope. Earlier [candidate evidence](SETTINGS_OBSERVATION_CANDIDATE.md) remains historical.

| Setting IDs | UI-step range | Established meaning |
| --- | --- | --- |
| audio_master, audio_effects, audio_music, audio_ambience | 0..20 | Quantized configured audio UI steps |
| mute_unfocused | 0..1 | Configured focus-mute preference |
| shadows, particles, gore | 0..2 | Configured visual detail choice |
| graphics_detail | 0..1 | Configured map-detail choice |
| brightness | 0..20 | Quantized brightness UI step |
| autosave_interval | 0..10 | Autosave selector step, without a time-to-save prediction |
| autosave_files | 1..10 | Configured retained-file count |
| edge_scroll, day_cycle, ui_day_cycle, visual_weather | 0..1 | Configured input/visual preferences |

Audio/brightness adapters truncate the normalized stored value multiplied by 20. A UI step can understate the underlying stored percentage; zero steps can conceal a positive audio setting. **Do not infer zero mixer gain, operating-system mute, physical audibility, current window focus, effective rendering or autosave ETA.** The exporter does not access the protected backing setting, measure device output or provide setters.

Rows contain `setting_id`, `configured_steps`, `minimum_steps`, `maximum_steps`, `unit` and source-member text. `requested_settings=16`, `complete_fixed_selection` and `failed_settings` describe the fixed selection. A changed value/range is distinguished from a null/failed getter. Failed settings produce no zero/false placeholder. All-failed or missing-object observations have unavailable coverage and null data. Partial success retains only valid rows; complete fixed-selection success still has partial coverage because the whole launcher/engine settings schema is larger.

[The query example](settings-query-example.json) selects row values/ranges and their completeness/failure metadata in one `select_game_state` batch with the same UI context. Add a `/setting_id` predicate and a smaller limit when only one option is needed. Discover fields first. An absent/failed row is unknown, not a disabled preference. `get_game_api_support` exposes the `configured_game_ui_settings` capability and compiler/source anchors even without a game observation; that metadata does not attest a separately installed mod.

## Thread, initialization and lifecycle

The reader accepts an already initialized `S` object and calls only the fixed public settings `get/min/max` methods on the game after-update thread. The caller obtains the singleton in that established runtime. Shipped `menu.Menu.start()` and the copied-game bootstrap initialize it before CORE creation; source/binary fingerprints verify this ordering. The singleton accessor itself can lazily initialize/load files, so it is not advertised as an unconditional pure reader. This is **shipped-source verification for 0.71.44**, not an official documented SCRIPT settings contract or cross-version promise.

These preferences are game-process configuration observed in a particular snapshot. They do not identify the currently selected settings tab, a permanent world/save, or a standalone main-menu lifecycle state. Existing return-to-menu freshness/unknown-state limits still apply. No reflection, private backing access, screenshots, input hooks, OS automation or gameplay command is used by the mapping.

## Evidence and limits

The feature-specific fixture uses the exact paid production JAR, asserts active city/world/city-return views, compares 144 values/minima/maxima with direct getters and verifies that the normal production snapshot already contains the observation. No settings are inserted by the fixture. Actual stdio MCP checks the published query example and field discovery against a retained native snapshot with original session/UI context. The retained read is not a new game-thread callback or global transaction.

Detached tests exercise both candidate and production namespaces with minimal stubs that omit lazy initialization/set/save/apply methods. They cover accepted endpoints, invalid indices/values/ranges, individual getter/null failures and all-failed/null-object refusal. Those failures are not native fault injection. Selected disassembly/compiler probes establish public routes and reject protected raw access; no complete transitive side-effect/cost or all-menu proof is claimed.

Two real native Pro turns include selective resource/settings reads, an audio-step quantization caveat and retrieved guide citations. The settings verifier checks source/session/value agreement with the retained first-answer observation and caveat terms, not comprehensive semantic entailment or cross-tick atomicity. A separate two-turn production-reference Pro check uses a synthetic demo context. Core scene/UI/lifecycle, connection/focus, guidance/discovery, finite collection cost and fresh extracted distribution gates have distinct evidence in the paired report. They do not establish physical keyboard/display/audio, every menu, large-city performance or full game-variable coverage.

The final published archive has a separate extracted-distribution check in [SETTINGS_FINAL_DISTRIBUTION_VALIDATION.json](SETTINGS_FINAL_DISTRIBUTION_VALIDATION.json). The aggregate report contains the earlier passing payload check; the final report pins the published container hash without a self-referential BUILD hash. Every payload byte must agree across these stages.

The prior tested player ZIP is retained during promotion. The simple DeepSeek Pro interface and read-only tool set remain; provider/account expansion and gameplay commands stay deferred.
