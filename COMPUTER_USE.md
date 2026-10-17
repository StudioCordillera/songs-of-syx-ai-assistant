# Computer-use adapter removed in 0.3.0

The user requires game access through the in-process game API route. The previous screenshot, native/window-input and private-field adapters have been removed from current source, registered MCP tools and built artifacts.

No game UI control or screenshot-based understanding is available. Future UI awareness must use an appropriate public game API with documented/source-verified provenance; documented SCRIPT event callbacks alone do not establish full UI semantics or synthetic-input support. See API_BOUNDARY.md.

Historical commits/tests of the former driver do not establish capabilities of the current build.
