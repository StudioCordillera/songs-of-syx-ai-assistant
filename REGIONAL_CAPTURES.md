# Retained regional output selections

`capture_live_regional_outputs` makes a complete bounded selection during one public `GAME.addAfterUpdate` callback, then retains encoded detached rows in the MCP server. `read_regional_output_capture` pages those rows without another game request. Use this pair when values must stay consistent across pages. [Live regional pages](REGIONAL_LIVE_READS.md) remain separate observations; they cannot be stitched into a capture.

```json
{
  "region_ids": [0, 17],
  "resource_ids": ["<exact loaded resource key>"],
  "fields": ["accrued_output_raw", "days_until_configured_output", "reference_id", "faction_id"],
  "min_accrued_output": 1,
  "max_rows": 2000,
  "scan_limit": 10000
}
```

The IDs/key are placeholders. Discover current active region IDs and exact loaded resource keys through world/resources fields and installed references. Unknown or inactive bindings fail, rather than becoming zero. Optional inclusive amount bounds and owner filter combine with AND. `region_id` and `resource_id` always identify each row. No selected-region identity is inferred.

## Completeness and budgets

Capture protocol 2 reuses the reviewed explicit getters and fixed region/resource matrix bindings from protocol 1. Public source/binary verification is distinct from a documented stable mod contract. See [the source boundary](REGIONAL_OUTPUT_BOUNDARY.md) and [API boundary](API_BOUNDARY.md).

A request accepts at most 100 unique region IDs and 100 unique loaded keys, requires cursor zero, and requires its entire ordered matrix to fit `scan_limit` (at most 10,000 cells). `max_rows` is 1–2,000, default 2,000. The request remains at most 8 KiB. Region/resource registry binding scans remain bounded at 1,023/1,000 entries. The ordinary active-registry getter can maintain its membership cache; no explicit boost/cache refresh or shipping action is invoked. Request deadline remains eight seconds. An exact row-bound match succeeds if the rest of the matrix has no further matches; scanning continues to prove that.

Any cell error or extra matching row makes the entire capture unavailable. An incomplete scan, remaining cursor, response/mode/identity mismatch or byte overflow retains nothing and does not evict an existing token. The worker permits at most 2 MiB for a capture response (live pages remain 64 KiB); the helper separately bounds the retained encoded payload at 2 MiB including its selection metadata. Narrow IDs/filters/fields when limits are exceeded. This route never relaxes failures into zero counters or silently collects multiple callbacks.

## Read and lifetime

Creation returns `capture` metadata and `current_state`, without rows. Use the returned `capture_id` with `read_regional_output_capture`, row `offset` and `limit` (1–100, default 25). A page is at most 64 KiB. `include_ui_context` optionally returns `captured_ui_context`; reduce the page size or omit context when the response is too wide.

Regional captures have a separate pool of three tokens per MCP server, each retained for 120 monotonic seconds. The oldest successful token is evicted when the pool is full. Tokens do not survive restart or work across processes or entity/tile pools. Expiry, missing tokens, stale/unloaded game status and session/version changes fail explicitly. A changed session/version invalidates the token. A fresh same-session/version observation is required even though the rows remain historical.

Every page keeps the original request/session/version, tick, time, selection, scene and optionally original UI context. `current_state` is current status metadata and is not the source of retained rows. Cite `capture_id` and original observation provenance; never present retained values as current or join different captures/live responses as one transaction. One callback does not freeze simulation workers or establish a global game-state transaction.

`accrued_output_raw` is resource-backed stored campaign accrual, not city inventory, delivered totals or production/income forecast. `days_until_configured_output` is a cyclic schedule offset, not shipment/arrival ETA or shipping permission. Owner is the observed campaign faction or null, not UI selection. Exact counter age, non-resource/MONEY outputs and boost/cache/shipping actions remain excluded.

## Evidence and reproduction

[REGIONAL_CAPTURE_VALIDATION.json](REGIONAL_CAPTURE_VALIDATION.json) pins the source/JAR, copied-game getter/MCP capture checks, retained paging after counter/view changes, restoration, real reload invalidation, finite scene follow-up and descriptive native capture/encoding samples. Offline tests separately cover malformed selections/responses, error/byte/metadata refusal without evicting good data, immutable decoded pages, pool isolation/eviction, expiry and freshness/session guards. Earlier live-page and request-cost reports retain their own build hashes and limits.

Use the licensed-game/copied-profile setup from [CONTRIBUTING.md](CONTRIBUTING.md):

```sh
.venv/bin/python dev/run_read_fixture.py --case regional-capture \
  --game-dir "$SYX_GAME_DIR" --save runtime/smoke.save \
  --java "$SYX_GAME_JAVA" --jdk-home "$SYX_JAVA_HOME"
```

The runner takes the shared native-fixture lock, validates the paired bundle/game/source, restores the prior copied mod and checks copied-save integrity. Test-only public counter writes and scene setup occur only inside the disposable copied game. No provider call, normal save, screenshot, native input or reflection is involved. Native checks are finite: not worst-case 10,000-cell/2,000-row cost, native registry/cell faults/2-MiB overflow, natural rollover/ownership transfer, every menu/scene or larger-city/FPS acceptance. All-state UI/lifecycle and remaining field coverage stay open. Install/restart the paired mod and helper; old mods do not implement capture protocol 2.

The copied-game sample selects 100 regions × 42 resource keys (4,200 cells); a positive filter yields 166 rows, and a separate 47-region unfiltered capture yields 1,974 rows (about 291 KiB). Thirty-one warm collector samples per shape have medians of 0.499 ms (filtered matrix) and 0.786 ms (near-row-bound selection), maxima 4.052/3.800 ms. Encoding is separate, with medians 0.195/1.859 ms, and runs off-thread in production. These finite descriptive timings do not justify a worst-case or global transaction claim.
