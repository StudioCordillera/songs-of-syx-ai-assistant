# Original blueprint teaching example — developer candidate

This candidate begins a structured example registry for the requested [blueprint/reference feature](PLAYER_EXPERIENCE_PLAN.md). It contains one original five-by-five warehouse interior sketch, with explicit catalog evidence and uncertainty. It is separate from the production fifteen-summary guidance corpus, installed help and MCP tools. A later developer-only MCP wrapper is described below. No player example browser, Workshop importer, video reconstruction or construction command is shipped.

The example is authored for this project. It copies no user save layout, third-party blueprint, game sprite, screenshot, video or guide. The repository has no selected redistribution license; the record makes no additional license grant. [Earlier third-party discovery](BLUEPRINT_REFERENCE_CANDIDATES.md) remains leads, not reviewed layouts or rights evidence.

## The authored example

`warehouse-two-items-teaching-grid` illustrates two small furniture footprints with an intended connected aisle. Coordinates are relative to the interior rectangle, starting at its upper left; the furniture origins are (1,1) and (1,3), with rotation zero. The entry at (0,2) is hypothetical. Walls, doors, roofing, building materials and exterior terrain are not modeled.

```text
.....
.RF..
E....
.RF..
.....
```

`R` is a catalog furniture tile whose public `mustBeReachable` flag is true. `F` is the other reserved furniture cell; `.` is authored empty aisle space; `E` is the hypothetical entry. This is two furniture instances and four occupied footprint cells. It is **not** a claim of two crates, a storage capacity, a bill of materials, staffing, throughput, construction legality or optimal design.

The original grid has 21 nonblocked cells connected under an authored four-neighbor flood check, and each required-access furniture cell adjoins that connected space. This is elementary rectangle geometry. It does not run the engine's pathfinder, test real door/exterior connectivity or prove a legal placement/building.

## Exact installed catalog evidence

[BLUEPRINT_CATALOG_VALIDATION.json](BLUEPRINT_CATALOG_VALIDATION.json) pins a fixed public catalog probe against the installed 0.71.44 game/source pair and unchanged player. On the update thread it reads the warehouse's public constructor, first placement group and first size at rotation zero, copying only item identity, dimensions, occupied tile IDs, blocker/access flags and the indoors requirement. The observed item index is **1**; the group/size selectors do not imply item index zero. The selected footprint is 2×1; both cells report blockers and only the first reports required access. External Java 16 compilation and the native fixture establish public accessibility, not a separately documented stable furnishing contract.

The fixture creates or places no room/item, invokes no placement helper or pathfinder, calculates no resource/capacity formula and makes no provider request. The source's storage/decorative sprite names are not used to infer quantities or efficiency. The clean completion/zero-exit/crash-marker and copied-mod/save integrity gates apply to this exact native run. Source text, sprites and raw saves remain private; only selected factual metadata, checksums and our conclusions are published.

## Discover first, request geometry explicitly

`dev/blueprint_examples.py` and [the candidate register](blueprint-examples-candidate.json) implement a detached, bounded original-example registry. `search(query, game_version, limit=5)` returns short summaries and compatibility, without geometry. `get(example_id, game_version)` returns that example's original geometry, selected catalog facts, author/source, rights statement, evidence checksums, materials uncertainty and caveats. Both paths explicitly report no construction/execution validation.

```python
from dev.blueprint_examples import load_registry
examples = load_registry()
hits = examples.search("warehouse aisle", "0.71.44")
example = examples.get(hits[0]["id"], "0.71.44")
```

Other numeric versions receive unknown compatibility, while preserving the original reviewed version. Matching version text alone cannot attest an actual player's mods/catalog. The source URL points to this project's authored explanation, not an invented community citation. The corpus pins the exact native report checksum, including its source/game hashes and review date. Checksums bind reviewed repository artifacts; they are not a cryptographic signature or proof that an arbitrary supplied report was produced by the engine.

