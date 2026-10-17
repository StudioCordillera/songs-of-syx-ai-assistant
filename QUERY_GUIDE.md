# Asking for exactly the game data you need

Start with `game_status`. It reports version, session, snapshot ID, freshness and coverage.
Missing/unavailable data does not mean zero. All current domain collectors are **partial**.

## Fast structured queries

`describe_game_fields(domain)` lists observed field paths and types without returning every row.
`query_game_state(domain, pointer, offset, limit)` reads a small subtree.
`select_game_state(spec)` filters, joins and summarizes data locally before returning it to the model.
All queries in a batch use the same cached snapshot, refreshed approximately every two seconds.
Set `expected_snapshot_id` to reject a changed snapshot. A version/session change requires rediscovery.

A query source is `{"domain":"resources","path":"/stockpiles"}`. Discover actual fields first.
For example, to return the five smallest stockpiles:

```json
{"queries":[{"name":"lowest_stocks","source":{"domain":"resources","path":"/stockpiles"},"select":{"resource":{"field":"/id"},"stored":{"field":"/stockpile_stored"}},"sort":[{"field":"/stored","direction":"asc"}],"limit":5}]}
```

Expressions use `{"field":"/path"}`, `{"literal":value}`, scalar constants, or one operator:
`eq`, `ne`, `lt`, `lte`, `gt`, `gte`, `in`, `contains`, `add`, `subtract`, `multiply`, `divide`
with two operands; `and`/`or` with 1–20 expressions; `not`/`is_null` with one expression.
Division by zero and arithmetic with null return null. Missing fields produce errors.

`where` is an expression. `select` maps output names to expressions.
`joins` is a list of `{source,left_key,right_key,as,kind}` with JSON pointer keys and `inner` or `left` kind.
Only join fields with established shared identifiers; similarly named labels do not establish a relationship.
`group_by` maps output names to expressions; `aggregates` maps names to `{op,value}`.
Aggregate operators are `count` (no value needed), `sum`, `avg`, `min`, `max`.
Numeric aggregates ignore null; an empty numeric aggregate is null, while count is zero.
Sort applies after projection/grouping; nulls sort last. `offset`/`limit` paginate results.

Limits: 10 queries/batch, 3 joins/query, 10,000 intermediate rows, 200,000 work units,
32 KiB specification, 64 KiB response, 100 returned rows/query. Narrow the request on a limit error.
No SQL, expressions as code, arbitrary methods or state writes are accepted.

## Public API coverage

Only fields mapped from direct public game APIs are exported. There is no arbitrary/private field exploration.
Discover the exported shape with `describe_game_fields`; use the structured query language for complex selections.
All current domains are partial. See API_BOUNDARY.md for source provenance and documentation limitations.
Use `get_game_ui_context` for active view, known overlays and selected subject identity. Open room blueprint context is available; exact instance, management tab, tooltip text and complete panel ordering are unavailable. Inspect `get_game_api_support` for evidence and limits before assuming a query exists.

## References and advice

1. `search_game_references` searches resource, technology and stat descriptions loaded by this exact game.
   Cite its reference ID and origin. Active mods can change this text; these are installed-data references.
2. `search_guidance` searches reviewed excerpts with direct URLs, authors, authority, retrieval time,
   version notes and compatibility labels. Prefer official/developer evidence; community guides are secondary.
3. Combine observed state with supported mechanics and explain the inference. An old forum answer or a
   version-family match does not prove applicability to the current patch. Report gaps instead of inventing evidence.

The initial external corpus is deliberately small. It is not an exhaustive or automatically updated knowledge base.

## UI-aware selections and scope

`{"context":"/selected_subject/id"}` reads a UI context field from the same snapshot. For example:

```json
{"include_ui_context":true,"queries":[{"name":"selected_person","source":{"domain":"entities","path":"/items"},"where":{"eq":[{"field":"/id"},{"context":"/selected_subject/id"}]},"select":{"id":{"field":"/id"}},"limit":1}]}
```

Discover the actual entity path before querying. A missing context field is an error; an empty result does not prove the person is absent from the game because entity export is bounded. Modal overlays may obscure the underlying selection.

Query results include coverage and scope for each source and join, plus `mixed_scopes`. Inspect `game_status.scene` and these scopes before comparing city, battlefield and campaign values. Resources also provide `field_definitions`: `owned` mixes scene logistics and player trade promises, while `stockpile_stored` describes the instantiated settlement. During world preparation, unavailable domains contain null, not fabricated zero values.
