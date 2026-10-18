# Cited-guidance regression checks

Run `.venv/bin/python dev/verify_guidance.py --state-dir runtime/guidance-check` from the repository. This starts the actual stdio MCP server and calls `search_guidance`; no running game, provider request or credentials are required. Use a new directory to evaluate the starter corpus independently of local edits. Existing corpus records are preserved by the seed installer, so the report records the evaluated corpus size and checksum.

`guidance-questions.json` contains 20 authored cases. Ten player questions cover the nine starter summaries; one unrelated question must return no evidence. Four version probes check exact version, family version and two mismatches. Three authority-filter cases check official, developer and community results. Two additional authority-filter queries must return no results rather than substituting a community guide.

Each positive case specifies a narrow advice expectation, the direct citation URL, speaker, authority and compatibility label. It also names supporting fragments that must be present in the returned **body**, and caveats that must remain in the body or version notes. Title matches alone cannot pass. Case expectations are authored from the existing reviewed summaries; this pass does not add a new source review or new gameplay claims. The transport-loop case checks that warning separately from warehouse collection settings.

The report preserves query/version/filter, citation, advice expectation, check counts, returned-body hash, evaluation time, corpus hash and exact evaluator/runtime hashes. It checks response size as well. Negative tests remove support or caveats and change citation URL, author, authority or compatibility to ensure an otherwise correctly ranked record fails the evaluation. A no-result expectation also rejects unrelated evidence.

## Review limits

Literal fragment checks detect missing evidence and caveats. They do not establish semantic entailment, validate a model's complete answer, prove that a guide is optimal, or turn old developer comments into current mechanics. A person must review the advice-to-passage relationship when changing an expectation. Keep recommendations narrower than their evidence, distinguish community recommendations from developer statements, and preserve unknown patch compatibility.

This is a small local retrieval regression set, not an independent search benchmark. Multiple cases reuse sources; case count is not unique source count. The evaluator performs no live web refresh and does not establish continued page availability. New primary-source review and broader topic coverage remain roadmap work. Source retrieval dates retain the prior review dates; re-running this evaluator must not refresh them.

The runtime and player bundle are unchanged by this checkpoint. Existing two-turn Pro and copied-game scene evidence retain their recorded scope; this local run does not constitute another provider or game playtest.
