# Shared Kali device — local Claude and Codex

Claude is running as a local/remote-controlled collaborator on this same device. No cloud execution environment, uploaded game installation or credential transfer is required. The portable workflow remains [CONTRIBUTING.md](CONTRIBUTING.md); these are observed local paths as of 2026-10-18, not dependencies guaranteed on another machine.

## Separate editing checkouts

The existing checkout is `/home/kali/Projects/songs-of-syx-ai-assistant`. Use it serially, or clone a separate directory for Claude's concurrent edits and create a topic branch there. A branch in the same directory does not isolate files from another agent. Do not switch/reset the other agent's checkout.

This device already has an authorized SSH host alias usable without copying private keys:

```sh
git clone git@github-syx-assistant:StudioCordillera/songs-of-syx-ai-assistant.git \
  /home/kali/Projects/songs-of-syx-ai-assistant-claude
cd /home/kali/Projects/songs-of-syx-ai-assistant-claude
python3 dev/collaboration_status.py
git switch -c claude/core-topic
```

Use a different branch name if it already exists. The public HTTPS URL also permits cloning; pushing requires the user's existing authorized GitHub authentication. Do not read, copy or commit SSH private keys. Follow CONTRIBUTING's comparison/reconciliation workflow before integrating or publishing; neither model's changes win by default.

## Existing read-only tools and game

Check these paths exist before using them:

```sh
export SYX_GAME_DIR='/run/media/kali/New Volume/SteamLibrary/steamapps/common/Songs of Syx'
export SYX_GAME_JAVA='/home/kali/Projects/songs-of-syx-ai-assistant/.tools/java21/usr/lib/jvm/java-21-openjdk-amd64/bin/java'
export SYX_JAVA_HOME='/home/kali/Projects/songs-of-syx-ai-assistant/.tools/jdk/usr/lib/jvm/java-25-openjdk-amd64'
```

The licensed game/source pair is 0.71.44; audit hashes establish the actual pair. The ignored tool runtimes can be used read-only from another checkout. Create that checkout's own .venv and build/runtime output. An editable Python install points at its source checkout, so do not share the first checkout's .venv for another agent's code.

The existing checkout has an initialized `runtime/smoke-home` and `runtime/smoke.save`, both private/ignored. A separate checkout needs its own fixture home and a **copy** of the test save, not a symlink to an original or another runner's active profile. Use the fixture install/setup in CONTRIBUTING. Never use the normal `~/.local/share/songsofsyx` profile as a mutable fixture.

## Shared native resource and credentials

The native display/game installation is shared across checkouts. Core/chat/cost runners take a machine-wide advisory lock at `~/.cache/syx-ai-assistant/game-fixture.lock`; `SYX_DEV_LOCK_DIR` is an explicit override for a deliberately separate test resource, not a way to bypass another runner. The lock records PID/checkout/time, contains no key and is released by the kernel if the owner exits. Do not delete a held lock, kill another agent's test or overlap manual fixture processes. Wrap manual native harnesses with `python3 dev/game_fixture_lock.py -- <fixture-command>`. Do not double-wrap a runner that already locks.

Claude's framework cannot inject environment variables here. The existing checkout has an ignored `.env` with a literal DEEPSEEK_API_KEY entry, mode 0600. Use `dev/run_player_chat_check.py ... --env-file .env` as in CONTRIBUTING; never print the file. A separate checkout needs its own privately supplied/copy of .env; do not copy it through Git. The helper reads it as data, strips keys from game/MCP children and restores its own copied-profile mod. Offline checks need no key. A published player bundle excludes credentials and all fixture/history artifacts.

Do not change the user's audio mute or minimum display brightness while testing. A working native display/OpenGL session is still needed; there is no screenshot/native-input test driver. If a mount, runtime or display is unavailable, complete portable/offline work and describe the specific unvalidated gate without claiming a native pass.


## Ready-to-run paid check on the existing checkout

This command needs no framework environment-variable injection. The local .env supplies the key; all other paths are explicit. It makes two real Pro turns, so run it only for an intended paid integration check:

```sh
cd /home/kali/Projects/songs-of-syx-ai-assistant
.venv/bin/python dev/run_player_chat_check.py \
  --game-dir '/run/media/kali/New Volume/SteamLibrary/steamapps/common/Songs of Syx' \
  --save runtime/smoke.save \
  --java '/home/kali/Projects/songs-of-syx-ai-assistant/.tools/java21/usr/lib/jvm/java-21-openjdk-amd64/bin/java' \
  --jdk-home '/home/kali/Projects/songs-of-syx-ai-assistant/.tools/jdk/usr/lib/jvm/java-25-openjdk-amd64' \
  --env-file .env
```

For a separate checkout, change the first cd and use its own .venv, private .env and copied runtime fixtures. The licensed game and read-only Java/JDK paths can stay shared. Run offline pytest/documentation/release checks without a provider key first.
