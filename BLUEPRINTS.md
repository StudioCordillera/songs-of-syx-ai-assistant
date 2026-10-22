# Original blueprint references

The paired tested player build includes these original reference tools. [Release evidence](BLUEPRINT_RELEASE_VALIDATION.json) separates the native-player Pro checks from the [synthetic-context production-reference Pro checks](BLUEPRINT_REFERENCE_PRO_VALIDATION.json). The previous tested ZIP is retained for rollback.

Ask the assistant to search for an original warehouse teaching layout, then explain the discovered example and cite its immutable source. The model can search short summaries first and retrieve just one selected grid. The default MCP entry point adds `search_blueprint_examples` and `get_blueprint_example` to the nineteen state/guidance tools; both new tools are read-only, idempotent and independent of the loaded world's state. The low-level `create_server` factory retains its nineteen-tool base for explicit developer extensions.

The first example is an original five-by-five interior sketch with two two-by-one furniture footprints. The public native catalog probe reviewed one warehouse item on 0.71.44. The example's orthogonal aisle/adjacency checks are authored geometry, not game construction or pathfinding. No actual door, walls, roof, exterior terrain, capacity, materials, staffing, throughput, efficiency or optimum is established. No placement or gameplay command exists. Matching version text does not attest the player's installed mods/catalog; other versions remain unknown.

Each exact original example cites immutable published explanation/corpus/catalog URLs and checksums. A moving main-branch link is navigation only. The catalog's original review date and installed game/source hashes stay visible in tool evidence; packaging does not refresh that historical native review. These are project-authored examples and finite shipped-source/public-API checks, not an official stable construction contract. No third-party layout/image/video is copied or granted a redistribution license.

The production Python modules embed the exact already-public original corpus and catalog-report bytes so extracted players and installed distributions do not depend on the repository's developer files or current working directory. `syx_blueprints.py` validates the bounded registry, `syx_blueprint_tools.py` registers fixed typed requests with actual UTF-8 limits, and `syx_blueprint_chat.py` admits/rechecks the two declarations for each turn. It retains the existing game-session/history/cancellation limits and plain-player policy. Provider/account expansion stays deferred.

For an MCP client, discover the tool schema and send nested typed requests:

```json
{"request":{"query":"warehouse aisle","game_version":"0.71.44","limit":3}}
```

Then request `get_blueprint_example` with `request.example_id` from the results and an explicit `request.game_version`. Search omits geometry. Neither tool infers a UI-selected target or claims live placement feasibility. Tool evidence stays in private history; the player receives normal prose and source links.

Historical developer evidence is mapped in BLUEPRINT_EXAMPLES_CANDIDATE.md. Current candidate/release acceptance must separately establish actual entry-point/provider/coordinator behavior, extracted distribution, native core/connection/focus checks and exact-source pairing. A design prototype, synthetic demo or fake-provider workflow cannot substitute for those gates. More useful independently reviewed examples, external-source rights/geometry review and the broader UI/copilot execution revision remain open.
