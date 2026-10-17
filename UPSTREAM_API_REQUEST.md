# Proposed public inspection API additions

This is an unsent technical proposal, not an official game API or implemented feature. No message has been sent to the developer.

The current adapter uses the shipped SCRIPT lifecycle and explicit public getters. Source/compiler/runtime checks establish useful partial coverage, but the following read-only additions would remove remaining gaps without reflection, native hooks or a general method-invocation interface.

| Requested public contract | Needed behavior | Current gap |
| --- | --- | --- |
| Lifecycle observation | Notify scripts before unload to menu, reload, game replacement and exit; specify callback ordering and thread | SCRIPT has load/create/update hooks; GameDisposable is next-init cleanup; engine disposal method is package-private |
| Current application/game phase | Identify standalone menu, new-game configuration, generation, loading, settlement, world, battle and quitting; distinguish loading overlays from actual loader state | SCRIPT instances do not observe standalone menu subpages |
| Active UI context | Read-only ordered list of visible panels/dialogs with stable IDs, titles, modality and selected tabs | Three popup/section roots have bounded public content access; general collection/order and management current tab are private |
| Current selection | Stable typed IDs for selected subjects, room instances, regions, armies and resources; explicit none/unknown | Subject identity and room blueprint presence are exposed, but exact selected room instance is not established |
| Battle phase/result observation | Public read-only deploying/running/concluded/result status, visible result-dialog identity, outcome and callback ordering | Logical deploying and army/engagement data exist; conclusion flag/overlay are private and no arbitrary outcome event feed is mapped |
| Tooltip observation | Final displayed text as read-only text fragments, with owner/panel ID and frame/time | GBox owns private text/render storage; script tooltip callback occurs before normal tooltip construction |
| Versioned data schemas | Discover supported fields, IDs, relations, types, units, enum meanings, null/unavailable semantics and paging for entity/map data | No complete officially documented state enumeration contract established |
| Consistent read batches | Execute bounded read-only selections at a defined game update boundary, returning session/tick/version identity and coverage | Our adapter currently maps a limited set of typed public getters |

Suggested compatibility rules: feature negotiation, no hidden fallback, explicit unavailable reasons, stable IDs across views, session rotation on load, bounded paging and deprecation notices per supported game build. Background UI selections should be distinguishable from the foreground/topmost context. Observation APIs should not consume input, modify selection, render UI or change simulation state.

The proposal intentionally excludes arbitrary reflection, process memory access, native input, screenshots and privileged control. The source-verified inventory (`api-audit.json`) and current coverage report (`API_ESTABLISHMENT.md`) provide concrete examples and reproducible evidence for the requested additions.
