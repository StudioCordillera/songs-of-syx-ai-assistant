# Contributing

Install `.[dev]` in a virtual environment and run `python -m pytest -q` before submitting changes. Keep runtime state and game files outside version control.

Do not claim a supported game version until collectors are compiled and tested against that build. Update coverage and source provenance with every new collector. Unknown values must remain unknown, never zero-filled. All exported observations need units and a stable field definition.

No code may read or reuse another app's auth files, rely on private OpenAI endpoints, silently switch billing mode, execute retrieved instructions, or expose local state over an unauthenticated remote listener. Read-only tools must stay read-only.

The repository is initially private with no release license selected. Resolve licensing before accepting external code or distributing an open-source build. Game binaries/source and third-party guide text retain their original rights.
