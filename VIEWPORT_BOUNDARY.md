# Cached viewport routes: reviewed candidate

Public in-process window routes are source/compiler reviewed and exercised in a disposable copied game. This file preserves the original candidate review. The subsequent production mapping is described in [CACHED_VIEWPORT.md](CACHED_VIEWPORT.md) and [VIEWPORT_VALIDATION.json](VIEWPORT_VALIDATION.json); the earlier candidate report keeps its original hashes and scope. No hovered tile is identified from these caches.

| Context | Public route | Source-bound coordinate space |
| --- | --- | --- |
| City | `VIEW.s().getWindow()` | Instantiated settlement tiles/pixels |
| City tactical HUD | `VIEW.s().battle.getWindow()` | Instantiated settlement tiles/pixels, separate window object |
| Generated battle | `VIEW.b().getWindow()` | Instantiated battlefield tiles/pixels, separate window object |
| Campaign world | `VIEW.world().window` | Campaign world tiles/pixels, not city coordinates |

The reviewed `tiles()`, `pixels()`, `view()` and `zoomout()` readers return stored window references/scalars. A future observer must immediately copy primitive values on the game update thread; mutable engine rectangles must not escape into MCP or worker threads. These are shipped-source/binary verified public members, not separately documented stable mod contracts.

`pixels()` returns the rounded `Pixels2` cache. `tiles()` is separately cached using integer conversion of pixel boundaries; it is not a conservative list of every rendered/intersecting edge tile. Rectangles can extend outside map bounds. The screen rectangle uses **internal UI coordinates**, not established OS/screenshot pixels. These caches establish neither clipping/occlusion nor what the player actually sees above another panel. Clip any future query bounds to the correct observed map and retain partial/empty semantics; never call the result a complete visible census.

## Freshness and excluded methods

The shipped `GameWindow.update` returns early when management is open. The native fixture confirms a stronger caution: a public test-only zoom action can change the reported zoom while both cached pixel/tile rectangles remain unchanged. Getter success therefore does not prove coherent current geometry. Closing management and applying a public camera update restores the tested pixel/screen scaling.

Exact cache age and a nonconsuming freshness/hover notification are not established. Production must not call `update`, a setter or an input consumer to repair caches. A future mapping needs explicit management/view/scene/session guards and cached-state semantics even in other contexts. Modals and hidden UI can obscure an underlying viewport.

`tile()` returns cached sub-mouse coordinates; it is not selected/hovered tile identity. Its private `hovered` flag is inaccessible to an ordinary external caller. `consumeHover()` clears that flag, `hover()` consumes wheel/click state, and the zoom-change consumer clears its flag. None is a read-only observer. No pointer movement or input injection is used by this review/fixture.

`VIEW.hide()` sets hidden UI **true**, rather than toggling it. The fixture's first attempt incorrectly expected a second call to restore UI; that run was rejected. The corrected test puts hidden UI last and never injects input or accesses a private flag to reset it. The inspected methods do not establish a public nonconsuming unhide route; this is not an exhaustive absence-of-API proof.

## Evidence

[VIEWPORT_BOUNDARY_REVIEW.json](VIEWPORT_BOUNDARY_REVIEW.json) pins the licensed source/JAR pair, declaration catalog, external positive compiler probe for all four routes, negative private-hover probe, selected stored-reader disassembly hashes and consuming-method exclusions. Direct selected readers have no heap writes, allocation, backward branches or calls. This finite check is not formal transitive purity, third-party override acceptance or a timing/availability guarantee. Proprietary source/bodies are not redistributed.

[VIEWPORT_CANDIDATE_VALIDATION.json](VIEWPORT_CANDIDATE_VALIDATION.json) records eleven controlled native phases: city baseline; shift/zoom; management cache mismatch; management close/refresh; city tactical HUD; campaign world; world confirmation; city return; generated battle deployment; battle menu; hidden battle UI. Native checks compare repeated cached reads, refreshed pixel/screen scaling, four distinct window handles and the management mismatch. Additional pinned source inspection establishes that WORLD pixel dimensions use tile dimensions times the same tile-size constant.

Eleven accepted **existing MCP context** observations agree with the fixture's view/management/modal/menu/hidden flags. Geometry is recorded only by the native fixture: **zero production viewport MCP calls** are claimed. This is not renderer/screenshot ground truth, a selected-room/tile getter, a full UI hierarchy, all-display/mod/menu acceptance, combat, natural camera motion, cost or instant unload detection.

The shared native lock, path-validated copied profile/save, explicit clean-completion marker, finite crash-marker guard, copied-mod restoration and unchanged copied-save checks pass. Test-only public camera/view/menu/hide and battle-setup actions are excluded from production. The developer follow-up passes 305 offline tests, with no inference. Normal profile, saves, credentials and latest/previous tested player payloads remain unchanged; prior player/provider reports keep their own dates/hashes.

## Original implementation gate — subsequent mapping linked above

A useful next mapping is explicitly cached viewport geometry for supported active views, with unavailable management/unsupported contexts, correct city-versus-world/battle units and same-observation provenance. Decide carefully whether reported engine tile bounds or an explicitly derived/clipped selection is needed; neither establishes all rendered tiles. Do not export cached mouse coordinates as a hover/selection fallback.

Before shipping: implement primitive DTOs and source-backed field/capability definitions; validate native getter-to-MCP geometry parity, predicates/joins/query-bound use and unavailable contexts; review bounds and costs; run the current-source build/core/Pro/distribution gates and promote the tested bundle. The candidate reports do not establish that these production steps have happened.

## Reproduce

Use the licensed paths/copied-profile setup from [CONTRIBUTING.md](CONTRIBUTING.md):

```sh
.venv/bin/python dev/review_viewport_boundary.py \
  --game-dir "$SYX_GAME_DIR" --jdk-home "$SYX_JAVA_HOME"
.venv/bin/python dev/run_read_fixture.py --case viewport \
  --game-dir "$SYX_GAME_DIR" --save runtime/smoke.save \
  --java "$SYX_GAME_JAVA" --jdk-home "$SYX_JAVA_HOME"
```

The static review never initializes game classes. The native fixture uses only public in-process actions in its disposable game process; it does not use screenshots, reflection, process memory, OS/native input automation or provider calls. Raw geometry and logs stay private under ignored `runtime/`.
