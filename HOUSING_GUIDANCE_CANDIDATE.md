# Housing reference candidate history

Production integration of these exact summaries is recorded in HOUSING_REFERENCE_RELEASE_VALIDATION.json and WORK_STATUS.md. The candidate checks below retain their earlier fifteen-record/private-corpus scope. To reproduce the candidate-only evaluator, use its pre-promotion checkout `c79ccdff69f37643eadeed18d7307538d2004173`; current production has already integrated the two IDs and their eight cases.

Two original historical summaries were reviewed on 2026-10-21. [Source provenance](HOUSING_REFERENCE_REVIEW.json) records original developer comment IDs, speaker/profile badges, Steam publication epochs and anonymous canonical-page/body checksums. Quoted community posts were separated from the developer's own words; raw HTML remains private. This review does not establish present game mechanics or an ongoing web refresh.

- [Not claiming housing, original developer comment #5](https://steamcommunity.com/app/1162750/discussions/0/3387294407407782274/): historical workplace-proximity troubleshooting and a then-planned correction. No numeric search radius or later delivery is established.
- [EA64 housing, original developer comment #1](https://steamcommunity.com/app/1162750/discussions/0/3800523859689753142/): historical privacy/upgraded-density context. The topic's version name does not verify an exact tested build, current geometry or an optimal blueprint.

[housing-guidance-candidate.json](housing-guidance-candidate.json) retains author, direct URL, retrieval date and explicit unknown compatibility for both records. [Eight candidate questions](housing-guidance-candidate-questions.json) require supporting body fragments and version caveats, unknown compatibility for exact/family/future queries and no substitution under official-only filters. These are historical diagnostic leads, not evidence that observed empty beds are usable or that a particular current housing change will work.

[Candidate validation](HOUSING_GUIDANCE_CANDIDATE_VALIDATION.json) exercises all eight cases plus the unchanged 37 production regression cases through the actual MCP server over a separate fifteen-record corpus. All 45 pass. Existing bodies/review dates remain intact. Literal support checks are regression guards, not independent semantic entailment or provider-answer correctness; no game or inference call is made.

Reproduce from the checkout with `.venv/bin/python dev/verify_housing_guidance_candidate.py --state-dir runtime/housing-guidance-new-check`. The script requires a new directory beneath this checkout's ignored `runtime/`, refuses existing state/corpus directories and validates candidate/review hashes before adding the two records to that private copy. It never installs them in normal player histories or changes production `SEEDS`.

At this historical candidate checkpoint the thirteen-record production corpus and player ZIPs stayed unchanged. The later production release above completes separate seed/migration and exact-source retrieval/provider/core/distribution/player gates. Broader current-version guide coverage, tested blueprint examples and current housing-advice correctness remain open.
