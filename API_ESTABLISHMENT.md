# API establishment report — 0.8.0, game 0.71.44

This report establishes what can be verified within the user's required in-process public-API boundary. It does not create an official guarantee on behalf of the game developer.

## Evidence levels

1. **Documented script contract:** the shipped semi-official script guide and SCRIPT interface describe script creation, updates and persistence callbacks. They do not document every game statistic or menu.
2. **Source-verified public API:** Java compiler attribution resolves each game member referenced by production mod code. The current inventory contains 183 members, all public. Of these, 182 match declaring type, name, arity and simple parameter types in shipped source; the remaining member is the compiler-generated enum `values()` method. Only one referenced member has its own Javadoc block; Javadoc presence does not establish semantics or stability. Script override contracts are reviewed separately from the member-reference inventory.
3. **Runtime evidence:** the isolated fixture exercises supported contexts using public game methods and a copied save. The production mod only observes. Test mutations and engine bootstrap code are never packaged into the mod.
4. **Unavailable/unvalidated:** missing public accessors and untested transitions stay explicit. No reflection, screenshot, native-input or package-access workaround is added.

The [official documentation project](https://github.com/songsofsyx/documentation) links the published guide. Its [getting-started page](https://songs-of-syx.readthedocs.io/en/latest/modding_getting_started.html), checked 2026-10-17, contains a heading but no API details. This does not supply the missing member-level contracts.

Runtime evidence spans the 0.8.0 extended-context fixture, 0.7.0 scene/entity fixtures and 0.6.0 context fixture. Exact run scopes are recorded in VALIDATION.md and validation-evidence.json.

## Current coverage matrix

| Capability | Established access | Runtime scope / limits |
| --- | --- | --- |
| Exported state variables | 18 partial typed public-API domains; 183 referenced members in the audit | Existing copied save; not every variable or every entity attribute |
| Active view | `VIEW.current`, subview `isActive` | Settlement, world, settlement tactical HUD, generated battle deployment and initial/terrain world generation exercised; editor activation exercised on a copied completed world |
| Selected subject | `UISubjects.current`, individual class/type and named `STAT.hasIndu` / `STAT.indu` getters | 58 individual statistics observed in the copied-save subject; values/min/max and installed-help reference IDs. Panel may remain behind a modal overlay |
| Room context | `UIRooms.openIs` and room-list membership | Room blueprint/table/detail presence exercised; exact selected instance unavailable |
| Game menu / confirmation | Public known interrupters and `isActivated` | Both exercised; menu subpages not enumerated |
| Management | `IManager.open` | Open/closed exercised; selected tab remains private |
| Encyclopedia | Known public WIKI interrupter | Open/closed exercised |
| Loading overlay | Known public ILoadScreen interrupter | Overlay flag exercised; actual save reload is a separate transition test |
| Save reload | Documented script creation plus session rotation | Copied save reloaded in the same process; new session verified |
| Main menu | No plugin context callback/accessor established | Fixture returns there; plugin uses freshness/unknown-state fallback, not menu identification |
| Full tooltip text | No read-only public enumeration established | Presence only; GBox text storage is private |
| Complete panel hierarchy / stacking | No public general enumeration/order established | Known overlay flags only; cannot select a topmost panel from these flags |
| All game variables / all menus | No complete public schema or contract established | Still unavailable; active combat/conclusion, complete world generation, editors, menu subpages and every popup combination are not exhaustively tested |

## Scene scope and semantic checks

The snapshot identifies whether an instantiated settlement is a city or a generated battlefield. Domain scopes distinguish scene-local observations, campaign/player data, and mixed resource logistics. During initial world setup, seventeen domains are explicitly unavailable; settings remain observable. Generated terrain alone does not establish a completed playable world. The exact wizard stage remains private.

`RESOURCE.owned()` is a mixed logistics quantity: warehouse/hauler and import/export/station goods, including incoming station goods, minus player trade promises. It is not a warehouse count and may be negative. Resource field definitions identify this scope separately from stockpile storage/capacity. A development-only bytecode check verifies this getter's operations against the installed JAR. Two further checks confirm the exit-to-menu factory and the package-private engine-disposal contract. Only fingerprints, member names and conclusions are published, not proprietary method bodies.

## Agent-facing tools

`get_game_ui_context` returns a partial UI observation from the same snapshot as exported state, including active view, known overlay flags, selected subject identity and open room blueprints. Unsupported details have reasons. Selected objects describe underlying panels and may be obscured; “this” is not automatically resolved when a modal is open. Individual subject statistics must not be inferred from population aggregates.

`select_game_state` supports a `{"context":"/selected_subject/entity_id"}` expression and optional `include_ui_context: true`, using the same snapshot as the data query. Results carry source coverage and scope, including joined sources. The selected person has a dedicated `/selected_subject` export in the entities domain, independent of the bounded `/items` list. Named individual statistics are partial, not a complete attribute schema.

`get_game_api_support(query, offset, limit)` returns capability evidence/limits and a paginated, searchable compiler inventory with source paths, declaration lines, source hashes and mod call sites. It is usable without a loaded game. It does not expose a method-call or private-field interface.

Stale status now distinguishes `observed_game_loaded` from the current `game_loaded` value. Once observations expire, current loaded state is null/unknown and `get_game_ui_context` refuses the stale observation. A clock skew receives its own unknown-state reason.

## Reproduce the audit

Use a full JDK 17+ for the development audit (the mod itself still targets Java 16 bytecode):

```sh
python3 audit_api.py --game-dir '/path/to/Songs of Syx'
```

`SYX_JAVA_HOME` may point to a complete JDK. The audit uses compiler attribution with annotation processing disabled; it reads the licensed game JAR and shipped source archive as references. It writes `api-audit.json` and the metadata-only `syx_api_manifest.py`. No game method bodies or game state are bundled. Audit failure on non-public members or unresolved source anchors prevents regeneration.

`dev/ApiAudit.java` and the context test scenario are development tools, outside the production mod source tree. Test-only UI methods are excluded from the production member inventory and JAR.

## Remaining upstream/API gaps

An official complete state schema, a stable contract for individual getters, selected room-instance/tab readers, a general panel tree, tooltip text enumeration and a script-level unload/menu callback were not established. Existing private/package-private fields do not satisfy the boundary. These need an appropriate public API, official clarification/extension, or a narrower product promise. Further local tooling can inspect availability but cannot turn an undocumented/private implementation into an official public contract.

A concrete unsent proposal for these missing public contracts is recorded in UPSTREAM_API_REQUEST.md. It is not an implementation or official support promise.

## Selected individual data — 0.8.0

The entities domain includes a dedicated `selected_subject` object with identity, race, class, type and named statistics whose public `hasIndu()` advertises an individual getter. This path does not depend on the first-1,000 `/items` export. Each statistic provides raw integer value, getter bounds, coverage and a `reference_id`. Missing getters fail individually; unknown semantic units stay unknown. A selected person is not inferred from population statistics. A null selection remains null.

The installed-help search accepts an exact reference ID such as the returned `stat:N`, so an advisor can retrieve the matching in-game description rather than guessing the meaning from a numeric value. These descriptions are installed game/mod data, not an official stability promise. The original copied save has 295 entities. The 0.7.0 isolated fixture raises this to 1,395 temporary entities and verifies that a target beyond the prefix is available through both dedicated selection and on-demand requests.

## On-demand entity access — introduced in 0.7.0

Fixed public getters now serve bounded entity requests across the instantiated scene. Explicit IDs use `ENTETIES.getByID(int)`; broader filters use bounded read-only array traversal. The production compiler inventory includes this lookup's source declaration. Installed stat references advertise whether a named individual getter exists.

The isolated fixture adds temporary citizens to a copied game without saving it. It verifies 1,395 live entities, a selected target absent from the 1,000-row snapshot prefix, direct attribute/stat reads, combined class/race/type/tile/stat predicates, 18-page complete paused-scene traversal, unknown-stat rejection, concurrent MCP reads and same-response UI context. Fixture mutations are never part of production. No arbitrary-field or method-call interface was introduced.

This is more complete entity access, not a complete game-variable schema. Every page is a separate observation; generic entity histories/private AI and stable whole-scene snapshot paging remain unavailable. See QUERY_GUIDE.md and validation-evidence.json for exact scope.

## Exposed UI content and transitions — 0.8.0

`known_content` reads three public roots: primary popup, secondary popup and section. Typed mappings use `IPopup.current`, `InterGuisection.current`, `GuiSection.elements`, `CLICKABLE.ClickSwitch.current`, `GTextR.text`, public control flags and internal UI bounds. Opaque widgets are retained as opaque; no private label/input fields are read. The general interrupter collection is still private. Its nested iterator methods do not make the collection publicly enumerable.

Reads are bounded to 80 nodes total, depth six, 4,096 UTF-16 text characters and 512 per label. Shared references point to an observation-local node ID. These IDs are not action handles. Truncation, getter errors and unavailable text remain explicit. Visibility flags and known ancestors do not establish clipping, occlusion or final rendered visibility; child order does not establish global overlay stacking. Public label strings are not a reconstruction of rendered pixels or tooltip contents.

The isolated extended fixture checks sixteen phases: base city; primary/secondary popups; section; node/text/depth limits; closed content; text input without private-value export; full-screen prompt; copied-save reload; world editor; return to city with the editing workflow flag still set; battle setup editor; return to city; battle deployment; and public retreat restoring the city with a new session. Content widgets are constructed by the fixture using game APIs, so this is not a claim that every native game dialog is readable. Retreat is tested from deployment, not active fighting. The test-supplied exiter asserts the result; production does not expose an arbitrary battle-result event feed.

The snapshot now explains that WorldGen workflow flags can persist after editor exit. `active_view` identifies the current UI mode. The battle deployment flag is likewise described as a logical flag, not proof that simulation/combat is running; the pinned start overlay remains inaccessible through a public read getter.
