# Songs of Syx AI Assistant

A custom advisor mod that understands the currently loaded Songs of Syx game and answers questions with cited game guides and forum evidence, using supported OpenAI subscription connections.

**Status: researched foundation and runnable MCP prototype. No installable game mod or live game integration yet.**

## Vision

Ask “Why is my food supply falling?” and receive an explanation tied to this settlement's stockpiles, production, consumption, workforce, and current game version, with links supporting the mechanics and actionable suggestions. The target is comprehensive access to the loaded game, through structured queries rather than sending every entity to the model on every question.

The initial assistant observes and advises. It does not issue gameplay commands.

## What works today

- A local stdio MCP server using the official Python SDK.
- Three read-only tools: `game_status`, `query_game_state`, and `search_guidance`.
- Versioned snapshot validation, per-domain coverage, session/snapshot identity, freshness checks, bounded results, and array pagination.
- Searching an operator-curated local corpus with direct citation URLs and version compatibility labels.
- Explicit missing-game and demo behavior; no sample data is silently treated as live.

## What still needs building

- The Java mod/exporter for a verified game build, including unload detection and complete domain collectors.
- Retrieval/refresh of real gameplay guides and forum posts. The corpus starts empty; the source directory is discovery metadata, not retrieved gameplay evidence.
- In-game chat UI and subscription login integration. The prototype connects to an existing Codex client; it performs no model calls itself.
- Cross-platform packaging and in-game performance/compatibility validation.

See [architecture](ARCHITECTURE.md), [roadmap](ROADMAP.md), and [verified references](REFERENCES.md).

## Try the MCP prototype

Python 3.11 or later is required. From the checkout:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m pytest -q
```

On Windows use `.venv\Scripts\python.exe` in place of `.venv/bin/python`.

Configure the stdio command using [codex.example.toml](codex.example.toml). Use an absolute path to `.venv/bin/syx-mcp` (Windows: `.venv/Scripts/syx-mcp.exe`) and an absolute `SYX_STATE_DIR`. Without an exporter, `game_status` correctly reports that no snapshot is available.

For an explicitly synthetic demo, create `runtime/`, copy `snapshot.example.json` to `runtime/snapshot.json` and `corpus.example.json` to `runtime/corpus.json`, and point `SYX_STATE_DIR` at that directory. Demo queries are allowed even though the example timestamp is old; all responses identify the data as demo, never live. Runtime data is gitignored.

## Subscription connection

The first development route is an existing Codex client signed in with ChatGPT, connected to this local MCP server. This uses that client's account entitlements and usage limits. MCP supplies data/tools; the client supplies the assistant.

For the eventual custom in-game client, OpenAI documents ChatGPT plan usage through Sign in with ChatGPT for eligible open-source/local apps. Registration, consent, eligibility, token renewal, and current preview limitations must be verified and implemented before shipping. Local MCP tools must be executed by the local client/app-server; hosted Responses MCP is unsupported on that preview route. See [the connection decision](ARCHITECTURE.md#openai-connection).

An API-key route would have separate API billing. This project never reads another application's authentication files, copies browser cookies, or calls private ChatGPT endpoints.

## Development boundary

Do not commit game binaries, game source, saves, snapshots, account tokens, or copied full guides. The game is not installed in the development environment used to create this foundation, so no game-version compatibility is claimed. Repository visibility is initially private; choose a source license before a public/open-source release or registration that requires it.
