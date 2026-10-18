# Installation and development connection

## Play the tested Linux build

Download the [latest tested player ZIP](https://github.com/StudioCordillera/songs-of-syx-ai-assistant/raw/refs/heads/main/releases/latest-user-test.zip), extract it, run `python3 install-mod.py`, then `sh start-chat.sh`. Enable the mod, load a supported **0.71.44** game and open **AI chat → New chat**. Read [the bundled instructions](user_test/README.txt).

The bundle contains the compiled mod and simple DeepSeek Pro client, chat/session histories, Send/Stop and a wrapped composer. No compiler or coding client is needed to play. Python and first-launch dependency downloads are required. Credentials stay in a private external environment/file, never the bundle or game save. Provider/login/debug controls are hidden; tool JSON stays in private logs. The installer backs up the existing own-mod folder and rolls back copying failures without editing saves. [Release policy](releases/README.md) explains the retained previous ZIP.

## Build and test as a contributor

Use [CONTRIBUTING.md](CONTRIBUTING.md) for complete Python/JDK/game configuration, copied-game fixture setup, manually supplied DeepSeek credentials, native tests and candidate promotion. Read [AGENTS.md](AGENTS.md) at each run and fetch/compare collaborators' work before editing/publishing.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
export SYX_JAVA_HOME='/path/to/full-jdk'
.venv/bin/python -m pytest -q
.venv/bin/python build_mod.py --game-dir '/path/to/Songs of Syx'
```

A full JDK 17+ is required for development/audits; the mod targets release 16. Native copied-game tests use Java 21 on the tested host and need a working desktop/OpenGL environment. Never substitute a synthetic observation for a loaded game or use an original save as a mutable fixture.

The builder creates `dist/syx-ai-assistant/_Info.txt` and `dist/syx-ai-assistant/V71/script/syx-ai-assistant.jar`. The 0.71.44 loader scans `V71/script/*.jar`; older documentation's `script/jar` path is historical. For manual installation use the launcher's user-mod directory (`~/.local/share/songsofsyx/mods` on the tested Linux machine), replace this mod's entire folder and enable it. Do not merge old classes into a new JAR. Prefer the tested player installer for backups.

## Standalone MCP

The game and MCP must share `SYX_STATE_DIR` (default `~/.local/share/syx-assistant`); Java also accepts `-Dsyx.assistant.stateDir=/absolute/path`. This local directory contains detached exports, optional curated summaries and bounded request/response mailboxes. It is not the save directory and opens no network listener. Live request transport currently needs a POSIX host.

Merge [Codex](codex.example.toml) or [Claude](claude.mcp.example.json) stdio configuration into your existing client using your own executable/state paths. These are development bridges, not in-game account setup. MCP reads no provider credentials and makes no inference calls. Ask for `game_status`, `game_query_help`, `get_game_api_support` and `describe_game_fields` before a narrow query.

`syx-knowledge --state-dir <directory>` merges 13 reviewed starter summaries without replacing edited records or refreshing old retrieval dates. The native coordinator does this automatically. Installed-game descriptions require no seed setup. Matching current mod/MCP builds are required; old mods may omit fields or reject new wire keys. [Query limits](QUERY_GUIDE.md), [data coverage](DATA_COVERAGE.md) and [API boundary](API_BOUNDARY.md) explain provenance and partial scope.

## Chat development routes

The current simple Pro panel is enabled by default. Start `.venv/bin/python -m syx_chat_service --state-dir <same-directory> --history-dir <private-dev-history>` with `--env-file .env` for the private local key (or an explicitly supplied environment key), or use the paid fixture runner in CONTRIBUTING.md. No Claude-compatible endpoint profile is needed for this native DeepSeek route.

Advanced developer controls require both `-Dsyx.assistant.chat.advanced=true` and coordinator `--advanced`. [CHAT_BACKEND.md](CHAT_BACKEND.md) describes that historical/experimental interface and older Claude subscription evidence. Provider/account expansion stays deferred; Claude API inference, native OpenAI access and in-game account setup remain incomplete. [PROVIDERS.md](PROVIDERS.md) distinguishes requirements from evidence.

## Troubleshooting

- Unsupported version: use the supported build or explicitly revalidate the adapter; do not bypass the guard.
- Missing/stale data: confirm enabled mod, loaded game, matching build/state paths and logs. UI-paused games should refresh, but menu return can retain apparently current data for up to 30 seconds before state becomes unknown.
- Missing compiler: select a full JDK using SYX_JAVA_HOME with java on PATH.
- Oversized query: inspect schema, project fewer fields/rows or page. Completing pages does not undo collector truncation/failures.
- Ambiguous field/UI: use source-backed definitions and same-observation context; unknown/private data stays unavailable.

`snapshot.example.json` is an explicitly synthetic offline example. It is never a live fallback. Screenshots, native game control, private fields and arbitrary invocation remain excluded.
