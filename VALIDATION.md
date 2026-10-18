# Validation — 0.12.0 public API/context audit

## Current checks

- 90 Python tests pass: snapshot validity/freshness, demo isolation, paging, selected-data bounds, query filtering/joins/grouping/aggregation, cited source authority/version labels, and MCP transport.
- MCP transport verifies exactly thirteen tools, all read-only. No raw-field, screenshot or input tools are registered.
- Boundary tests check the mod namespace and reject reflection, native input/capture, process launch and engine-resource bypass patterns in production Java source. These tests supplement source review, not a complete security proof.
- Seven production Java source files compile against the installed 0.71.44 JAR with Java 16 target bytecode. Detached JSON serialization tests pass.

## Rebuilt-mod copied-save test

The new 0.3.0 mod was loaded in an isolated Linux user profile using Java21 and a copied save. All 18 domains returned partial coverage. The installed-help catalog contained 720 records; a structured query ranked the 42 resource rows by stockpile storage and returned only selected IDs/values. No control mailbox was created. Original saves were not modified.

## Explicit limitations

The script lifecycle is documented in the shipped SCRIPT source and semi-official script guide. Most individual data getters are public APIs verified in shipped source, not separately documented stable contracts. API_BOUNDARY.md records that distinction. Complete state access is not claimed.

Partial public-API UI context is exported; gameplay control remains excluded. The prior native-input and private-reflection tests are historical and do not apply to this build. An 11-check copied-save scenario passed: settlement, selected subject, game menu, confirmation, world view, management overlay, encyclopedia, loading overlay, room blueprint context, save reload/session rotation, and stale/unknown status after return to the main menu. The last check does not identify main-menu subpages. A further eight scene checks passed in 0.5.0: city, settlement tactical HUD, restored city, generated battle deployment, battle menu, reloaded city, initial world creation and generated terrain. The 0.9.0 fixture below adds sampled engagement and controlled victory/defeat paths. Natural campaign resolution, complete political-world generation, full editor workflows and every menu/popup combination remain unvalidated. The eleven context checks were run with 0.6.0. The eight scene checks and larger entity fixture were run with 0.7.0. The 0.8.0 extended fixture covers sixteen UI/editor/retreat phases.

GameDisposable promises cleanup on the next game initialization. JVM shutdown also closes the exporter. Immediate return-to-menu detection is not established without an appropriate public lifecycle hook; stale state expires after 30 seconds. No large-city frame-time or cross-platform performance claim is made.

## Reproducible evidence

The production compiler audit resolved 246 public game members, with 245 shipped-source declaration matches and one generated enum member. It inventories mod references rather than every possible game variable. API_ESTABLISHMENT.md records the distinction between documented script contracts, public source-verified access and runtime checks. The context verifier completed with no missing phases; both verifier and isolated game exited with code zero. Test output/state remains local under runtime/ and is not published.

## Isolated fixture preflight

`LiveSmoke` requires an explicit state directory, an existing sibling `smoke-home` as its isolated user home, and a copied save inside that fixture root. It resolves real paths and rejects the normal user home or an original save outside the root before engine initialization. `-Dsyx.smoke.validateOnly=true` validates these boundaries without starting the engine. Fixtures are development-only and never packaged in the mod. Scene verification is implemented by `dev/verify_scenes.py`; context verification by `dev/verify_context.py`.

Four static binary checks pass for public after-update dispatch, resource-owned semantics, the menu state factory and engine-disposal accessibility. They support these specific findings, not whole-SDK source/binary equivalence. The latest scene run and verifier both exited zero, with all eight required phases observed. Runtime reports and saves remain private local artifacts.

## Individual data and description retrieval — 0.6.0

The copied-save fixture selects the last live humanoid in its entity traversal, rather than relying on the first entity. It verifies identity agreement between UI context and the dedicated entities.selected_subject export, then filters/projects individual stat rows through the same-snapshot query engine. This save has 295 entities and exports 58 named individual statistics. A separate MCP transport check retrieves an exact installed stat description from the 720-record catalog. The 0.7.0 fixture below adds over-1,000-entity coverage. All individual getter implementations and large-city performance remain unvalidated.

