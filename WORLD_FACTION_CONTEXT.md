# World faction panel context

`get_game_ui_context` now includes `context.world_faction_panels`. This is a partial observation through explicit public in-process game APIs, sampled on the same update boundary as exported state. It is available only in an active completed-world view. City, battlefield, editor and preparation views return unavailable with null panel values; retained hidden world panels are not treated as current context.

- `list_open` reports the faction-list panel's membership in the world side panels.
- `detail_faction` contains a confirmed `faction_id` and stored `diplomacy_tab` boolean, or null. The ID joins diplomacy `/factions` rows through `/id` in the same snapshot.
- `scanned_factions`, `faction_limit` (1,000), `failed_factions`, `truncated`, `matched_detail_factions` and `identity_search_complete` qualify the identity search. More than one match produces null and an ambiguity reason. Incomplete searches do not turn missing identities into an absence claim.

The underlying list/detail can remain present behind a confirmation or hidden UI. Switching factions preserves the stored diplomacy tab. Returning to the world view can clear its panels; reopening restores the retained tab. Presence does not identify the foreground/topmost selection, clipping, occlusion, proposed deal, accepted trade or a complete diplomacy tab hierarchy. Inspect `active_view`, `ui_hidden`, `known_overlays` and the scope/reason fields before interpreting the user's “this.” IDs belong to the observed campaign/session; do not carry a selected faction across reloads.

After confirming a non-null detail object, use [world-faction-query-example.json](world-faction-query-example.json) for a same-observation diplomacy selection. A context expression traversing a null/missing detail object is rejected as an absent path; do not issue that expression when no detail exists. `include_ui_context` returns the context of the actual selected snapshot. Pinning a previously observed snapshot is optional and strict; a mismatch must be retried intentionally.

## Provenance and validation

[UI_LIFECYCLE_BOUNDARY_REVIEW.json](UI_LIFECYCLE_BOUNDARY_REVIEW.json) checks the route `VIEW.world().UI.factions` and the three public `openIs`/`diploIs` observers in the paired licensed JAR/source. It fingerprints selected method bodies, checks direct read operations and compiles a positive public-route probe. These are shipped-source/binary findings, not separately documented stable official mod contracts. Panel membership iterates the existing side-panel list; the production faction scan has a separate 1,000-item bound and retains only one detached identity row. Getter failures omit the whole row, preserving null versus false.

Reproduce the static checks without starting the game:

```sh
.venv/bin/python dev/review_ui_lifecycle_boundary.py \
  --game-dir "$SYX_GAME_DIR" --jdk-home "$SYX_JAVA_HOME"
```

The default catalog is the local `build/game-api-catalog.json` described in API_DISCOVERY.md. A different licensed game/source pair is refused until reviewed with a matching catalog.

The same finite review checks misleading alternatives: `UIRoom.detailIns()` has no established public route to the live `UIRoom` object; `UIRegions.get(region)` binds/mutates panels; `GBox.text()` advances/clears pooled builder state. Compiler probes reject the named private/package accesses and an external engine-disposal subclass. SCRIPT declarations expose no unload hook, and `GameDisposable` disposal occurs at next GAME construction. These checks do not prove no other public route exists. Tooltip text, selected room/region, complete panel/tab ordering and immediate menu unload remain unestablished. The existing up-to-30-second freshness limitation remains.

[WORLD_FACTION_CONTEXT_VALIDATION.json](WORLD_FACTION_CONTEXT_VALIDATION.json) pins eleven successful native phases and actual MCP checks. The copied-game runner is `dev/run_read_fixture.py --case faction-ui` with the licensed game/JDK/Java/copied-save arguments from CONTRIBUTING.md, plus candidate arguments when testing an unpublished build. It uses the shared fixture lock, restores its copied mod and checks the copied save. Test-only panel/view changes are not packaged or exposed as MCP actions. The fixture verifies city unavailable; world closed; list; first detail; diplomacy tab; another faction; confirmation over detail; city with retained hidden world panels; world return clearing panels; reopened detail; closed panels. Actual MCP selections join the confirmed context ID with diplomacy rows in the same observation. Missing detail paths are explicitly rejected. It does not establish all factions/scenes, cap/fault injection or large-city cost.
