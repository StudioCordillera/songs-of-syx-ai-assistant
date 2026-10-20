# Computer-use adapter removed in 0.3.0

The user requires game access through the in-process game API route. The previous screenshot, native/window-input and private-field adapters have been removed from current source, registered MCP tools and built artifacts.

No game UI control or screenshot-based understanding is available. Version 0.4.0 adds observation-only public-API context; see API_ESTABLISHMENT.md. Future UI awareness must use an appropriate public game API with documented/source-verified provenance; documented SCRIPT event callbacks alone do not establish full UI semantics or synthetic-input support. See API_BOUNDARY.md.

The later player request adds a planned public-API copilot execution track; see [PLAYER_EXPERIENCE_PLAN.md](PLAYER_EXPERIENCE_PLAN.md). That track must establish typed commands and per-context acceptance before enabling gameplay actions. It does not restore the removed OS/screenshot driver. Published tutorial/Workshop/forum visuals may be reviewed as external reference material with provenance and rights; this is separate from observing or controlling the running game.

Historical commits/tests of the former driver do not establish capabilities of the current build.
