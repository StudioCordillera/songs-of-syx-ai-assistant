# Roadmap

Current boundary: an in-process SCRIPT mod, typed public-API observations, bounded snapshot selections and cited reference retrieval. No private reflection or native/OS UI automation. See API_BOUNDARY.md.

1. Expand explicit data mappings with primary-source provenance, meanings, units and per-version coverage. Leave inaccessible data unavailable.
2. Extend the established partial UI context and evidence catalog. Selected subject/view/known-overlay/room-blueprint reads and named individual statistics are implemented. Exact selected room instances, tooltip text, management tabs and panel ordering require appropriate public APIs.
3. Establish a documented unload-to-menu lifecycle hook or keep the freshness limitation explicit; test menus/transitions and large settlements.
4. Extend reviewed official/developer reference coverage and version-aware search.
5. Build an in-game chat client using supported OpenAI authentication, subject to registration/eligibility.

Full game state, all-menu coverage and a fully documented stable mod API are not currently available.

Next data-access work: design bounded on-demand typed entity/data requests across the whole instantiated scene, with session/snapshot provenance and update-thread execution. The current prefix entity list and dedicated selected-person export do not implement arbitrary whole-state selection or every entity attribute. Any new request protocol must remain read-only, reject arbitrary member names/code, and preserve the public API boundary. No such mailbox is included in 0.6.0.
