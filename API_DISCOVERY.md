# Public declaration discovery — game 0.71.44

The production reference audit proves only the public members used by our adapter. To identify remaining mapping work, `catalog_api.py` separately scans the entire shipped source archive and resolves its named types and public declared members against the installed game JAR with the Java compiler. It never starts the game, executes its classes, or uses reflection. This is development tooling, outside the packaged mod and MCP server.

The current scan covers 2,443 source files, resolves every cataloged named top-level/member source type, and finds 2,052 public types with public enclosing types and 17,442 public declared member signatures. All 446 production reference IDs occur in this catalog. Matching game JAR/source archive hashes establish that the discovery run and production audit used the same reference pair. They do not attest the installed/running mod.

| Root package | Public declared member candidates | Production reference IDs |
| --- | ---: | ---: |
| settlement | 6,606 | 167 |
| snake2d | 2,817 | 40 |
| game | 2,295 | 63 |
| init | 1,726 | 57 |
| util | 1,664 | 24 |
| world | 1,212 | 30 |
| view | 1,006 | 65 |
| launcher | 69 | 0 |
| script | 28 | 0 |
| menu | 11 | 0 |
| integrations | 7 | 0 |
| cutscene | 1 | 0 |

These are not variable counts or a completion percentage. Constructors, setters, renderers, collections and utilities are included. Script overrides are documented separately; zero referenced `script` members does not mean no SCRIPT integration. Local/anonymous implementation classes are outside this catalog. Inherited declarations are listed at their declaring owner. Public inherited members declared by an inaccessible owner and JAR-only types absent from shipped source are outside this catalog's enumeration scope. Public signatures can themselves involve inaccessible types. Object availability, purity and safe invocation are not established by a declaration.

16,932 members have one source anchor matching owner, name and simple parameter type strings; 510 do not. This lightweight matching does not prove fully qualified type equivalence or method-body equivalence. Unmatched entries include generated enum methods, implicit constructors and different source/binary spelling of nested types. They are retained with explicit missing-anchor status; they are not promoted to source-verified getter contracts. The stricter production audit remains authoritative for adapter references. No method bodies, Javadoc text or game values are included in either the full local metadata output or the checked-in summary.

## Reproduce and search

Use a complete JDK 17+ (`SYX_JAVA_HOME` may select one):

```sh
python3 catalog_api.py --game-dir '/path/to/Songs of Syx'
python3 catalog_api.py --query 'world.regions' --limit 10
python3 catalog_api.py --query 'menu.Menu' --offset 0 --limit 10
```

The full metadata stays at `build/game-api-catalog.json`; the smaller reproducibility summary is `API_DISCOVERY.json`. Search reads only this local metadata, applies case-insensitive AND terms to member identity/return type, and bounds pages to 30 records/64 KiB. It does not invoke the selected member or expose an arbitrary runtime method tool.

`test_api_catalog.py` builds an independent synthetic binary/source pair. It checks public enclosing-type access, implicit public interface members, overloaded signatures, source hashes/lines/Javadoc presence, inheritance ownership, generated-method anchor gaps and exclusion of bodies/comments. Its static initializer throws if the inspected class is executed; catalog generation completes without running it.

## Lifecycle finding and next mapping work

The public compiled declarations for `snake2d.CORE` and `CORE_STATE` provide no current application-state getter. The shipped source holds transition state/updater details privately. `menu.Menu` exposes factories and update/render/input methods, but no public singleton/current-menu getter; constructing a new menu would mutate the process and would not inspect its current menu. `VIEW.existTemp()` only checks an existing static VIEW reference; its implementation is not evidence that VIEW is the engine's active state. None supplies an immediate read-only unload observer, so the stale/unknown fallback remains.

This finding is scoped to these inspected classes and the earlier SCRIPT/disposal review. It does not prove that no other public lifecycle mechanism could exist. Continue targeted review of object entry points and thread contracts before making a broader claim.

For each useful candidate, remaining work is to establish a public route from the loaded game's objects, review getter implementation/thread/units semantics, write a bounded typed mapping, extend the production audit, and validate actual game behavior. Priority areas remain entity relationships, non-entity data, broader consistent typed observations, UI selections and lifecycle gaps. A public declaration alone is never permission to run a mutator or guess a private implementation's meaning.

The chat-development checkpoint audit contained 275 production public-member references, all present in the same offline catalog. This includes the opt-in mod-owned GUI; it does not add new game-data coverage or establish a stable official GUI contract. The 246-reference observation-only inventory belongs to the 0.12.0 baseline.

The authenticated shared-chat checkpoint audit inventoried 276 public production game members, all source/compiler matched and present in the offline catalog. Earlier 275/246-member inventories belong to their stated builds. No private game API reference was added. Current hashes and per-provider evidence are in CHAT_VALIDATION.json.

The current simplified player build inventories 314 public production member references, all present in the offline catalog; zero non-public production references. See USER_TEST_VALIDATION.json for this build’s exact hashes and two-turn Pro check. Earlier inventories above remain historical.

