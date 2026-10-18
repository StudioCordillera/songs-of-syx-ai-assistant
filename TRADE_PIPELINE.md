# City resource trade observations

The trade domain retains the campaign current-day import/export ledger at `/resources`. A separate `/settlement_pipeline` contains staged **city** resource bookkeeping and configured policy values. Its absence on a battlefield is explicit: the campaign ledger may still be meaningful there, while city logistics are unavailable. The combined domain scope is `mixed_city_trade_pipeline_and_campaign_ledger`.

`policies` contains `resource_id`, an installed resource-help `reference_id`, raw buy-price cap, treasury floor, import level, sell-price floor and export level. These are configured values, not executable quotes or proof an order can run. The shipped resource adapters use level integers from 0 to 100; import 100 has special capacity-filling behavior, so it is not simply a warehouse target percentage. No setter is called by production code.

`flows` contains one row per resource and public trade reason. Reasons include tax, trade, spoils and diplomacy; do not call all incoming goods market purchases. The public counters mean:

| Field | Public reader | Interpretation boundary |
| --- | --- | --- |
| `inbound_reserved_units` | `buyer.toBeAdded().get(type)` | Existing reserved bookkeeping; not an individual order record |
| `inbound_pending_placement_units` | `buyer.toBeStored().get(type)` | Booked units awaiting the city delivery stage |
| `inbound_caravan_units` | `buyer.attempting(type)` | Existing city caravan delivery counter; not world-map position or ETA |
| `inbound_total_units` | `buyer.incoming.get(type)` | Public sum of the preceding three stages |
| `outbound_reserved_units` | `seller.promised().get(type)` | Existing promised bookkeeping |
| `outbound_caravan_units` | `seller.attempting(type)` | Existing city caravan withdrawal counter |
| `outbound_total_units` | `seller.outbound.get(type)` | Public sum of the preceding two stages |

These resource counts are not day buckets and must not be added to daily trade ledger totals as if they were independent completed transactions. `city_entry_closed` reports the public entry flag, not a complete trade-failure explanation. `trade_type_id` is the installed type index; labels can be translated. `resource_id` joins stockpile IDs and policy resource IDs in the same observation. Warehouse storage is not the producer's or import depot's internal stock.

The observer reads at most 1,000 resource tradables, 4,000 stage rows and 16 trade reasons, stopping before splitting a resource's stage batch. A failed resource emits neither partial policies nor partial stages. Check `coverage`, `truncated`, `failed_resources` and bounded failure samples before interpreting missing records. Missing/unavailable is not zero. Slave/non-resource tradables, a full order list, tariff-inclusive quotes and transport routes remain outside this mapping.

The route and stage arithmetic are reviewed in the shipped `Player`, `PBuyer`, `PSeller`, resource adapters, `TradableData`, `Caravans` and `TRADE_TYPE` sources. [TRADE_VALIDATION.json](TRADE_VALIDATION.json) records compiler/source hashes and actual MCP getter, paging, stage-sum and stock/policy-join checks. The copied-game fixture deliberately seeds nonzero reservations/delivery bookkeeping and policy settings through public methods and never writes a save; those mutations are test-only. It does not simulate a naturally executed market transaction or establish nonzero caravan movement, every trade failure, cap-exceeding mods or large-city performance. These are shipped-source-verified public APIs, not individually documented stable SCRIPT contracts.

Structured queries retain the enclosing pipeline's unavailable status. Selecting/counting or joining its battlefield rows is refused instead of returning an empty successful table. Direct pages expose unavailable coverage and null data/total; metadata can still explain the reason. This guard applies to explicit nested observation coverage, including other mapped partial/unavailable subtrees.
