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

## Computer-use references (checked 2026-10-17)

- [OpenAI browser and desktop drivers](https://developers.openai.com/api/docs/guides/tools-computer-use-sdk-drivers): observations/actions and coordinate conventions; the game needs its own driver.
- [Computer-use integration recipes](https://developers.openai.com/api/docs/guides/tools-computer-use-integration): screenshot-based integration patterns.
- [Plan-usage preview limitations](https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations): native computer use and hosted MCP are excluded on this route; local function/custom-tool execution is a separate integration concern.

These establish integration constraints; the local driver validation is documented in VALIDATION.md. They do not guarantee account/model availability.

## Gameplay evidence shipped with this prototype

Installed resource, technology and stat help text is indexed at runtime, with current version/mods and original class/key identifiers. It is not bundled from proprietary game files.

Five short authored summaries, checked 2026-10-17, can be installed with `syx-knowledge`: [v71 community guide](https://steamcommunity.com/sharedfiles/filedetails/?id=3776333166) , [official V71 law/family/trade release notes](https://steamcommunity.com/games/1162750/announcements/detail/529882384083977659), and [historical developer reply about eatery overlays](https://steamcommunity.com/app/1162750/discussions/0/4841941418359552221/). Source records retain authority and compatibility caveats. These do not establish exhaustive current mechanics.
