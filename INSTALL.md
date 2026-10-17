# Installation and connection

## Build the mod

Use the actual 0.71.44 game folder containing `SongsOfSyx.jar`. A full JDK with the compiler and release signatures is needed. `SYX_JAVA_HOME` can select a JDK home if the default runtime lacks those components.

```sh
python3 build_mod.py --game-dir '/path/to/Songs of Syx'
```

The build contains only this project's classes. It targets Java 16 bytecode and creates:

```
dist/syx-ai-assistant/_Info.txt
dist/syx-ai-assistant/V71/script/syx-ai-assistant.jar
```

The shipped guide's `script/jar` example is older than the current loader; 0.71.44 scans `V71/script/*.jar`.
Copy the `syx-ai-assistant` folder into the game's **user** `mods` folder. On the tested Linux machine this is `~/.local/share/songsofsyx/mods`. Use the launcher's mod-folder location on other platforms. Enable the mod and load an existing or new game. Back up saves before using an experimental mod. The script stores no persistent save data.

## Set up MCP

Create the Python environment and install the project as shown in README. Merge `codex.example.toml` into your client's MCP configuration, replacing the executable path. Restart/reconnect the MCP client after configuration.

Both the game and MCP server default to `~/.local/share/syx-assistant`. Set `SYX_STATE_DIR` in both processes to override; the game also accepts `-Dsyx.assistant.stateDir=/absolute/path`. The directory is local to this user and holds live game data, the optional reviewed corpus, and bounded read-request/response transport files. No network listener is opened.

Run `syx-knowledge --state-dir /your/state/directory` once to merge the five reviewed starter summaries without overwriting existing records. Installed resource/technology/stat references do not require this step.

Ask the assistant to call `game_status`, `game_query_help`, and `describe_game_fields`. See QUERY_GUIDE.md for examples. A missing/unloaded/stale snapshot is an explicit error; never replace it with synthetic data.

## Access boundary

Only the in-process script mod reads the game, using mapped public APIs. MCP reads detached local snapshots.
No control panel, screenshot tool, private-field query or native input adapter is included. Version 0.8.0 includes partial UI/API evidence tools and query_live_entities for bounded on-demand reads. The latter requires a POSIX MCP host. Use matching mod/MCP builds; older mods may omit the content fields or lack the on-demand request handler.
Replace the previous mod folder/JAR completely when upgrading; do not merge old classes into the new JAR.
See API_BOUNDARY.md for primary-source provenance and lifecycle limitations.

## Troubleshooting

- Unsupported game: use the verified build or update and revalidate the adapter; do not bypass the version guard.
- No snapshot: confirm the mod is enabled, a game is loaded and both processes point at the same directory.
- Stale snapshot: inspect the game log; a paused game should still refresh wall-clock snapshots.
- Compiler missing: select a complete JDK, rather than a JRE.
- Result too large: discover the field schema, project fewer fields, lower depth or paginate.
- Unclear raw field: inspect shipped game documentation/source locally and record its meaning before relying on it.

For a synthetic offline demonstration, copy `snapshot.example.json` to a separate runtime directory. It is labeled demo and never accepted for live UI control.

## Claude subscription/API and DeepSeek API

Use the official-client profiles and shared stdio configuration in [PROVIDERS.md](PROVIDERS.md). `claude.mcp.example.json` contains no provider credentials. These setup examples do not install, authenticate or start a provider client automatically.
