# World list-panel context

`get_game_ui_context` exposes `context.world_list_panels` from the same observation as its state identity. `select_game_state` can project the same fields with context expressions and an expected snapshot pin. The three flags identify known activated side-panel-manager membership:

| Field | Public route | Meaning |
| --- | --- | --- |
| `army_list_present` | `VIEW.world().UI.armies.listIsOpen(VIEW.world().panels)` | The known army list belongs to the activated world side-panel manager. |
| `player_realm_list_present` | World `panels.added(UI.regions.playerList)` | The known Realm panel belongs to that manager. |
| `region_browser_present` | World `panels.added(UI.regions.allList)` | The known Regions browser belongs to that manager. |

These are presence flags, not selected army/region identities, list contents, search/sort state, a complete hierarchy or topmost/rendered visibility. A confirmation or hidden UI can obscure underlying true flags. Inspect the same observation's `active_view`, `ui_hidden`, `known_overlays` and `reference_resolution`; clarify an ambiguous user reference instead of guessing which object they mean.

## Availability and source meaning

Only the active completed-world view produces `coverage: partial` with boolean flags. A completed membership check that does not find its panel returns **false**. Inactive city/editor, incomplete world, uninitialized view or a reader failure returns `coverage: unavailable` and **null** for all three flags, with a reason. Unknown does not become closed=false. The editing workflow flag can persist after returning to the world; actual active view and world completion govern availability.

The public `ISidePanels.added` reader first requires manager activation and then compares panel identity in its private engine collection. Our adapter invokes the public getter only; it does not access that collection. The pinned source/binary review establishes a fixed 16-slot collection, so these three readers have at most 48 membership comparisons in this implementation. That is a source-backed bound, not a measured FPS or worst-case whole-collector guarantee.

The source `playerList` row builder skips realm index zero; `allList` excludes the player capital and has its own filtering/sorting. Neither presence flag establishes a complete census or a foreign-only listing. Read actual world-domain rows for campaign data; do not infer those rows are currently displayed in a list.

These routes are **shipped-source/binary verified public members**, not separately documented stable mod contracts. [WORLD_LIST_BOUNDARY_REVIEW.json](WORLD_LIST_BOUNDARY_REVIEW.json) pins compiler access, selected reader/constructor disassembly, source hashes, fixed collection capacity and explicit limits. Existing SCRIPT contracts and inaccessible selection/lifecycle routes remain distinct in [API_ESTABLISHMENT.md](API_ESTABLISHMENT.md). No opening/binding/hide action is used in production.

## Same-observation queries

[world-list-context-query-example.json](world-list-context-query-example.json) projects campaign IDs alongside the three flags and includes the original UI context. It illustrates shared observation provenance; it does not identify a selected region. Obtain `snapshot_id` from current status/context and supply `expected_snapshot_id` to reject a changed observation. Never join an older UI context to newer data as though simultaneous. Main-menu identity and instant unload remain unestablished; the existing up-to-30-second freshness limitation still applies.

## Validation and reproduction

[WORLD_LIST_CONTEXT_VALIDATION.json](WORLD_LIST_CONTEXT_VALIDATION.json) pins fourteen copied-campaign phases: inactive city, closed world panels, individual lists, three simultaneous lists, confirmation over lists, inactive retained world panels, world return, completed-world editor, return with editing flags retained, reopening/closing and hidden UI. Each phase compares independent public getters with MCP context and same-snapshot selective projections, including false versus unavailable/null. The separate current core scene checks retain null fields through city/tactical/battle/menu/reload/generation phases. Native fault injection, every popup/mod/display, selected identities and complete UI hierarchy remain unestablished.

Use the copied-game setup and licensed paths from [CONTRIBUTING.md](CONTRIBUTING.md):

```sh
.venv/bin/python dev/review_world_list_boundary.py \
  --game-dir "$SYX_GAME_DIR" --jdk-home "$SYX_JAVA_HOME"
.venv/bin/python dev/run_read_fixture.py --case world-lists \
  --game-dir "$SYX_GAME_DIR" --save runtime/smoke.save \
  --java "$SYX_GAME_JAVA" --jdk-home "$SYX_JAVA_HOME"
```

The static review requires the local declaration catalog from `catalog_api.py` and never initializes game classes. The native runner takes the shared fixture lock, validates paired source/bundle/game, restores the copied mod and checks the copied save unchanged. Public UI/view/hide actions occur only in that disposable process; no native input, screenshot, reflection or inference is used.

The first fixture attempt reached all observations but raced past its last acknowledged phase during teardown; its apparent zero exit was not accepted as a complete pass. The corrected fixture waits for the verifier's final marker and emits explicit clean-completion/failure markers. Read/core runners additionally reject known engine crash/fixture-failure log markers even when process exit is zero. Normal captured-stderr shutdown messages alone are not failures, as confirmed against the shipped engine's error handling. These finite guards do not detect every possible engine failure. No historical run is relabeled with the stronger gate.
