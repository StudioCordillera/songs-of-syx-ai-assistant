# Completed local Claude Code prototype review

A tool-free peer-review invocation completed successfully on `claude-opus-5-5` through the local signed-in CLI, at high effort, after two max-effort generation attempts had exceeded our own runtime limits. The review supplied the independently authored prototype directly and returned concrete source findings. [Invocation evidence](CLAUDE_UX_COLLABORATION.json) preserves model/base/input/final-response hashes and scopes. No credits were purchased, no account limits bypassed and no production game actions/provider changes were requested. This is a completed review, not a Claude-generated native interface.

## Accepted and implemented

- **Drag initiation:** normal header drag starts immediately; the launcher retains hold/slop disambiguation. Its engaged hold has a visible ring and no longer becomes a click on release. Early movement announces the hold instruction.
- **Pointer lifecycle:** own browser pointer capture, lost-capture/blur/cancel handling and a primary-button guard prevent continuing a gesture after release. These browser contracts do not establish equivalent native game focus/capture APIs.
- **Render focus and scrolling:** own chat/read/source controls have stable focus keys. Rebuilding a list restores the corresponding focus, or the transcript after a read action removes its button. Scroll position is set synchronously with smooth scrolling disabled; the delayed-reply check confirms the chat button remains focused.
- **Reconnect visibility:** continuing a historical chat adds an explicit context-boundary notice, and a delayed final reply retains the turn's captured load. Earlier message loads remain immutable.

## Reviewed alternatives kept separate

The reviewer proposed a fork or confirmation before reconnecting a historical chat. The user explicitly wants automatic attachment, and the production design separates a chat's current attachment from original event provenance. We retained automatic reconnection with a visible boundary instead of adding another routine confirmation.

The reviewer correctly identified that the strict whole-card read gate cannot acknowledge a reply taller than the transcript. This is an intentional conservative candidate limit, still requiring a production policy decision. The refusal now also appears visibly. A proposed top/bottom-sentinel traversal alone cannot establish that every middle segment was displayed, unobscured and from the same layout/frame. We did not adopt it as receipt proof. The [detached coverage policy](CHAT_DISPLAY_CANDIDATE.md) and [native negative evidence](CHAT_VISIBILITY_BOUNDARY.md) remain authoritative acceptance limits.

The native-risk list was advice, not a new game-source audit. Public own-widget bounds already exist; complete clipping, occlusion, focus and input-capture semantics remain unestablished. Do not convert the review into a claim that all public geometry is absent, or that the browser checks prove a native contract.

## Recheck

[Prototype review evidence](PLAYER_CHAT_PROTOTYPE_VALIDATION.json) adds post-review browser checks: an actual immediate header drag moved x by -100 while y clamped; pointer resize changed 790×650 to 726×602; a stationary 500-ms launcher hold stayed closed and a subsequent short click opened it; a delayed completion preserved chat-button focus; and automatic continuation showed both the historical label and new boundary notice. These finite browser observations do not prove out-of-window release, touch/scaling, all resolutions, persistent receipt migration or native game acceptance. The runnable player ZIP and production source remain unchanged.
