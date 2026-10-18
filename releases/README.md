# Playable user-test download

[Latest tested Linux ZIP](https://github.com/StudioCordillera/songs-of-syx-ai-assistant/raw/refs/heads/main/releases/latest-user-test.zip) · [Setup instructions](../user_test/README.txt)

The stable filename follows the tested production code on main. It includes our compiled mod and the simple DeepSeek Pro client. It excludes credentials, histories, saves, game binaries and game source. The runtime model is explicitly `deepseek-v4-pro`; no Flash fallback is allowed in the player client.

`latest-user-test.json` records checksums and validation scope. Candidates are checked before replacing the download. On the next promotion, the prior ZIP is retained as `previous-user-test.zip`. The installer separately backs up an existing local mod and restores it if copying fails. Save files are outside the installer target.

For maintainers: build against the licensed supported game, audit public references, run appropriate tests and an isolated Pro chat check, then run `dev/verify_user_test_chat.py` and `make_user_test.py`. Install repository hooks with `git config core.hooksPath .githooks`. `python3 dev/check_user_test_release.py` rejects stale packaged Java/Python sources, launchers, builder, packager, manifest or validation. CI runs that same check without proprietary game files or credentials. CI checks freshness; it cannot replace a licensed-game playtest. Packaging alone is not evidence that every menu or game variable works.

Dependencies install on first launch, so an internet connection and supported Python environment are needed. This is a Linux test build, not an installer for every platform. Full game-state coverage and exhaustive UI/lifecycle acceptance remain open in ROADMAP.md.

The launcher checks dependency imports at each start and retries installation when a previous attempt failed. This is exercised by a two-attempt failure/retry test; network availability and provider service availability remain external requirements.

To validate a candidate while keeping the public ZIP intact, package into a runtime directory and pass `--candidate-dir` plus its `--validation` report to `dev/verify_current_player_core.py`. Its default remains the published bundle. The core suite includes copied-game regional getter checks before scene/UI regressions. Promote only after the relevant checks pass.

The current core suite also checks nonzero city trade bookkeeping in a copied save and verifies that battlefield-unavailable city logistics cannot be queried/count-aggregated as zero. This is a scoped evidence checkpoint, not a complete trading or all-menu acceptance claim.

The service-counter build adds a seventh core fixture group: per-room raw service points, a nullable staffing join and installed help links. The same candidate is checked across the existing scene/UI groups before promotion. Service points are not daily people capacity or guaranteed citizen access; see SERVICE_COUNTERS.md.

The reference/discovery checkpoint keeps the service-counter Java JAR unchanged and updates its paired Python knowledge/API-support modules. It validates current modules with unit tests, actual MCP retrieval/discovery, two current-build Pro turns and extracted-client startup/install checks. Earlier scene/core reports retain their prior Python hashes; unchanged Java does not relabel those as a new full-suite run. The previous tested ZIP is retained on promotion.

The configured-service-policy build adds city race/class permission flags while retaining the simple Pro interface. Its current JAR/Python pair is checked by all seven core groups and a two-turn Pro run before promotion. Battlefield city policy is unavailable, and configured flags are not effective individual eligibility; see SERVICE_PERMISSIONS.md.

The collection-diagnostics build retains the same Java mod and simple Pro interface. Paged state reads and selective-query sources now carry ancestor truncation/failure counts and limits, so completing pagination does not imply a complete game census. Current Python passes the seven-group core suite, two Pro turns and a separate real entity-prefix cap check before promotion. See COLLECTION_DIAGNOSTICS_VALIDATION.json, ENTITY_PREFIX_VALIDATION.json and QUERY_GUIDE.md for the synthetic/native boundaries.

The historical-reference build adds two reviewed developer-thread summaries while retaining unknown patch compatibility and all existing reference dates/edits. Its thirteen-record corpus passes 37 MCP retrieval cases, 167 tests and two current-build Pro turns. Prior game/query core evidence remains explicitly scoped to its recorded knowledge-module hash; Java and the query engine are unchanged. Current extracted-client checks and release freshness pass before promotion.

The workforce-factor build adds bounded stored employment factors and same-observation recorded-output joins while preserving the simple Pro interface. The candidate passes 168 tests, two actual Pro turns, all seven copied-save core groups and fresh extracted-client checks before promotion. Current small-city collection cost is measured separately; complete production modifiers, cap/fault/large-city behavior and exhaustive menus remain open. See WORKFORCE_FACTORS.md and COLLECTION_COST.md.


The workplace-filter build adds optional recorded-room assignment selection for live entity reads and retained captures, without extra game member references. Fourteen native worker IDs, exclusions and combined predicates pass in a 1,395-entity copied scene. The exact candidate passes 175 tests, Java codec checks, two Pro turns, all seven core groups, six supported capability probes, 37 guidance cases and fresh extracted-client checks before promotion. The previous tested ZIP is retained. Assignment is not present activity or permanent room identity; complete production, menus and large-city costs remain open. See WORKPLACE_FILTER.md and WORKPLACE_FILTER_VALIDATION.json.


The producer-degradation build adds a source-backed stored room value to producer recipe flows and a staffing/output query example. Its baseline 16 producer rooms all report zero. Separate decoder/query synthetic tests and a controlled copied-game public maintenance action also pass; the latter verifies one actual positive room value through the getter and MCP. No game is saved, and the production observer invokes no maintenance action. The candidate passes 177 tests, two real Pro turns, all seven copied-save core groups, seven supported capability probes, 37 guidance cases and fresh extracted-client checks. The simple player interface is preserved and the previous tested ZIP retained. No full bonus, exact age, large-city or exhaustive-menu claim is made. See ROOM_DEGRADATION.md and DEGRADATION_VALIDATION.json.


The world-faction-context build adds a bounded public panel identity/diplomacy-tab observation and same-snapshot diplomacy selection, preserving the simple Pro UI. Eleven native faction phases, 236 Python tests, two Pro turns, seven native core groups and extracted-client checks pass before promotion. Source/compiler review excludes named private live-room/management/panel routes and mutating region/tooltip builders; it does not prove no other public API exists. The previous tested ZIP is retained. Current paused-city cost is measured separately; all menus, cap/fault and larger-city acceptance remain open. See WORLD_FACTION_CONTEXT.md and WORK_STATUS.md.
