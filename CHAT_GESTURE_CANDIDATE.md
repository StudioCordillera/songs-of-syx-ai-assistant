# Mod-owned gesture candidate — not shipped

The game-independent model in dev/chat_gesture_candidate.py begins executing the drag/resize behavior requested in PLAYER_EXPERIENCE_PLAN.md. It is our own algorithm informed by the saved Claude review constraints, not a completed Claude design, visual prototype or native input implementation. No player module imports it and neither release ZIP packages it.

The native adapter must first classify an actual mod-owned launcher, header, empty chrome or resize handle and copy pointer/button primitives on the game thread. The candidate does not discover those surfaces, poll input, establish focus, identify game objects or control the game. Names of composer/citation/button/scroll/game targets are refused, but this does not prove native hit-testing is correct.

Candidate behavior:

- A stationary launcher press toggles only on release. Launcher motion requires a 350-ms hold and at least six internal coordinate units of movement. Early movement/release cancels the click rather than accidentally opening the menu. A completed drag drops without toggling.
- Explicit own header/chrome movement and resize can start without the launcher hold. Position/size remain clamped to the provided internal viewport. Candidate 480×320 minimums shrink when available bounds are smaller; they are not accepted native font/layout requirements.
- Capture cancels on own-surface deactivation, viewport change, out-of-bounds pointer, explicit cancel or a five-second total gesture timeout. This timeout is a bounded recovery policy for review, not proof of window focus; it can cancel a long deliberate drag. The inspected native focus getter remains private.
- Non-finite/coerced inputs, backwards time, malformed viewport and nested capture are refused. Invalid samples leave the last valid capture unchanged. Only explicit booleans are accepted for held/own-surface-active; the latter must not be presented as a window-focus measurement.

CHAT_GESTURE_CANDIDATE_VALIDATION.json records 25 offline state-transition cases, including click/hold/release, early-move suppression, edge clamping, small bounds, resize origin preservation, cancellation, invalid samples and recovery. No game, key, inference, normal saves, screens or native input are used.

Next: ask the entitled local Claude CLI after reset to critique the tradeoffs alongside CHAT_INPUT_BOUNDARY.md. Port only an accepted design into Java with own-widget input/capture routes, source/audit review, native gesture/focus/scene/scale cases and a source-matched player release. Theme, layout persistence/reset, typed attachments and unread display receipts are separate unfinished work.
