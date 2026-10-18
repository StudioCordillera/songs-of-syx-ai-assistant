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
