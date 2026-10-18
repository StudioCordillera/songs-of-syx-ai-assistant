# Production helper boundary review

The shipped 0.71.44 source and binary establish a limited reason to avoid treating the generic room production helper as observed output. `IndustryUtil.calcProductionRate(double, IndustryRate, Boostable, RoomInstance)` combines a room bonus, stored employment efficiency and an average of per-person boosts. It defaults that average to one when no employees are found and does not multiply by worker count. A positive result is therefore not evidence of present production, a measured room total or a forecast.

The employee-list helper maintains a shared cache keyed by game update and object. Its private cache check writes cache metadata and clears the shared list; its collector traverses scene entities without an observer-supplied scan bound. These are cache operations, not evidence of gameplay corruption. The generic room bonus also dispatches through `RoomBoost.get`; its public interface alone establishes neither purity nor the units and cost of every implementation. These helpers remain outside the mod's explicit observer mappings.

Instead, the bounded workplace filter in WORKPLACE_FILTER.md reuses the existing recorded workplace getter within existing scan limits. It supports focused worker/stat questions without invoking the shared employee-list helper. Recorded assignment still does not establish present activity or complete production bonuses.

`RoomInstance.getDegrade()` is a narrower future candidate. The reviewed stored decoder chain has no write opcode, but this checkpoint does not map it, validate values in a game, establish units or prove general call-graph purity. Runtime additions require their own typed semantics, audit and copied-game checks.

PRODUCTION_MODIFIER_REVIEW.json records source/disassembly fingerprints for eight inspected methods. The developer-only verifier reads licensed files statically without initializing game classes. A private cache helper and package implementation are inspected only to explain the public call chain; neither is called by the mod or fixture. The production compiler inventory remains 358 public references with zero non-public references. Source verification is not a separately documented stable contract. No proprietary method bodies are redistributed.

Reproduce with `dev/review_production_modifier_boundary.py --help` and the matching licensed game/source pair. The report is scoped source/binary evidence, not complete production, performance or all-menu acceptance.