The regional-population checkpoint brings the production audit to 322 public member references, all present in the same pinned offline catalog. The eight added public references support stored regional counts and realm-capital/area reads. WORLD_VALIDATION.json records scoped copied-campaign evidence; the catalog still does not enumerate supported variables or establish an official stability contract.

The current resource-trade checkpoint inventories 342 public production member references, all present in the same offline catalog, with zero non-public production references. This expands explicit typed mapping, not arbitrary variable discovery or a completion percentage.

The service-counter checkpoint pairs the new 346-member public production audit with the unchanged pinned offline catalog. All 346 IDs occur in its 17,442 candidates. This rechecks audit membership against the existing catalog, not complete state coverage or a new game version.

The configured service-policy checkpoint expands the public production audit to 353 references, all found in the unchanged pinned discovery catalog. This is an explicit mapping of cohort flags through public interfaces, not private bitmap access or a count of every game variable.

The workforce checkpoint refreshes production-reference pairing against the retained full catalog after verifying its checksum and game/source hashes. All 358 current production references occur there. The full 17,442-declaration scan is retained evidence, not claimed as a new scan for this pairing update.


The producer-degradation checkpoint pairs all 359 public production references against the same checksum-verified 17,442-member catalog. The full declaration scan is retained evidence, not a new scan or a count of supported state variables. The new public getter still requires its own semantics and finite runtime checks.


The world-faction-context checkpoint pairs all 369 production references with this same retained declaration catalog. UI_LIFECYCLE_BOUNDARY_REVIEW.json reviews a compiling public faction-panel route and named inaccessible/mutating alternatives. Declaration presence alone still does not establish live reachability or observation safety.


The regional-output checkpoint pairs all 375 production references with this retained catalog. It maps resource-backed stored accruals and cyclic configured schedules through explicit typed rows; REGIONAL_OUTPUTS.md distinguishes these from inventory, delivered totals, forecasts and ETA. Candidate and production/cost reports keep separate JAR/source scopes.


The live-regional checkpoint reuses these same 375 public references through a fixed update-thread request protocol and adds no game getter. Registry bindings, selected cells and live response provenance are reviewed separately from cached table rows; REGIONAL_LIVE_READS.md / REGIONAL_LIVE_VALIDATION.json describe the native matrix, authored partial-cache and scene evidence. This does not create a full schema or stable official contract.

The world-list-context checkpoint adds six explicit public field/getter references for known army/realm/region-browser membership, bringing the production pairing to 381. Source/binary review checks activated-manager semantics and the fixed 16-slot collection; native context/availability evidence is separate. This adds no selected-object or full panel-tree contract. See WORLD_LIST_CONTEXT.md and WORLD_LIST_BOUNDARY_REVIEW.json.

The stored ground-moisture projection adds three explicit public references (SETT.GROUND and its two stored maps), bringing that checkpoint’s production pairing to 384. The MAP_DOUBLE coordinate getter was already referenced. Stored fractions are not total moisture, rainfall, fertility or yield. See GROUND_MOISTURE.md for runtime limits and GROUND_MOISTURE_BOUNDARY_REVIEW.json for the pinned review.

The automatic-connection checkpoint paired all 385 references at that checkpoint with the retained catalog after checksum/game-source verification. The additional public Str.add(CharSequence) restores bounded mod-owned composer drafts; it is not a gameplay action or a stable documented contract. See AUTO_CONNECTION.md.

The cached-viewport mapping adds eight explicit public camera-window/cache references, bringing that checkpoint pairing to 393. All match the retained declaration catalog/source pair; no dynamic invocation or input/refresh method is exposed. See CACHED_VIEWPORT.md and CACHED_VIEWPORT_CONTRACT_REVIEW.json.

The per-warehouse mapping adds four explicit public references, bringing that checkpoint pairing to 397 (all catalog matched). STOCKPILE_LIVE_READS.md and STOCKPILE_LIVE_CONTRACT_REVIEW.json establish fixed tally/slot reader meaning and bounds; the declaration catalog itself still does not establish getter safety or runtime reachability.


The stored-weather mapping adds sixteen fixed public references (413 total, all catalog matched; 412 source anchors plus one generated enum). WEATHER.md / WEATHER_CONTRACT_REVIEW.json / WEATHER_VALIDATION.json pin ten stored game-scale factors and four flags, units/age/scene boundaries and finite production DTO/MCP acceptance. They do not establish physical units, crop predictions, all variables/menus or stable official getter contracts.

The housing production checkpoint re-pairs all 427 public compiler references with this checksum-verified existing catalog: 426 source anchors plus one generated enum method. This is a pairing update, not a repeated full declaration scan or complete variable/menu coverage; [HOUSING.md](HOUSING.md) records the selected reader semantics and exact-build acceptance.

The configured-settings checkpoint pairs 446 public production references with the same 17,442-member declaration catalog; all 446 IDs are present. Nineteen additional references map the public settings singleton/fields/readers. These are not nineteen new variables or a completeness percentage. [Settings semantics and gates](SETTINGS.md) distinguish sixteen quantized/configured preferences from physical/effective state and complete menus.
