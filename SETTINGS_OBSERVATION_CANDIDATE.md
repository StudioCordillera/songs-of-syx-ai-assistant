# Configured game settings observation candidate

This is **developer-only**, not a change to the tested player or production settings domain. The current player still exports clock/speed/time only. The candidate implements sixteen fixed public in-process settings UI observations, with source-backed ranges and explicit failure/scope metadata. [Static boundary review](SETTINGS_BOUNDARY_REVIEW.json) and [native/MCP evidence](SETTINGS_CANDIDATE_VALIDATION.json) are separate from production promotion and full settings/menu coverage.

`SettingsObservation.collect(S initialized)` accepts an already initialized game settings object. It never calls `S.get()`, `set`, `save`, `applyRuntimeConfigs`, `getValue` or `make`. The public `S.get()` accessor can lazily allocate the settings object and load files; invoking a public getter is not automatically side-effect free. Selected shipped source/binary proves that the normal `menu.Menu.start()` initializes S before CORE creation. The copied-game LiveSmoke bootstrap does likewise. This establishes ordering in those paths, not an official SCRIPT contract or a live standalone-menu observation callback.

## Fixed fields and meaning

| Candidate IDs | Configured UI range | Meaning and limit |
| --- | --- | --- |
| audio_master, audio_effects, audio_music, audio_ambience | 0..20 | Quantized audio UI steps, not raw launcher percentages or measured/effective mixer gain |
| mute_unfocused | 0..1 | Configured focus-mute preference, not actual window focus or current mute |
| shadows, particles, gore | 0..2 | Configured visual detail choices, not measured rendering load |
| graphics_detail | 0..1 | Configured map-detail choice |
| brightness | 0..20 | Quantized brightness UI steps, not monitor brightness or luminance |
| autosave_interval | 0..10 | Configured selector step; not elapsed/remaining time until a save |
| autosave_files | 1..10 | Configured retained-file count, not actual files present |
| edge_scroll, day_cycle, ui_day_cycle, visual_weather | 0..1 | Configured visual/input preferences, not current mouse position, visibility or weather state |

The percentage adapter truncates normalized launcher storage multiplied by 20. This can understate any underlying stored percentage. In particular, zero audio UI steps can conceal a positive underlying setting. **Zero steps do not prove zero mixer gain, physical silence or operating-system mute.** No protected backing value is read to fill that gap; an external compiler probe rejects it.

Each row identifies its fixed setting ID, `configured_steps`, minimum/maximum, unit and source member. Unexpected values/ranges produce a `value_or_range_mismatch` diagnostic; a null/failed getter produces `getter_unavailable`. A failed setting contributes no fabricated row/zero. If every read fails, the observation is unavailable with null data and explicit failed-setting diagnostics. Partial success retains bounded rows and a false `complete_fixed_selection` flag. A successful fixed selection still has `coverage:partial`: sixteen known UI preferences are not the complete launcher/engine settings schema.

## Validation and query scope

The reader runs on the game after-update thread in a disposable copied game. Three fixed own-view phases—city, world, city return—compare sixteen rows' values/minima/maxima with direct public getters, 144 comparisons total. The fixture changes only its own view/speed and makes no explicit settings mutation. Null-object refusal is exercised natively. Engine background writes can occur in the copied profile; no general zero-write guarantee is made.

The first callback also creates a separate retained snapshot with `/configured_options` added only to its settings data and a plainly labeled developer reason. Actual production stdio MCP performs one selective batch containing row projections and requested/complete/failure metadata, plus `describe_game_fields` discovery. Both queries retain the original observation/session/UI context. The production export mailbox, tool set and getter inventory are unchanged. The reader is not installed in the player's callback, and the static audit still inventories the existing production references separately.

For a candidate-augmented observation, the source paths are:

- `settings /configured_options/data/rows`: select `/setting_id`, `/configured_steps`, `/minimum_steps`, `/maximum_steps`.
- `settings /configured_options/data`: select `/requested_settings`, `/complete_fixed_selection`, `/failed_settings` in the same batch.

These paths do not exist in ordinary production observations. Discover fields before querying; null/unavailable or failed reads are not zero/false.

A detached Java test compiles against own minimal stubs that deliberately have no lazy accessor, setters or save/apply methods. It checks all sixteen accepted endpoint ranges, out-of-range values, changed ranges, invalid indices, per-field null/throw failures, typed diagnostics and all-failed/null-object refusal. This is DTO/failure logic evidence, not licensed API accessibility or native fault injection. Separate licensed compiler probes establish the real public field/get/min/max routes and rejected protected access. Selected disassembly hashes cover the ordinary and percentage getter bodies; source hashes/anchors pin all field declarations and the bootstrap path. No reflection, process memory, screenshots, input hooks or OS automation is used.

Local authenticated Claude Code completed a bounded tool-free **Opus 5.5/high** source critique before the diagnostic/all-failed refinements. Accepted findings are the distinction between source-range mismatch and runtime getter failure, and avoiding available data when all reads fail. The suggested complete coverage flag was not adopted: fixed-selection completeness remains separate from whole-settings coverage. `StateCollector.object` permits null through its LinkedHashMap implementation, confirmed by native null-object refusal. Off-version linkage errors are not evidence of supported-version failure: the runner rejects nonmatching source/binary hashes, and this candidate claims only the pinned build. Native failure injection, full transitive side-effect/cost proof and cross-version compatibility remain open. Invocation/source/final-text hashes and actual outcome are in [the collaboration record](CLAUDE_UX_COLLABORATION.json).

Reproduce the source review with `dev/review_settings_boundary.py --game-dir ... --jdk-home ... --output SETTINGS_BOUNDARY_REVIEW.json`. Run `dev/run_settings_candidate.py` with the licensed copied-game paths described in [CONTRIBUTING.md](CONTRIBUTING.md); the runner owns the shared native lock, verifies pairing and requires three-phase clean completion plus copied-mod/save restoration. No provider key is used. The first packaging attempt failed compilation before game startup because the fixture shim was placed in the wrong package; it is corrected and excluded from passing evidence.

Next: review production integration and startup/scene coverage, map other useful variables/UI contexts, and complete paired native/core/actual-Pro/distribution gates before player promotion. The goal remains broader than these sixteen preferences; no full variable/menu coverage or live main-menu detection is claimed. The latest/previous tested player bundles stay unchanged.
