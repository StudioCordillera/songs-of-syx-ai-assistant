# Shared contributor instructions

Read this for every new/resumed run, including scheduled runs. Claude uses the same instructions through CLAUDE.md. The human user's current directions take priority.

## Start each run and check again before publishing

1. Run `python3 dev/collaboration_status.py`. It fetches origin/main and tags, identifies a changed published ZIP, ahead/behind/divergence, dirty files and overlapping remote edits. If unavailable, use `git status --short --branch`, `git fetch --prune --tags origin`, `git log --left-right --oneline HEAD...origin/main` and inspect both diffs. A failed fetch is not proof that no update exists.
2. Read README.md, WORK_STATUS.md, ROADMAP.md and the relevant entries in REPOSITORY_MAP.md / DOCUMENTATION_INDEX.md. Read the remote version of changed instructions as well. Current implementation/evidence outrank remembered chat history.
3. Reconcile remote work before building on overlapping assumptions. Preserve unpublished commits, staged/unstaged patches and relevant untracked files privately before integrating. Do not hard-reset, force-push, blindly stash/drop, overwrite another contributor's work or commit secrets/game data as a backup.
4. Compare implementations against the requirements, public-API provenance, correctness, boundedness, failure/consistency behavior, tests and maintainability. Keep the better implementation regardless of author, or combine the strongest parts into a better version. An identical patch can be dropped only after equivalence is established and work is recoverable. A conflict-free merge alone is not acceptance. Follow CONTRIBUTING.md for the decision record and Git workflow.
5. Re-run affected checks after reconciliation; evidence for a different source/JAR is historical. Fetch again immediately before pushing. A rejected non-fast-forward push means fetch/compare/reconcile, never force-push.

## Shared local device

Claude is a local/remote-controlled collaborator on this device, not an assumed cloud runner. Use separate checkouts (and branches) for concurrent edits: branches alone do not isolate a shared working directory. See LOCAL_DEVELOPMENT.md for tested host paths without credentials. Native runners must honor dev/game_fixture_lock.py's machine-wide advisory lock; do not run two fixtures, replace another runner's copied-profile mod, remove a held lock or kill another contributor's process. Core/chat/cost runners acquire the lock themselves; wrap manual native harnesses with the lock CLI. Locks require cooperation and do not replace Git reconciliation.

## Scope and boundary

Prioritize selective/discoverable game-state data, truthful UI/lifecycle context and high-quality version-aware cited references. Provider/account/sign-in expansion is deferred. Preserve the simple DeepSeek Pro player interface.

The production game bridge uses only explicit in-process public game APIs on the game update thread and detached DTOs. Distinguish documented SCRIPT contracts from shipped-source/binary verification. No private reflection/fields, process memory, screenshots, native game input/automation, arbitrary member invocation or gameplay mutation in production. Do not promote declaration candidates into getters without semantic/thread/cost review.

Keep partial/unavailable/unknown, null vs zero, scope, collection caps/errors, source provenance and observation/session consistency explicit. Never claim complete variables, menus, production or performance without evidence. Test-only public mutations belong only in path-validated disposable copied-game fixtures and must be labeled separately from observer behavior. Preserve normal saves and credentials.

## Validation and publishing

CONTRIBUTING.md has portable setup, offline checks, licensed-game fixtures, a manually supplied DeepSeek key workflow and candidate promotion. On this shared device Claude must use the ignored mode-0600 local .env via --env-file .env; the framework cannot inject environment variables. Never print or commit that file. Offline tests need no provider credentials. Never print keys, put them in commands/chat/commits, copy another app's tokens or run inference implicitly during offline tests.

Keep `releases/latest-user-test.zip` runnable and matched to production source on published main. Build/test candidates under ignored runtime/, promote with make_user_test.py only after required checks, retain the previous tested ZIP, and run `python3 dev/check_user_test_release.py`. Do not merge ZIPs or generated audit manifests by hand; regenerate from the chosen source and revalidate. Do not bypass freshness gates to publish unfinished production changes.

Treat game files/source/saves, snapshots, histories, environment files and raw provider/game logs as private local artifacts, never repository contents. The repo is public and has no selected redistribution license; do not invent one or redistribute proprietary material.

Update current docs, map/index entries, WORK_STATUS.md and evidence when publishing. Preserve historical reports/dates/hashes rather than relabeling old tests as fresh. Document which implementation was retained/combined and why when work overlaps. Keep final handoff concise, with changes, checks, limitations and the next useful core objective.
