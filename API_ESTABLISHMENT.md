# API establishment report — 0.4.0, game 0.71.44

This report establishes what can be verified within the user's required in-process public-API boundary. It does not create an official guarantee on behalf of the game developer.

## Evidence levels

1. **Documented script contract:** the shipped semi-official script guide and SCRIPT interface describe script creation, updates and persistence callbacks. They do not document every game statistic or menu.
2. **Source-verified public API:** Java compiler attribution resolves each game member referenced by production mod code. The current inventory contains 141 members, all public. Of these, 140 match declaring type, name, arity and simple parameter types in shipped source; the remaining member is the compiler-generated enum `values()` method. Only one referenced member has its own Javadoc block; Javadoc presence does not establish semantics or stability. Script override contracts are reviewed separately from the member-reference inventory.
3. **Runtime evidence:** the isolated fixture exercises supported contexts using public game methods and a copied save. The production mod only observes. Test mutations and engine bootstrap code are never packaged into the mod.
4. **Unavailable/unvalidated:** missing public accessors and untested transitions stay explicit. No reflection, screenshot, native-input or package-access workaround is added.

The [official documentation project](https://github.com/songsofsyx/documentation) links the published guide. Its [getting-started page](https://songs-of-syx.readthedocs.io/en/latest/modding_getting_started.html), checked 2026-10-17, contains a heading but no API details. This does not supply the missing member-level contracts.

## Current coverage matrix

| Capability | Established access | Runtime scope / limits |
| --- | --- | --- |
| Exported state variables | 18 partial typed public-API domains; 141 referenced members in the audit | Existing copied save; not every variable or every entity attribute |
| Active view | `VIEW.current`, subview `isActive` | Settlement and world exercised; battle predicate compiled but battle not exercised |
| Selected subject | `UISubjects.current` and public entity identity/race/location | Subject panel exercised; may remain behind a modal overlay |
| Room context | `UIRooms.openIs` and room-list membership | Room blueprint/table/detail presence exercised; exact selected instance unavailable |
| Game menu / confirmation | Public known interrupters and `isActivated` | Both exercised; menu subpages not enumerated |
| Management | `IManager.open` | Open/closed exercised; selected tab remains private |
| Encyclopedia | Known public WIKI interrupter | Open/closed exercised |
| Loading overlay | Known public ILoadScreen interrupter | Overlay flag exercised; actual save reload is a separate transition test |
| Save reload | Documented script creation plus session rotation | Copied save reloaded in the same process; new session verified |
| Main menu | No plugin context callback/accessor established | Fixture returns there; plugin uses freshness/unknown-state fallback, not menu identification |
| Full tooltip text | No read-only public enumeration established | Presence only; GBox text storage is private |
| Complete panel hierarchy / stacking | No public general enumeration/order established | Known overlay flags only; cannot select a topmost panel from these flags |
| All game variables / all menus | No complete public schema or contract established | Still unavailable; battle, world generation, options/save/load subpages and every popup type are not exhaustively tested |

## Agent-facing tools

`get_game_ui_context` returns a partial UI observation from the same snapshot as exported state, including active view, known overlay flags, selected subject identity and open room blueprints. Unsupported details have reasons. Selected objects describe underlying panels and may be obscured; “this” is not automatically resolved when a modal is open. Individual subject statistics must not be inferred from population aggregates.

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
