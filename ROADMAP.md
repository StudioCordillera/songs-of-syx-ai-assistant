# Delivery roadmap

## 0 — Foundation (this repository)

Implemented: official-reference research, read-only stdio MCP, explicit snapshot contract, bounded state queries, local corpus search, demo fixture, unit and MCP transport checks. No live gameplay support claimed.

## 1 — Verify game integration

- Locate the installed game, record exact build/version and Java runtime requirements, and read shipped modding docs/examples.
- Confirm script entry point, load/unload/update lifecycle and mod packaging from those references.
- Build a minimal exporter using verified APIs, without copying proprietary game code into Git.
- Export loaded/session/tick/version and one real resource/population measurement. Verify it against the visible game UI.
- Acceptance: new game, load, pause, unpause, unload, save switch and quit cannot leave apparently live state for the wrong session. Record the known heartbeat timeout window.

## 2 — Comprehensive state coverage

- Inventory every domain in ARCHITECTURE.md against a specific supported build.
- Define field schemas, identifiers, units and provenance; include modded content where exposed.
- Implement collectors and chunked entity/map access, diffs, and consistency checks.
- Acceptance: collector coverage matrix has no unexplained missing domains; representative snapshots match game UI; unsupported fields are explicitly unavailable; measured overhead remains within an agreed budget on large saves.

## 3 — Real cited knowledge

- Curate actual developer documentation, version-matched guides and specific public forum posts.
- Add permitted retrieval, deduplication, cache refresh and provenance, separating developer statements from player experience.
- Evaluate: food decline, immigration, labor shortages, happiness and trade. Include missing-data, conflicting-guides and obsolete-version cases.
- Acceptance: every externally grounded mechanics claim has a direct supporting passage and URL, state facts have snapshot provenance, and unsupported claims are identified.

## 4 — In-game assistant and subscription

- Select and validate the official local-app ChatGPT plan-usage registration path or documented app-server integration.
- Choose an open-source license before any release/registration requiring open-source distribution.
- Build in-game question entry and streamed answers, citations, account/usage display, cancellation and reconnection.
- Keep authentication out of the game-state exporter. Implement consent, token storage/refresh/revocation and account-specific model discovery.
- Acceptance: login, expired/revoked token, plan exhaustion, no network, unsupported model and MCP failure all have clear recovery; no silent API billing fallback.

## 5 — Game computer use

- Implement the separate game observation/input adapter described in COMPUTER_USE.md after validating the installed game's render/UI/input hooks.
- Add viewport screenshots and visible element metadata, then click/hover/scroll/drag/key/text tools with honest mutating annotations.
- Add a visible player-controlled task/session grant, stop button, emergency hotkey and immediate takeover.
- Enforce game-window boundaries, fresh observations, bounded inputs and duplicate-action receipts.
- Verify actions with refreshed screenshots and structured game state; retain cited mechanics in explanations.
- Validate the subscription-client screenshot/custom-tool loop; native computer use is excluded from the current plan-usage preview.
- Acceptance: all cases in COMPUTER_USE.md pass on each supported platform before control is enabled in release builds.

## 6 — Release

- Validate Windows/Linux/macOS compatibility where the game and tooling support them.
- Package per supported game version; include setup and mod conflict diagnostics.
- Test representative large and modded saves and publish measured coverage/performance.
- Ship only project-owned code and permitted assets. No saves, proprietary game source, credentials or full scraped guides.
