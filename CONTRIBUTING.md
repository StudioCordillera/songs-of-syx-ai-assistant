# Contributor and Claude development workflow

Read [AGENTS.md](AGENTS.md), [the repository map](REPOSITORY_MAP.md) and [current handoff](WORK_STATUS.md) first. Work on the core [roadmap](ROADMAP.md); provider/account/sign-in expansion remains deferred. Coding with Claude does not require changing the mod's provider adapters.

## Start and end every run

Run `python3 dev/collaboration_status.py` before edits and immediately before publishing. It fetches origin/main and Git tags, reports divergence, overlapping committed/uncommitted paths and tracked player-bundle changes. `--no-fetch` inspects cached refs only; fetch failure exits nonzero and does not establish freshness. The helper never pulls, merges, resets, stashes or edits work files. It checks this project's tracked release channel, not separately uploaded GitHub release assets.

If aligned and clean, a separate checkout directory and feature branch per contributor/topic keep concurrent edits separate; changing branches inside one shared checkout does not. Claude runs locally on this device; see LOCAL_DEVELOPMENT.md for tested paths. Avoid simultaneous writes to the same checkout, release files or native fixture profile. Existing authorized main work can continue there when reconciled. Keep normal fast-forward pushes; do not force-push shared history. GitHub PRs are useful for review but do not replace validation or imply a new human approval requirement.

## Reconcile concurrent work

1. Preserve recoverable local work first: a local backup branch for unpublished commits, private binary patches for staged/unstaged tracked changes, and copies of relevant untracked source files. Use ignored runtime/ with private permissions for patches; inspect contents before staging. Never publish keys, game files, raw state or histories as a backup.
2. Compare `git log --left-right --oneline HEAD...origin/main`, `git diff HEAD...origin/main`, `git diff origin/main...HEAD`, `git diff` and `git diff --cached`. Read complete implementations and tests for overlapping paths, including remote instruction/documentation changes. Do not use timestamps, model identity or line count as quality criteria.
3. Assess requirement fit, public-API provenance, correct meaning/units, bounds, null/error/freshness behavior, test evidence and maintainability. Keep the better version or implement a better combination. Drop a redundant patch only after proving equivalence and preserving recovery. Carry forward useful tests from both sides; obsolete tests/claims must be corrected, not blindly retained.
4. Integrate on the working branch using an appropriate merge/rebase after preserving dirty work. Resolve source first. Rebuild generated API manifests and player ZIPs from the chosen implementation; do not hand-merge binaries or fabricate validation. A clean Git merge is not proof of correct behavior.
5. Run affected checks against the reconciled source. Record in the commit/PR or handoff which competing changes were kept/combined and why. Fetch again before pushing; if the remote moved, compare/reconcile again. A rejected push is not permission to force it.

## Offline setup — no provider credentials

Use Python 3.11+, Git and a complete JDK 17+ (compiler/release signatures, not just a JRE):

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
export SYX_JAVA_HOME='/absolute/path/to/full-jdk'
.venv/bin/python -m pytest -q
python3 dev/check_documentation.py
python3 dev/check_user_test_release.py
```

Keep `java` on PATH. `SYX_JAVA_HOME` selects its module/release files for this repo's compiler invocations. The Java mod targets release 16; the audit/catalog tools need release 17+. The optional `claude` extra is for deferred advanced SDK/provider work, not a prerequisite for core development or the simple Pro client.

Pytest also checks that the duplicated Java tile-projection allowlist, snapshot discovery list and Python schema/field definitions agree. Run this cheap cross-layer check before paid/native work; native MCP tests remain the behavior proof.

Pytest discovery excludes ignored runtime/build/hidden dependency directories, so disposable source clones under runtime do not duplicate the suite. Pytest uses mocks/synthetic fixtures and local Git repositories. It does not need a key or real inference. Native-game tests are explicit scripts; GitHub CI cannot validate licensed-game behavior. Documentation-only/developer-tool changes do not require rebuilding the unchanged player payload or refreshing historical product test counts.

## Licensed game fixture setup

Set paths for your own licensed supported game, full JDK and a working game-compatible Java executable. Java 21 is the tested native runtime; the development JDK can be newer. A working desktop/OpenGL/native-library environment is needed even though the fixtures use no screenshots or native input.

```sh
export SYX_GAME_DIR='/absolute/path/to/Songs of Syx'
export SYX_GAME_JAVA='/absolute/path/to/java21/bin/java'
export SYX_JAVA_HOME='/absolute/path/to/full-jdk'
mkdir -p runtime/smoke-home
# Copy a compatible test save yourself; do not point tests at the original.
cp '/path/to/a/copied-or-original-test.save' runtime/smoke.save
python3 -m zipfile -e releases/latest-user-test.zip runtime/fixture-player
python3 runtime/fixture-player/install-mod.py --user-dir runtime/smoke-home/.local/share/songsofsyx
```

These paths are local configuration, not committed defaults. Do not copy an entire real home or auth directory. The loader validates that the save is under runtime/ and Java user.home is the sibling runtime/smoke-home. The copied profile's settings may be written; game saves are never written by fixtures. One native fixture at a time across checkouts. Core/chat/cost runners use the shared advisory lock under ~/.cache/syx-ai-assistant/game-fixture.lock; honor it, never remove a held lock or kill another contributor's process. Wrap manual harnesses with `python3 dev/game_fixture_lock.py -- <fixture-command>` (do not wrap an already locking runner). Keep the normal profile and normal saves out of commands.

For current published-player core checks, no provider key is used:

```sh
.venv/bin/python dev/verify_current_player_core.py \
  --game-dir "$SYX_GAME_DIR" --save runtime/smoke.save \
  --java "$SYX_GAME_JAVA" --jdk-home "$SYX_JAVA_HOME"
