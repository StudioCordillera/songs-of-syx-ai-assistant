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

Both the game and MCP server default to `~/.local/share/syx-assistant`. Set `SYX_STATE_DIR` in both processes to override; the game also accepts `-Dsyx.assistant.stateDir=/absolute/path`. The directory is local to this user and holds live game data, screenshot receipts and the optional reviewed corpus. No network listener is opened.

Run `syx-knowledge --state-dir /your/state/directory` once to merge the five reviewed starter summaries without overwriting existing records. Installed resource/technology/stat references do not require this step.

Ask the assistant to call `game_status`, `game_query_help`, and `describe_game_fields`. For deeper reads call `query_live_game_fields` with an empty list to discover roots. See QUERY_GUIDE.md for examples. A missing/unloaded/stale snapshot is an explicit error; never replace it with synthetic data.

## Optional UI control

The in-game panel offers “Allow AI control (5 min)” and Stop. Reading game state requires no grant. Capturing/controlling the viewport follows the current driver rules; changing the UI requires a current grant, session and recent screenshot. Physical key/mouse/scroll input revokes the grant. The assistant cannot click its own permission controls. No desktop access is exposed.

## Troubleshooting

- Unsupported game: use the verified build or update and revalidate the adapter; do not bypass the version guard.
- No snapshot: confirm the mod is enabled, a game is loaded and both processes point at the same directory.
- Stale snapshot: inspect the game log; a paused game should still refresh wall-clock snapshots.
- Compiler missing: select a complete JDK, rather than a JRE.
- Result too large: discover the field schema, project fewer fields, lower depth or paginate.
- Unclear raw field: inspect shipped game documentation/source locally and record its meaning before relying on it.

For a synthetic offline demonstration, copy `snapshot.example.json` to a separate runtime directory. It is labeled demo and never accepted for live UI control.
