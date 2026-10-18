# Stockpile and logistics candidate boundary

[STOCKPILE_BOUNDARY_REVIEW.json](STOCKPILE_BOUNDARY_REVIEW.json) records static review of Songs of Syx 0.71.44's licensed source/binary and its paired public declaration catalog. **No new stockpile fields are exposed by this checkpoint.** The production inventory remains 359 public references; the simple Pro player and its tested predecessor are unchanged. These are shipped-source findings, not separately documented stable mod contracts.

## Narrow candidate route

The existing public `SETT.ROOMS()` route leads to `ROOMS.STOCKPILE`, public `ROOM_STOCKPILE.tally()` and five public `StockpileTally.TallyData` fields. With an explicitly validated installed resource index, `total(int)` reads the aggregate array and `get(int, StockpileInstance)` reads a per-room array. The selected bytecode has no method calls, direct writes, allocations or backward branches. This establishes bounded accessor bodies, not measured collector cost, thread safety in arbitrary contexts or complete source/binary equivalence.

| Tally | Candidate meaning | Avoid interpreting it as |
| --- | --- | --- |
| `crates` | Number of crates assigned to this resource | Resource-item capacity or unused crates available for any resource |
| `space` | Assigned capacity, in resource items | Free capacity, physical floor area or capacity for every resource simultaneously |
| `spaceReserved` | Incoming capacity already reserved, in resource items | Goods physically present or guaranteed future deliveries |
| `amount` | Stored resource items, including reserved stored goods | Goods freely available for every use or all settlement inventory |
| `amountReserved` | Reserved stored resource items | Reserved incoming capacity or completed consumption |

The shipped bookkeeping derives these counters from crate capacity, stored amounts and their two distinct reservation counters. `RESOURCE.owned()` has a broader existing meaning: it combines additional logistics locations and incoming station goods, then subtracts trade promises. Its result must not be relabeled warehouse inventory. Counters are stored bookkeeping; exact update age and reconciliation with ground/transport/import/export goods remain unestablished.

Resource-object overloads also exist, with null selecting a cross-resource aggregate slot. Prefer explicit installed resource indexes and retain resource IDs in each proposed row. Do not access internal arrays, private/package fields or the aggregate slot directly. A per-room route still needs type checks against actual `StockpileInstance` objects obtained through existing bounded public room enumeration; never accept arbitrary handles/indexes from an agent.

## Fullness and shared-handle traps

The reviewed helpers differ:

- `StockpileTally.load(resource)` divides stored amount by assigned space; zero space returns **1**.
- `StockpileInstance.getUsedSpace()` divides room stored amount by room assigned space; zero space returns **0**.
- `StockpileInstance.storedD(resource)` subtracts reserved stored goods before dividing by assigned space; zero space returns **1**.

None should be presented as an interchangeable player-facing fullness percentage. A future explicit ratio should use detached counters, specify whether reservations are included and return null with a reason at zero denominator. Do not clamp away bookkeeping inconsistencies or claim that apparent free capacity guarantees reachability, staffing or successful delivery. Assigned capacity is resource-specific; combining heterogeneous rows does not establish physical warehouse fullness.

`StockpileInstance.crate/storage/resourceTile` delegate to a shared crate object. Its public coordinate binder writes four scratch fields. This is a source/bytecode observation, not a runtime private-field read. No live crate handle should be retained across calls or exported. The proposed tally path avoids the binder and logistics actions.

## Required implementation and validation

Keep a future mapping city-only until other scenes are established. Collect on the existing game after-update thread into detached DTOs; never expose tally objects, reservation actions or arbitrary method invocation. Resource/room scans and row counts need explicit budgets, truncation and failed-read metadata. Preserve null versus zero and unavailable scene semantics. A resource-wide total must not silently be inferred from a capped room prefix.

Before exposing data, use a disposable copied game to compare each public getter with exported rows and actual MCP selections. Cover at least unassigned/zero-capacity resources, positive storage, both reservation counters where safely obtainable, inactive/removed rooms, a bounded per-room join and unavailable scenes. Establish actual cap/failure behavior and relevant collection cost separately. Synthetic values do not prove that live reservations were observed. No such runtime acceptance is claimed here.

## Reproduce the static review

```sh
.venv/bin/python dev/review_stockpile_boundary.py \
  --game-dir '/path/to/Songs of Syx' \
  --jdk-home '/path/to/full-jdk' \
  --catalog build/game-api-catalog.json \
  --output runtime/stockpile-boundary-review.json
.venv/bin/python -m pytest -q test_stockpile_boundary.py
```

Use `catalog_api.py` as described in [API discovery](API_DISCOVERY.md) if the local declaration catalog is absent. The review checks catalog/game/source checksum pairing, public declaration identities, selected getter bytecode, bookkeeping source markers and the crate binder's scratch writes. It never initializes the game, invokes game methods, changes a profile or uses a provider key. Published evidence contains metadata/hashes/conclusions only; licensed source and bytecode stay local.