The initial schema deliberately admits only original project examples using this selected item contract. Unknown/action fields, another origin, ambiguous duplicate JSON keys, nonfinite constants, Boolean-as-number values, bad identities/evidence checksums, footprint overlap/out-of-bounds, invalid entry, disconnected intended aisles and missing adjacent required access refuse. Input files are at most 128 KiB each; records are capped at 100, dimensions at 64×64 and placements at 128. Returned results own their copies. The registry itself has no network fetch, decompression, external importer, MCP registration, game handle, worker traversal or execution route. The later wrapper below registers only developer reference tools; production remains unchanged.

[Candidate validation](BLUEPRINT_EXAMPLES_VALIDATION.json) distinguishes synthetic registry checks from the native catalog report. These checks do not validate arbitrary external layouts or mechanical advice. Future community/video examples need source/author/version/timestamp/rights review and explicit geometry uncertainty; broader room items need new public catalog contracts. A usable recommendation and an executable construction plan remain separate acceptance gates.

Reproduce the native catalog with `dev/run_blueprint_catalog.py` and the isolated licensed-game arguments in [CONTRIBUTING.md](CONTRIBUTING.md), under an appropriate display. The runner uses the shared native lock and copied profile. Reproduce offline checks with `.venv/bin/python -m pytest -q test_blueprint_examples_candidate.py`. Re-running a report changes its date/checksum; deliberately re-review/re-pin the corpus rather than bypassing the checksum refusal. The current/previous tested player downloads, credentials and normal saves stay unchanged.


## Developer MCP wrapper — not the player server

`dev/blueprint_mcp_candidate.py` now wraps the unchanged production server factory with two additional **read-only developer tools**. The candidate lists 21 tools: the original nineteen tool definitions remain identical, plus `search_blueprint_examples` and `get_blueprint_example`. The published server, coordinator's fixed tool admission and player ZIP still use their existing nineteen tools. No production assistant access or paid provider behavior is implied by this candidate.

Configure a developer stdio MCP client to run `.venv/bin/python -m dev.blueprint_mcp_candidate` from the repository, with `SYX_STATE_DIR` pointing to an existing disposable subdirectory under this repository's `runtime/`. The CLI refuses an omitted/default home path, the runtime root itself, outside directories and symlink hops. No snapshot is required for reference retrieval. No key is needed or read. The inherited game tools are unchanged and still require their ordinary source/freshness/request contracts; the wrapper does not turn a teaching grid into a game action.

The tools require nested typed request objects, for example:

```json
{"request":{"query":"warehouse aisle","game_version":"0.71.44","limit":3}}
```

Then request just the discovered example:

```json
{"request":{"example_id":"warehouse-two-items-teaching-grid","game_version":"0.71.44"}}
```

Request objects forbid unknown fields and coerced Boolean/string limits. The get ID cannot be a file path. Explicit numeric version text is a comparison against the reviewed catalog, not attestation of a loaded world's version, mods, UI context or placement feasibility. Search exposes the reviewed version and summaries without geometry; get returns source/author/rights/evidence and the original grid. Other versions retain unknown compatibility. Responses identify `developer_reference_catalog_no_live_state`, report no construction/execution support, and invent no snapshot/session/selected target.

New results are literal JSON text capped at 65,536 actual UTF-8 bytes before returning MCP text content; overflow refuses rather than silently trimming geometry or caveats. The tests separately check Unicode near the wire bound. No receipt, chat send, registry write, file fetch, arbitrary invocation or build action is added.

[Developer protocol evidence](BLUEPRINT_MCP_CANDIDATE_VALIDATION.json) records actual stdio listing and eight calls: summary/get, another version, no match, unknown ID and three invalid nested request shapes. All nineteen original tool definitions match a separately instantiated production server. No snapshot is supplied, which verifies that reference results are not invented live game/UI evidence. Unit cases cover schema and UTF-8/path isolation. Historical registry/native reports above retain their original scope; no fresh native, paid Pro or player release is claimed here. Integrating these tools with the actual coordinator/player still requires a reviewed paired source-matched release.