## On-demand entity fixture — 0.7.0

56 Python tests pass, including fixed selection validation, Unicode-safe protocol framing, concurrent-client locking, demo/stale refusal, response identity/freshness/size checks, and timeouts with lock reuse. The development Java codec test accepts a valid request and rejects eleven malformed/unsupported requests without initializing game state.

The first exploratory live run exposed a wrong fixture assumption: a target can be in a high scene-array slot even with a small population. The failed verifier stopped; its owned game process was terminated before rebuilding. The corrected production path uses public getByID for explicit IDs, while general scans retain bounded cursors. The successful rerun and verifier both exited zero. It used 1,395 temporary entities and a target in slot 59,999 outside the exported prefix; all identities remain private runtime data. All 1,395 IDs were traversed once in 18 pages in the paused fixture. Combined predicates, stat values and references, exact ID lookup, unknown-stat rejection and concurrent MCP requests passed. The target/selection/population remained unchanged by reads. Temporary citizens were never saved.

The scene verifier's `--on-demand` mode checks reads in city, tactical city HUD, generated battlefield deployment, battle menu and reloaded city. Initial world creation and generated terrain must return an explicit no-instantiated-scene error. This does not establish active fighting, battle completion, full world creation, every menu or large-city performance.

## Extended UI/editor/retreat fixture — 0.8.0

The extended fixture verifies sixteen phases through game APIs in an isolated copied game. Public popup/section content checks cover nested text, switches, control flags, hidden labels, repeated references and the node/text/depth budgets. Opaque button labels and private text-input values are not exported. A real MCP call retrieves mapped popup content. Editor activation is checked on a copied completed world, including the persistent editing flag after switching to city. A generated battle retreats through the public BattleState path; the fixture's exiter checks RETREAT and the restored city has a new session. On-demand reads are also checked in both editors and after retreat.

The previous 0.7.0 scene/entity fixtures and 0.6.0 full context matrix are retained as version-scoped evidence. The 0.8.0 fixture did not rerun every older phase as one combined scenario. It uses game widgets it constructs; every native dialog, private-wrapper text, full editor/world workflows and cross-platform/performance behavior remain unvalidated. Its battle scope is deployment/retreat; the 0.9.0 fixture below adds sampled engagement and controlled result paths.

## Running-battle and controlled result fixture — 0.9.0

Nine required phases pass in a copied game: city, deployment/engagement/result/restoration for controlled victory, and deployment/engagement/result/restoration for controlled defeat. Each army begins with one forty-person division. The public game manager dispatches Start and Close; public melee orders produce observed engine engagement. Test-only public casualty calls then set up deterministic result paths. This is not a natural-outcome or battle-AI benchmark.

The actual private result overlays are closed through the normal public dispatcher using a public layout reference; the fixture's exiter checks each outcome and new session after restoration. Production result getters are not invented. Exports retain the private-overlay unsupported reason and show global hover consumption despite all known overlay flags being false. The initial clean trial informed clearer stale-buffer wording; the final packaged trial checks that wording too. These are public in-process UI calls, with no OS/native input, screenshots or private object reads.

The 0.8.0 extended-context, 0.7.0 scene/entity and 0.6.0 context fixtures remain version-scoped evidence. Natural campaign resolution, every combat condition/result workflow, complete public field coverage, full world/editor workflows and large-city performance remain unvalidated. Source boundary tests additionally reject the fixture's concrete control-call patterns in production.

## Offline public-declaration discovery

The discovery extension passes an independent compiled synthetic API fixture; that initial release had 57 passing Python tests. The installed-game scan resolves 2,052 public types / 17,442 declared public members from 2,443 shipped source files, with all 246 production references present. API_DISCOVERY.json contains hashes/counts, and API_DISCOVERY.md records the scope and missing source-anchor cases. The initial discovery pass added development evidence without changing production Java code; the later 0.10.0 relationship mapping has its own runtime evidence below. Existing earlier fixtures retain their original build scope.

