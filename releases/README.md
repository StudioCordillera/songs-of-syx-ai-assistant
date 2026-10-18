# Playable user-test download

[Latest tested Linux ZIP](https://github.com/StudioCordillera/songs-of-syx-ai-assistant/raw/refs/heads/main/releases/latest-user-test.zip) · [Setup instructions](../user_test/README.txt)

The stable filename follows the tested production code on main. It includes our compiled mod and the simple DeepSeek Pro client. It excludes credentials, histories, saves, game binaries and game source. The runtime model is explicitly `deepseek-v4-pro`; no Flash fallback is allowed in the player client.

`latest-user-test.json` records checksums and validation scope. Candidates are checked before replacing the download. On the next promotion, the prior ZIP is retained as `previous-user-test.zip`. The installer separately backs up an existing local mod and restores it if copying fails. Save files are outside the installer target.

For maintainers: build against the licensed supported game, audit public references, run appropriate tests and an isolated Pro chat check, then run `dev/verify_user_test_chat.py` and `make_user_test.py`. Install repository hooks with `git config core.hooksPath .githooks`. `python3 dev/check_user_test_release.py` rejects stale packaged Java/Python sources, launchers, builder, packager, manifest or validation. CI runs that same check without proprietary game files or credentials. CI checks freshness; it cannot replace a licensed-game playtest. Packaging alone is not evidence that every menu or game variable works.

Dependencies install on first launch, so an internet connection and supported Python environment are needed. This is a Linux test build, not an installer for every platform. Full game-state coverage and exhaustive UI/lifecycle acceptance remain open in ROADMAP.md.