```

This extracts the published JAR and runs services, trade, world, production, scenes, UI/help lifecycle and extended UI fixtures. Additional dev verifiers cover entities/captures/tiles/battles, source/binary contracts and controlled positive degradation. `dev/run_read_fixture.py --case regional-cost` measures regional collector/encoding and sequential actual MCP latency without inference; see REGIONAL_LIVE_READS.md for the full command and exclusions. See [map and evidence](REPOSITORY_MAP.md). Synthetic cases, controlled public mutations and unmodified observations are distinct evidence.

## Local .env for Claude's paid development test

Claude's remote-control framework on this device cannot inject the key into its environment. Use the ignored repository-local `.env` file, already prepared on the shared Kali checkout. It contains one literal `DEEPSEEK_API_KEY=...` entry and has owner-only (0600) permissions. Do not overwrite an existing key file or display its contents.

On a fresh separate checkout, privately copy/supply the key in that checkout's own `.env` (the blank `.env.example` is only a template). `git check-ignore .env` must succeed and `git ls-files .env` must print nothing. Keep permissions at 0600. Do not paste the value into a prompt, command argument, source file or commit, and never source this file as a shell script. The runner parses it as literal data and gives the key only to its coordinator child.

An explicit external private file is also supported with `--env-file /absolute/private/provider.env`. If a different framework can already provide `DEEPSEEK_API_KEY`, omitting --env-file uses that environment variable. Neither option requires changing the coding client's provider/account configuration. Avoid shell tracing/environment dumps.

Run the explicit paid integration test with the local file:

```sh
.venv/bin/python dev/run_player_chat_check.py \
  --game-dir "$SYX_GAME_DIR" --save runtime/smoke.save \
  --java "$SYX_GAME_JAVA" --jdk-home "$SYX_JAVA_HOME" \
  --env-file .env
```

This audits/builds the current source, compiles public-API fixtures, temporarily installs only our mod in the copied profile, starts the simple coordinator, performs two actual `deepseek-v4-pro` turns and verifies selective rows/citations/no visible debug JSON. It strips provider credentials from the game/MCP environment, restores the prior copied-profile mod and prints candidate JAR/report paths under ignored runtime/. Private logs/history stay there. It makes real paid requests only when invoked. A missing/invalid key, quota or provider error is a failed test, never permission to switch provider/model/billing.

For manual in-game testing, use the built mod with the normal player instructions and start `.venv/bin/python -m syx_chat_service --state-dir <same-state-dir> --history-dir <private-dev-history>`; pass `--env-file .env` to read the same private literal file. Keep developer history separate. No coding-client provider profile is needed for this native DeepSeek path.

## Change and promote production code

For a Java mapping, review licensed source/binary semantics/thread/cost, edit explicit DTOs, audit with `audit_api.py`, and build with `build_mod.py`. Both accept `--game-dir`; the builder accepts `--output runtime/<candidate>`. Update relevant source review, typed definitions, query examples and native getter/MCP checks. The full declaration catalog is a candidate backlog, not supported variables.

Use the JAR and provider report printed by the paid runner:

```sh
.venv/bin/python make_user_test.py --mod-jar <candidate.jar> \
  --validation <provider-validation.json> --output runtime/player-candidate
.venv/bin/python dev/verify_current_player_core.py \
  --game-dir "$SYX_GAME_DIR" --save runtime/smoke.save \
  --java "$SYX_GAME_JAVA" --jdk-home "$SYX_JAVA_HOME" \
  --candidate-dir runtime/player-candidate --validation <provider-validation.json>
```

Run the required feature-specific fixtures, pytest, guidance/discovery checks and fresh extracted dependency/startup/isolated-install/credential-exclusion checks. Assemble USER_TEST_VALIDATION.json with exact source/JAR/evidence hashes and honest scopes. The raw paid report is a starting point, not proof of all menus or a complete release checklist. Promote with make_user_test.py's default releases output only after checks pass, then `python3 dev/check_user_test_release.py`. Preserve the previous tested ZIP; do not promote twice and accidentally replace the real predecessor with a duplicate candidate.

Install hooks with `git config core.hooksPath .githooks`. The pre-push hook and CI check release freshness. Published main must pair production source with the tested ZIP; do not bypass that gate for unfinished production changes. Push review-ready changes, check remote CI/download checksums and leave a concise WORK_STATUS.md handoff.

## Documentation and evidence

Run `python3 dev/check_documentation.py` before publishing. Update REPOSITORY_MAP.md and DOCUMENTATION_INDEX.md for new entry points/docs, current guides for behavior changes, and WORK_STATUS.md for next work. Keep historical dates/hashes/cases intact; label stale claims or replace misleading current prose. Earlier reports are not fresh validation of a changed source/JAR. Preserve the public-only game boundary, simple Pro interface, credentials, normal saves and proprietary game materials.
