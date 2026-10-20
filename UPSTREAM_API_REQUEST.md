# Proposed public inspection API additions

This is an unsent technical proposal, not an official game API or implemented feature. No message has been sent to the developer.

The current adapter uses the shipped SCRIPT lifecycle and explicit public getters. Source/compiler/runtime checks establish useful partial coverage, but the following read-only additions would remove remaining gaps without reflection, native hooks or a general method-invocation interface.

| Requested public contract | Needed behavior | Current gap |
| --- | --- | --- |
| Lifecycle observation | Notify scripts before unload to menu, reload, game replacement and exit; specify callback ordering and thread | SCRIPT has load/create/update hooks; GameDisposable is next-init cleanup; engine disposal method is package-private |
| Campaign identity | Public opaque campaign identity with documented persistence across loading/renaming and explicit clone/fork semantics; separate runtime identity | Runtime sessions are available; a reliable cross-load world identifier is not established. City/save names are not identity proof |
| Current application/game phase | Identify standalone menu, new-game configuration, generation, loading, settlement, world, battle and quitting; distinguish loading overlays from actual loader state | SCRIPT instances do not observe standalone menu subpages |
| Active UI context | Read-only ordered list of visible panels/dialogs with stable IDs, titles, modality and selected tabs | Three popup/section roots have bounded public content access; world faction detail/diplomacy-tab presence has a public route. General collection/order and management current tab remain private |
| Current selection | Stable typed IDs for selected subjects, room instances, regions, armies and resources; explicit none/unknown | Subject identity, room blueprint presence and underlying world-faction detail identity are exposed. Topmost selection and exact selected room/region instances are not established |
| Battle phase/result observation | Public read-only deploying/running/concluded/result status, visible result-dialog identity, outcome and callback ordering | Logical deploying and army/engagement data exist; conclusion flag/overlay are private and no arbitrary outcome event feed is mapped |
| Tooltip observation | Final displayed text as read-only text fragments, with owner/panel ID and frame/time | GBox owns private text/render storage; script tooltip callback occurs before normal tooltip construction |
| Versioned data schemas | Discover supported fields, IDs, relations, types, units, enum meanings, null/unavailable semantics and paging for entity/map data | No complete officially documented state enumeration contract established |
| Consistent read batches | Execute bounded read-only selections at a defined game update boundary, returning session/tick/version identity and coverage | Our adapter retains bounded typed entity observations at a source-verified after-update hook; a documented full-game/worker synchronization contract and broader schemas remain missing |

Suggested compatibility rules: feature negotiation, no hidden fallback, explicit unavailable reasons, stable IDs across views, session rotation on load, bounded paging and deprecation notices per supported game build. Background UI selections should be distinguishable from the foreground/topmost context. Observation APIs should not consume input, modify selection, render UI or change simulation state.

The proposal intentionally excludes arbitrary reflection, process memory access, native input, screenshots and privileged control. The source-verified inventory (`api-audit.json`) and current coverage report (`API_ESTABLISHMENT.md`) provide concrete examples and reproducible evidence for the requested additions.

## Mod-owned gesture focus and display validity follow-up

The finite 0.71.44 review in [CHAT_INPUT_BOUNDARY.md](CHAT_INPUT_BOUNDARY.md) finds public pointer/held-state routes, but the inspected GraphicContext.isFocused getter is package-private. Mouse.getCoo returns a mutable engine cache whose coordinates can remain unchanged outside bounds/unfocused. This is not an exhaustive proof that no other public route exists.

A documented in-process API for read-only focus, pointer validity/age and mod-owned capture/release/cancel would let chat panels handle dragging without private access, native input injection, engine coordinate mutation or another widget's click consumption. Detached primitive coordinates with explicit coordinate units and validity would be preferable to a mutable shared handle. Separately, an own-widget visibility/clip/occlusion contract would help validate per-event unread display receipts; a render callback alone is not evidence that an unoccluded reply was seen. Stable save/world identity remains a separate existing request, never inferred from pointer/UI/city names.

The unshipped gesture candidate uses a bounded cancellation policy while these native semantics are reviewed. It does not bypass focus access or claim actual native input acceptance.

The subsequent [source/compiler review](CHAT_VISIBILITY_BOUNDARY_REVIEW.json) and [three-phase native probe](CHAT_VISIBILITY_VALIDATION.json) make the display-validity request concrete: an own reply and overlapping popup both receive drawing callbacks; the public tooltip box can already be empty after drawing; and an activated panel stays activated when hidden UI stops its draws. Request an explicit frame-scoped own-widget clipped/occluded/unknown result rather than treating those flags as human-read proof. These are finite observed limits, not exhaustive absence of another public API. The proposal remains unsent and production remains read-only.