## Person assignments — 0.10.0

The updated EntityScenario / verify_entities run passes with 1,395 entities and a selected person beyond the first-1,000 export. It checks all four relationship kinds with both absent and present assignments (two workplace, profession and home cases; one division case), selected-person parity, combined predicates, 18-page traversal, unknown-stat rejection and concurrent MCP reads requesting the new relationship projection through the actual server. Both processes exit zero. Full suite: 57 passing tests. Existing battle/context reports retain their earlier build scope; this pass does not rerun or extend those scenarios.

## Retained captures and observer regression — 0.11.0

The actual MCP run captures 1,395 entities and reads 70 retained pages while simulation advances. All pages preserve original tick/time and UI context, exclude a newly created citizen, and a new capture includes it. Concurrent pages, actual MCP text bounds, row/scan failures and UI-paused nonzero-speed export refresh pass. Both processes exit zero. Twelve new Python tests cover immutable-cache behavior, token expiry/eviction, session/server scope, size/completeness/identity failures and selection bounds; the full suite passes 69 tests. Java protocol tests include capture bounds as well as legacy malformed-request checks.

The eleven-phase context scenario passes again with the exact 0.11.0 mod: settlement, subject, game menu, confirmation, world, management, encyclopedia, loading overlay, room blueprint, reload and stale/unknown return-to-menu. Game/verifier exit zero. Earlier battle, editor and scene reports retain their original version/hash scope; they were not all rerun with the new observer.

Exploratory capture runs identified three issues before the successful run: SCRIPT sampling stopped under a UI pause with requested speed nonzero; clearing ordinary interrupters did not remove the fixture's pinned menu; and placing 1,100 fixture citizens together caused an engine collision-grid failure after resume. The production sampler now registers public GAME.addAfterUpdate. The fixture explicitly removes its pinned menu and disperses temporary citizens across reachable empty tiles. Those failed runs are not counted as passing validation. No copied game was saved and normal profile data was not modified.

This establishes bounded retained entity paging, not a global worker-thread transaction, full schema, all-menu support or large-city performance. The after-update hook is source/binary verified, not a separately documented stable SCRIPT contract.

## Provider requirements and local client check

PROVIDERS.md records nine required provider acceptance gates. Official Claude Code 2.1.296 reports Connected for the local stdio MCP in an isolated configuration; the normal client configuration contains no test entry. All three shell profiles pass syntax and credential-variable transition checks using fake values. No login or paid model request was made. Subscription entitlement, Claude API/DeepSeek inference, provider-specific model tool round-trips and in-game provider selection remain pending. provider-validation.json records this limited scope.

## Spatial query and scene regression — 0.12.0

The tile verifier checks direct public-getter expectations in a copied paused city through the actual MCP tool. It covers absent/present floors, room instances/shared room records and mineral deposits, terrain varieties, combined filters, coordinate bounds, exact installed mineral reference retrieval, rectangular pagination and concurrent tile/entity requests. The updated scene verifier additionally checks tile and legacy entity requests through city, tactical HUD, restored city, generated battle deployment/menu, reload and initial/terrain world setup. No game save is written by the tile fixture.

The first tile pass succeeded, but its follow-up verifier had started before the new editable module mapping was installed and failed to import syx_tiles. A late transition-only verifier then missed the original city phase and could not verify the reload baseline. Those are failed full-run attempts, not complete scene evidence. The clean installed-environment rerun passes all sixteen tile point cases, 306 matching tiles over 33 pages, and all eight scene phases. Both game and verifier exit zero. Current scoped reports are in validation-evidence.json.

The automated suite covers spatial selection bounds, unsupported/private projections, wire encoding, demo refusal, response scope/cursor/coordinate errors and the thirteen-tool MCP inventory. Pure Java tile framing accepts a valid frame and rejects fourteen malformed/unsupported frames. Earlier retained entity, battle and context reports preserve their earlier version/hash scope. This does not establish every game state/menu, active-combat tile consistency, complete tile/world schema or performance at large scales.

