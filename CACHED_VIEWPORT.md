# Cached viewport observations

`get_game_ui_context` now includes `context.cached_viewport` in the tested production mapping. This is a small detached observation of public `GameWindow` caches, sampled on the game after-update thread. It does not refresh the camera, read a pointer, consume input or identify selected/hovered tiles. The readers are verified against shipped 0.71.44 source/binary and external compilation, not separately documented stable game API contracts.

Supported active routes are the city window, the separate city tactical window, the generated battlefield window and the completed campaign-world window. The world route has campaign-world coordinates; the other three use the currently instantiated settlement/battlefield map. Loading overlays, management and unsupported views return `available=false`, `coverage=unavailable` and `data=null` with a reason. Management is refused because the native fixture demonstrates that zoom can change while its rectangle caches stay frozen. World generation, editor views and standalone-menu identity are not inferred from another window.

With supported cached data, `available=true` means that the stated caches were read, not that the camera is fresh or visible. Hidden UI retains its cached underlying camera with `ui_hidden=true`; a known modal/menu is recorded by `known_overlay_active`. `cache_age_known=false` and `rendered_visibility_known=false` remain explicit in every available observation. No panel-occlusion, clipping or renderer/screenshot ground truth is established.

| `data` field | Meaning |
| --- | --- |
| `tiles` | Stored engine tile rectangle, `[x1,y1,x2,y2]`, upper bounds exclusive. Integer conversion is not a conservative census of every rendered/intersecting edge tile. |
| `pixels` | Rounded stored map-pixel rectangle in the same map as `coordinate_scope`. These are not desktop pixels. |
| `screen` | Stored internal UI rectangle, not established physical display/OS coordinates. |
| `zoomout` | Public stored zoom-out value. It is not a proof of coherence with every other cached rectangle. |
| `map_bounds_tiles` | `[0,0,map_width,map_height]` for the stated coordinate space. It is not the camera or a selected area. |

Rectangles can extend beyond map bounds and negative coordinates are preserved. If an explicit later map query is appropriate, intersect the desired rectangle with its matching map bounds and preserve empty/partial semantics. **Campaign-world camera bounds must not be passed to the settlement/battlefield tile reader.** A separate live read is a separate observation, even when it uses previously observed bounds. Neither route establishes path feasibility, construction suitability, selected-room identity, every visible tile or permission to act.

[The example](viewport-context-query-example.json) projects the whole cached-camera observation beside one bounded world-region row through existing context expressions. Inspect current status, source availability and coordinate scope first; pin the actual snapshot ID when consistency matters. `include_ui_context` returns context from the same selected observation. Unavailable source domains refuse instead of becoming an empty inventory or a zero rectangle. `get_game_api_support("cached_viewport_geometry")` describes the public routes, source evidence and limits without a loaded snapshot.

## Evidence

[VIEWPORT_BOUNDARY_REVIEW.json](VIEWPORT_BOUNDARY_REVIEW.json) retains the original licensed source/JAR pairing, positive external compilation, stored-reader disassembly and exclusions for hover/input consumers. [VIEWPORT_CANDIDATE_VALIDATION.json](VIEWPORT_CANDIDATE_VALIDATION.json) remains the earlier fixture-only eleven-phase report, with its original hashes and zero production-geometry MCP acceptance.

[VIEWPORT_VALIDATION.json](VIEWPORT_VALIDATION.json) records the newer candidate's production DTO/MCP checks. Ten available geometry observations match independent public getter samples on the **same game-update tick**, and the management phase returns null/unavailable. Eleven same-snapshot selective context projections match their direct MCP context observations. City movement/zoom, management mismatch/recovery, tactical, world/modal, generated deployment, menu and hidden-UI cases remain finite tests, not all display/mod/menu/combat coverage. Production caches may legitimately move between updates: the initial one-time phase-baseline comparison was rejected and replaced by bounded same-tick getter samples before test-only phase mutations. No production camera was refreshed to make the test pass.

Current-source core scene/extended-context verifiers additionally check supported/unavailable viewport semantics across their held scenes, including world preparation and editor/setup contexts. Real Pro chat, focus/automatic connection, background replies, collector/encoding cost and extracted distribution retain separately pinned reports. The matching tested candidate completed those gates and is promoted as latest-user-test.zip, retaining the prior tested ZIP. Large-world costs, exact cache age, topmost visibility, hovered/selected objects, immediate unload detection and exhaustive variables/menus remain open.


## Source review and local Claude critique

A bounded local Opus/high critique completed on actual `claude-opus-5-5` (47220 ms, one reported turn). Its map-binding concern is addressed by the complete response contract: MCP returns the same observation's `state.scene` alongside context, including city/battlefield kind. A camera object alone is not a durable area identity; carry scene/session/time and revalidate later explicit queries. The claimed absent subject-panel guard was disproved by tracing `UISubjects.current()` to `UISubject.showing()`, which checks panel membership. Underlying membership still cannot establish unobscured visibility. The deployment rectangle uses named keys, while the new camera vectors explicitly state order; changing that legacy shape is unnecessary, and the public rectangle point-membership semantics exclude upper bounds. No production behavior was changed merely to match these critique proposals.

[CACHED_VIEWPORT_CONTRACT_REVIEW.json](CACHED_VIEWPORT_CONTRACT_REVIEW.json) pins the full-envelope, subject-panel, rectangle and paused-tick source checks separately from native evidence. It publishes hashes/names/conclusions only and executes no game methods. This finite source trace and marker check is not formal transitive purity, arbitrary unpaused tick uniqueness, full call-graph coverage or a new official contract. [Claude metadata](CLAUDE_UX_COLLABORATION.json) records actual model, outcome and exact input hash; no credits purchased or limits bypassed.
