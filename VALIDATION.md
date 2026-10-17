# Validation — 0.9.0 public API/context audit

## Current checks

- 56 Python tests pass: snapshot validity/freshness, demo isolation, paging, selected-data bounds, query filtering/joins/grouping/aggregation, cited source authority/version labels, and MCP transport.
- MCP transport verifies exactly ten tools, all read-only. No raw-field, screenshot or input tools are registered.
- Boundary tests check the mod namespace and reject reflection, native input/capture, process launch and engine-resource bypass patterns in production Java source. These tests supplement source review, not a complete security proof.
- Six production Java source files compile against the installed 0.71.44 JAR with Java 16 target bytecode. Detached JSON serialization tests pass.

## Rebuilt-mod copied-save test

The new 0.3.0 mod was loaded in an isolated Linux user profile using Java21 and a copied save. All 18 domains returned partial coverage. The installed-help catalog contained 720 records; a structured query ranked the 42 resource rows by stockpile storage and returned only selected IDs/values. No control mailbox was created. Original saves were not modified.

## Explicit limitations

The script lifecycle is documented in the shipped SCRIPT source and semi-official script guide. Most individual data getters are public APIs verified in shipped source, not separately documented stable contracts. API_BOUNDARY.md records that distinction. Complete state access is not claimed.

Partial public-API UI context is exported; gameplay control remains excluded. The prior native-input and private-reflection tests are historical and do not apply to this build. An 11-check copied-save scenario passed: settlement, selected subject, game menu, confirmation, world view, management overlay, encyclopedia, loading overlay, room blueprint context, save reload/session rotation, and stale/unknown status after return to the main menu. The last check does not identify main-menu subpages. A further eight scene checks passed in 0.5.0: city, settlement tactical HUD, restored city, generated battle deployment, battle menu, reloaded city, initial world creation and generated terrain. The 0.9.0 fixture below adds sampled engagement and controlled victory/defeat paths. Natural campaign resolution, complete political-world generation, full editor workflows and every menu/popup combination remain unvalidated. The eleven context checks were run with 0.6.0. The eight scene checks and larger entity fixture were run with 0.7.0. The 0.8.0 extended fixture covers sixteen UI/editor/retreat phases.

GameDisposable promises cleanup on the next game initialization. JVM shutdown also closes the exporter. Immediate return-to-menu detection is not established without an appropriate public lifecycle hook; stale state expires after 30 seconds. No large-city frame-time or cross-platform performance claim is made.

## Reproducible evidence

The production compiler audit resolved 197 public game members, with 196 shipped-source declaration matches and one generated enum member. It inventories mod references rather than every possible game variable. API_ESTABLISHMENT.md records the distinction between documented script contracts, public source-verified access and runtime checks. The context verifier completed with no missing phases; both verifier and isolated game exited with code zero. Test output/state remains local under runtime/ and is not published.

## Isolated fixture preflight

`LiveSmoke` requires an explicit state directory, an existing sibling `smoke-home` as its isolated user home, and a copied save inside that fixture root. It resolves real paths and rejects the normal user home or an original save outside the root before engine initialization. `-Dsyx.smoke.validateOnly=true` validates these boundaries without starting the engine. Fixtures are development-only and never packaged in the mod. Scene verification is implemented by `dev/verify_scenes.py`; context verification by `dev/verify_context.py`.

Three static binary checks pass for resource-owned semantics, the menu state factory and engine-disposal accessibility. They support these specific findings, not whole-SDK source/binary equivalence. The latest scene run and verifier both exited zero, with all eight required phases observed. Runtime reports and saves remain private local artifacts.

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