## Developer conversation admission seam

`dev/blueprint_chat_candidate.py` now provides an opt-in `BlueprintConversation` subclass for developer integration. It uses the unchanged production conversation loop/history lifecycle and base nineteen-tool allowlist. A small provider wrapper supplies the two separately admitted reference schemas to that turn's provider; it does not change globals, the production coordinator, CLI or player. Providers remain caller-supplied. The current evidence uses a deterministic fake provider, with zero paid inference and no claim of DeepSeek accepting the extended schemas or producing correct blueprint advice.

Admission requires both reference tools exactly once, with read-only/idempotent/non-destructive/closed-world annotations. Each reference call validates the nested request locally and rechecks the admitted tool definitions before dispatch. Missing, duplicated, changed or writable declarations refuse; unrelated names retain the base allowlist's refusal. Results keep the existing 64-KiB serialized chat-evidence budget, which includes the MCP envelope and can be stricter than a tool's text-only bound.

Each turn has its own task-local grant. Cleanup revokes it on completion/cancellation, including inherited child contexts; the finite late-child test cannot issue another reference read. Concurrent chats retain separate grants/providers and durable history. This is finite cooperative async evidence, not a general malicious-provider, arbitrary detached-task or remote-server security audit. An already dispatched external request is not undone by grant revocation.

The parent loop still requires fresh matching session status before inference and before each tool call; the reference seam adds no fake live-state bypass. Admission has its own five-second window before durable turn start; subsequent provider work uses the inherited conversation timeout/tool-round/call limits, cancellation, redaction and provider-close behavior. No fallback model, hidden paid retry or construction authority is introduced.

[Conversation evidence](BLUEPRINT_CHAT_CANDIDATE_VALIDATION.json) separates synthetic admission/lifecycle cases from one actual stdio integration with a deliberately **synthetic demo snapshot**, a generated session UUID and current fixture timestamp. Three fake provider rounds request summary/get and then complete. The two original-reference results pass through real MCP and durable chat evidence, retaining the original grid and no-construction/no-execution qualifiers. The demo's game version remains unverified; its timestamp is fixture data, not a fresh real-game observation. No normal history/save or game process is used. Real provider, coordinator/native UI and source-matched player promotion remain required gates.


## Explicit paid Pro follow-up — still developer-only

`dev/run_blueprint_pro_check.py --env-file .env` is an explicit paid check, separate from pytest/CI. It reads the private literal key file, requests `deepseek-v4-pro`, and uses a fresh private directory under `runtime/`. The key stays in the provider process and redacted private history; it is not given to the MCP child, game or published evidence. Do not run this command as an offline check or retry a returned quota/model/credential gate automatically.

[Pro evidence](BLUEPRINT_PRO_CANDIDATE_VALIDATION.json) records two completed user turns, five successful API round trips with 21 schemas, and three actual reference calls: summary search, exact-version get and another-version get. Both final replies cite the original source URL and 0.71.44, and the second retains unknown compatibility for 0.72.0. Durable get results preserve the original grid/catalog evidence and false construction/execution flags. A finite manual review of these two visible replies checks the stated coordinates/geometry, source/version and uncertainty; it does not establish broad semantic advice quality or unscripted retrieval accuracy.

The context remains a deliberately synthetic demo, with a fresh fixture UUID and a once-per-second **synthetic** timestamp heartbeat so the unchanged conversation freshness checks can run during inference. No native observation is refreshed or relabeled, no game process is launched and no real world, UI selection or clock progression is attested. The explicit requested API model is recorded; the streaming adapter does not independently attest the remote model's identity. There is no model/account fallback, runner retry or credit purchase.

The production coordinator/player remains unchanged. This result closes the finite developer provider-schema/transport gap described above; it is not a promoted player build, native client/Stop/background acceptance or construction test. The earlier fake-provider and catalog reports retain their historical scopes. Three offline runner-control tests replace inference with fakes and check success/noncompliance/source-change rejection and cleanup without reading a key or making a paid request.
