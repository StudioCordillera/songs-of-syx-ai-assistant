# Contributing

Install `.[dev]` in a virtual environment and run `python -m pytest -q` before submitting changes. Keep runtime state and game files outside version control.

Game access must stay within the in-process SCRIPT route and typed public API calls. No private reflection, native/window input hooks, screenshots, process-memory inspection, arbitrary method invocation or OS automation. Add source provenance for every new game mapping in API_BOUNDARY.md; distinguish documented hooks from source-verified public members.

Keep missing/unknown values explicit, domains partial until coverage is established, and UI/context claims tied to actual exported observations. New APIs need compile and copied-save validation against the supported game build.

No code may read another app's auth files, use private OpenAI endpoints, silently switch billing, execute retrieved instructions or expose an unauthenticated remote listener. The repository is private and has no selected redistribution license. Do not distribute proprietary game files or full copied guides.
