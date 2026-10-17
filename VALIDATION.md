# Validation — 0.5.0 public API/context audit

## Current checks

- 37 Python tests pass: snapshot validity/freshness, demo isolation, paging, selected-data bounds, query filtering/joins/grouping/aggregation, cited source authority/version labels, and MCP transport.
- MCP transport verifies exactly nine tools, all read-only. No raw-field, screenshot or input tools are registered.
- Boundary tests check the mod namespace and reject reflection, native input/capture, process launch and engine-resource bypass patterns in production Java source. These tests supplement source review, not a complete security proof.
- Four production Java source files compile against the installed 0.71.44 JAR with Java 16 target bytecode. Detached JSON serialization tests pass.

## Rebuilt-mod copied-save test

The new 0.3.0 mod was loaded in an isolated Linux user profile using Java21 and a copied save. All 18 domains returned partial coverage. The installed-help catalog contained 720 records; a structured query ranked the 42 resource rows by stockpile storage and returned only selected IDs/values. No control mailbox was created. Original saves were not modified.

## Explicit limitations

The script lifecycle is documented in the shipped SCRIPT source and semi-official script guide. Most individual data getters are public APIs verified in shipped source, not separately documented stable contracts. API_BOUNDARY.md records that distinction. Complete state access is not claimed.

Partial public-API UI context is exported; gameplay control remains excluded. The prior native-input and private-reflection tests are historical and do not apply to this build. An 11-check copied-save scenario passed: settlement, selected subject, game menu, confirmation, world view, management overlay, encyclopedia, loading overlay, room blueprint context, save reload/session rotation, and stale/unknown status after return to the main menu. The last check does not identify main-menu subpages. A further eight scene checks passed in 0.5.0: city, settlement tactical HUD, restored city, generated battle deployment, battle menu, reloaded city, initial world creation and generated terrain. Active fighting/conclusion, complete political-world generation, editors and every menu/popup combination remain unvalidated. The earlier eleven context checks were performed with 0.4.0; the eight scene checks used the rebuilt 0.5.0 mod.

GameDisposable promises cleanup on the next game initialization. JVM shutdown also closes the exporter. Immediate return-to-menu detection is not established without an appropriate public lifecycle hook; stale state expires after 30 seconds. No large-city frame-time or cross-platform performance claim is made.

## Reproducible evidence

The production compiler audit resolved 165 public game members, with 164 shipped-source declaration matches and one generated enum member. It inventories mod references rather than every possible game variable. API_ESTABLISHMENT.md records the distinction between documented script contracts, public source-verified access and runtime checks. The context verifier completed with no missing phases; both verifier and isolated game exited with code zero. Test output/state remains local under runtime/ and is not published.

## Isolated fixture preflight

`LiveSmoke` requires an explicit state directory, an existing sibling `smoke-home` as its isolated user home, and a copied save inside that fixture root. It resolves real paths and rejects the normal user home or an original save outside the root before engine initialization. `-Dsyx.smoke.validateOnly=true` validates these boundaries without starting the engine. Fixtures are development-only and never packaged in the mod. Scene verification is implemented by `dev/verify_scenes.py`; context verification by `dev/verify_context.py`.

Three static binary checks pass for resource-owned semantics, the menu state factory and engine-disposal accessibility. They support these specific findings, not whole-SDK source/binary equivalence. The latest scene run and verifier both exited zero, with all eight required phases observed. Runtime reports and saves remain private local artifacts.
