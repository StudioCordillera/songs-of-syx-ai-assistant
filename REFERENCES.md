# Reference register

Checked 2026-10-17. Recheck official docs at implementation time; access and preview behavior can change.

| Source | Authority | What it establishes / limitation |
| --- | --- | --- |
| [Codex authentication](https://learn.chatgpt.com/docs/auth) | OpenAI | ChatGPT login and API-key modes; different billing paths. |
| [MCP configuration](https://learn.chatgpt.com/docs/extend/mcp?surface=cli) | OpenAI | Local stdio and remote HTTP server configuration. |
| [ChatGPT plan usage overview](https://developers.openai.com/siwc/token-sharing-open-source) | OpenAI | Eligible local/open-source app registration and consent route; does not establish this project's eligibility. |
| [Plan usage preview limitations](https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations) | OpenAI | Hosted MCP is unsupported on this route; local tools are a separate client concern. |
| [Models and inference](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference) | OpenAI | Account-specific model discovery and public Responses endpoint. |
| [Codex app-server](https://learn.chatgpt.com/docs/app-server) | OpenAI | Protocol for custom clients and streamed interactions. |
| [Build an MCP server](https://modelcontextprotocol.io/docs/2026-07-28/develop/build-server) | MCP project | Python SDK 2.x server pattern and stdio transport. |
| [Official Python MCP SDK](https://github.com/modelcontextprotocol/python-sdk) | MCP project | SDK implementation; this prototype pins 2.3.0. |
| [Songs of Syx documentation repository](https://github.com/songsofsyx/documentation) | Game documentation project | Describes itself as game modding documentation and links Read the Docs. |
| [Published modding getting started](https://songs-of-syx.readthedocs.io/en/latest/modding_getting_started.html) | Game documentation project | Currently sparse; no verified Java API signatures obtained here. |
| [Game store page](https://store.steampowered.com/app/1162750/Songs_of_Syx/) | Developer/publisher via Steam | Confirms game identity and Steam app ID. |
| [Steam guides directory](https://steamcommunity.com/app/1162750/guides/) | Community platform | Starting point for guide discovery, not evidence for gameplay mechanics. |

Community mod templates may help investigation but must be labeled community references and checked against the shipped game. No community template is used here to assert unverified official API signatures. The implementation was checked against locally shipped `info/MAKE_A_MOD.txt`, `info/scriptGuide.odt`, `info/SongsOfSyx-sources.jar`, and actual loader/SCRIPT bytecode for 0.71.44. These proprietary references are not redistributed.

## Access boundary

See API_BOUNDARY.md for shipped primary references. The screenshot/input and reflection adapters were removed in 0.3.0. Former computer-use design references do not establish an approved game mod API.

## Gameplay evidence and review history

The current seed contains 15 reviewed original summaries; GUIDANCE_VALIDATION.json records 45 authored cases. The paragraphs below preserve earlier expansion scopes/dates. See HOUSING_REFERENCE_REVIEW.json and HOUSING_REFERENCE_RELEASE_VALIDATION.json for the latest additions. Installed help and external guidance remain separate.

Installed resource, technology and stat help text is indexed at runtime, with current version/mods and original class/key identifiers. It is not bundled from proprietary game files.

The initial five short authored summaries, checked 2026-10-17, could be installed with `syx-knowledge`: [v71 community guide](https://steamcommunity.com/sharedfiles/filedetails/?id=3776333166) , [official V71 law/family/trade release notes](https://steamcommunity.com/games/1162750/announcements/detail/529882384083977659), and [historical developer reply about eatery overlays](https://steamcommunity.com/app/1162750/discussions/0/4841941418359552221/). Source records retain authority and compatibility caveats. These do not establish exhaustive current mechanics.

## Additional reviewed gameplay evidence (2026-10-18 UTC)

At this historical expansion checkpoint, the starter corpus contained nine original summaries. Three added records were checked directly on their canonical Steam pages, including the developer badge and surrounding discussion:

| Source | Authority | Scope / limitation |
| --- | --- | --- |
| [Workload versus production](https://steamcommunity.com/app/1162750/discussions/0/3800525036429614132/) | Gamatron, developer reply #2, 12 July 2023 | Distinguishes an estimate from realized output. Later participants dispute display behavior; no exact current-patch applicability is established. |
| [Pasture fertility](https://steamcommunity.com/app/1162750/discussions/0/2954914688097551706/) | Gamatron, developer answer #1, 22 September 2021 | Historical animal-capacity explanation. Subsequent irrigation/base-fertility discussion is community commentary, not a new developer guarantee. |
| [Developer FAQ](https://steamcommunity.com/app/1162750/discussions/0/3388408347654953100/) | Gamatron, opening post, edited 9 July 2023 | Historical navigation to wiki, installed help and release notes; current UI locations and old-save compatibility require verification. |

These records retain unknown version compatibility rather than being labeled V71-compatible by assumption. Wiki.gg pages encountered during discovery returned access errors and were not added as newly reviewed evidence. Existing source timestamps are preserved when the corpus is reinstalled.

Search uses whole-word relevance before version compatibility and authority tie-breakers. Matching terms and a retrieval score are returned for inspection; the score is not factual confidence. The response stays within 64 KiB and reports truncation. See GUIDANCE_VALIDATION.json for the current 45 authored local-MCP cases. This is a lexical starter retrieval check, not a comprehensive evaluation of model advice.

## API establishment audit (0.4.0)

API_ESTABLISHMENT.md links the primary sources, reproducible compiler inventory and runtime coverage matrix. Individual member anchors and hashes are in api-audit.json. The online documentation getting-started page was rechecked on 2026-10-17 and does not provide member-level API contracts. No community SDK is used to claim official support.

## Additional provider evidence (2026-10-17)

- [Claude Code authentication](https://code.claude.com/docs/en/authentication): official login, API-key and authentication precedence.
- [Claude Code MCP](https://code.claude.com/docs/en/mcp): local stdio server configuration.
- [Claude plan/Agent SDK notice](https://support.claude.com/en/articles/15036540-use-the-claude-agent-sdk-with-your-claude-plan): current subscription/SDK and plan-specific credit guidance; recheck eligibility.
- [Claude API authentication](https://platform.claude.com/docs/en/manage-claude/authentication): API credential mechanisms.
- [DeepSeek Claude Code integration](https://api-docs.deepseek.com/quick_start/agent_integrations/claude_code/): compatible endpoint and model settings.
- [DeepSeek API introduction](https://api-docs.deepseek.com/): native service endpoint and current model identifiers.

PROVIDERS.md tracks required behavior and distinguishes supplied connection templates from pending authenticated/model/in-game-client validation.


## Installed help expansion

The latest copied-game catalog contains 834 records, including 111 room blueprint descriptions and three research-currency descriptions. Source/compiler-verified public `RoomBlueprintImp.info` and `TechCurrency.bo` metadata supply these additions. Runtime checks compare title/description hashes and exact-ID/category MCP lookup; only hashes/counts are published. UI blueprint links remain partial context, with the existing stale-main-menu limit. See INSTALLED_HELP_VALIDATION.json.

Added [Nerond's V71 logistics guide](https://steamcommunity.com/sharedfiles/filedetails/?id=3622513777) as community evidence for collection settings and delivery loops; exact patch compatibility remains unverified.

## Historical developer-reference expansion (2026-10-18 UTC)

That historical checkpoint contained thirteen original summaries. Two further canonical threads were reviewed with original developer badges, reply numbers and surrounding discussion: [warehouse shipping replies #1/#9](https://steamcommunity.com/app/1162750/discussions/2/3759977302534570731/) and [service-display answer #1](https://steamcommunity.com/app/1162750/discussions/0/3196993316890360111/). HISTORICAL_REFERENCE_REVIEW.json records review time, visible dates, author, text hashes and evidence limits. Both keep an empty established-version list and unknown compatibility. Review through web text extraction can use cached content; it does not establish continuing live availability. Older source-review records and retrieval dates remain unchanged.

## Official feed recheck (2026-10-20 UTC)

[REFERENCE_FEED_RECHECK.json](REFERENCE_FEED_RECHECK.json) records a separate official Steam news API retrieval of the V71 release announcement. It confirms the already summarized service-fetch/treatment topics and preserves the API record's author/date/body hash separately from older review attribution. No duplicate summary is added, no earlier review date is replaced, and exact-patch behavior remains unverified. A localized web archive returned older cached content during this check; treat search snippets/archive freshness separately from the retrieved API record. The API externalpost HTTP redirect resolves to the existing canonical event citation; this establishes URL mapping separately from the API text retrieval.

The housing-reference release promotes two exact original summaries reviewed in HOUSING_REFERENCE_REVIEW.json. Their canonical developer comment IDs, author badges, publication epochs and body hashes remain separate from quoted community replies. Unknown exact/family/future compatibility remains explicit; no current numeric distance, eligibility, geometry, optimal blueprint or later-fix delivery is established. The fifteen-record corpus passes 45 actual MCP cases; local evaluation does not refresh source-review dates. See HOUSING_REFERENCE_RELEASE_VALIDATION.json for seed preservation and exact player evidence.
