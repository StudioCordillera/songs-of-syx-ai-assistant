# Public declaration discovery — game 0.71.44

The production reference audit proves only the public members used by our adapter. To identify remaining mapping work, `catalog_api.py` separately scans the entire shipped source archive and resolves its named types and public declared members against the installed game JAR with the Java compiler. It never starts the game, executes its classes, or uses reflection. This is development tooling, outside the packaged mod and MCP server.

The current scan covers 2,443 source files, resolves every cataloged named top-level/member source type, and finds 2,052 public types with public enclosing types and 17,442 public declared member signatures. All 246 production reference IDs occur in this catalog. Matching game JAR/source archive hashes establish that the discovery run and production audit used the same reference pair. They do not attest the installed/running mod.

| Root package | Public declared member candidates | Production reference IDs |
| --- | ---: | ---: |
| settlement | 6,606 | 90 |
| snake2d | 2,817 | 17 |
| game | 2,295 | 51 |
| init | 1,726 | 18 |
| util | 1,664 | 11 |
| world | 1,212 | 17 |
| view | 1,006 | 42 |
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

The chat-development audit now contains 275 production public-member references, all present in the same offline catalog. This includes the opt-in mod-owned GUI; it does not add new game-data coverage or establish a stable official GUI contract. The 246-reference observation-only inventory belongs to the 0.12.0 baseline.