## Chat development checkpoint (2026-10-17)

The optional own-panel/chat implementation has separate [chat evidence](CHAT_VALIDATION.json) and [documented limits](CHAT_BACKEND.md). The current compiler/source audit covers 275 public production member references, including the new public widgets. The 0.12.0 observation-only reports and JAR hashes above remain historical evidence of their own builds. They do not attest reruns of all older scene scenarios with the chat prototype.

The isolated copied-save chat fixture passed normal public GUI-manager dispatch to the mod's own controls, click consumption, composer focus, chat creation through the coordinator, missing-key rejection with zero inference turns, reopen identity and world/city transitions. The sampled UI context identifies the mod-owned chat separately from underlying game selection. No screenshots or native input were used. No physical keyboard, exhaustive modal/menu/reload or authenticated provider flow was validated. Python protocol tests use mocked inference; the real stdio MCP discovery/missing-game tests remain credential-free.

## Authenticated shared-chat checkpoint

DeepSeek API and Claude subscription now pass separate two-turn flows through the shared in-game panel with selective MCP queries and cited guides. Local rename/evidence/export/delete and reload attachment are tested. Claude API has an explicit SDK route and missing-key/no-plan-fallback tests; actual API-key inference remains pending. See [current evidence](CHAT_VALIDATION.json) and [execution/credential limits](CHAT_BACKEND.md). OpenAI sign-in, fully in-game account setup, physical keyboard/multiline behavior and exhaustive scene coverage remain required.

## Core-data development checkpoint: research

`ResearchScenario` loads the existing copied save in the throwaway profile, pauses simulation, waits ten seconds for post-load initialization, and writes independent public-getter expectations. `dev/verify_research.py` connects to the actual stdio MCP server and checks all 402 technology rows, 1,132 expanded prerequisite relationships, 402 per-currency cost rows and three currencies. It checks prerequisite level references, available-point balance, a relational filter/join/projection with same-observation UI context, discoverable meanings, and null next-level cost after capping one technology through a test-only public setter. The copied game is never saved. Game and verifier exit zero.

The first exploratory run compared values before initialization settled and failed on currency totals; it is not accepted evidence. The delayed second run passed. This run validates the research expansion in a paused copied city, not every menu/scene or full game state. New evidence and exact source/JAR hashes are in CORE_VALIDATION.json. Existing chat provider validation remains historical to its recorded build; it was not rerun for these collector changes.

The final combined core-data run repeats the research checks on the new JAR and adds getter agreement for all 31 employment-room IDs/blueprints in the copied city. It selects an assigned worker through the public test-only subject API, then joins the dedicated selected-person observation to employment through the shared numeric room ID using one MCP query. The ID is unique within this observed employment set; this does not establish permanent identity. This combined run is the current CORE_VALIDATION.json checkpoint.

## Per-room production development checkpoint

`ProductionScenario` and `dev/verify_production.py` pass on the new production JAR: all 35 current-recipe input/output rows across 16 producer rooms match independent public getter expectations in the paused copied city. An actual MCP selection joins output rows to employment and resource storage, reports mixed scopes, and links resource IDs to installed help. Meanings distinguish configured coefficients, fractional day accumulation and stored ledger buckets.

The same JAR passes all eight `SceneScenario` phases with production coverage checks plus on-demand entity/tile reads: city, settlement tactical HUD, restored city, generated battle deployment, battle menu, copied-save reload, empty world setup and generated terrain. Non-world phases have partial scene room data with no getter failures; world setup leaves the domain unavailable. Both game runs and both verifiers exit zero. The full Python suite passes 141 tests. See PRODUCTION_VALIDATION.json for source and binary hashes.

Limits: this does not exercise a cap-exceeding large city, every producer type, current-day bucket alignment, live production forecasts, active combat/conclusion paths or every menu. The observer deliberately does not call bucket-refresh or production-mutating methods. No provider inference was needed for these checks.
