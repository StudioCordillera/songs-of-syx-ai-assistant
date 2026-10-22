SONGS OF SYX — DEEPSEEK PRO USER TEST (Linux)

Requires your licensed Songs of Syx 0.71.44, Python 3.11+ with venv/pip,
and a DeepSeek API key. The ZIP contains no game files or credentials.

1. Extract the whole ZIP into a regular folder.
2. Run: python3 install-mod.py
   For another game profile: python3 install-mod.py --user-dir /path/to/profile
   Your previous copy is backed up under that profile's syx-assistant-backups.
3. Run: sh start-chat.sh
   The first run installs Python dependencies and asks for your API key if needed.
   Keep this terminal open. Your key is stored privately outside this bundle.
4. Enable Syx AI Assistant in the game's launcher and load a game.
   Click AI chat. A conversation connects automatically. Ask a question and Send.

This player build uses DeepSeek Pro (deepseek-v4-pro). There is no provider
picker, subscription login, evidence JSON view, or developer control panel.
Messages and separate chats are saved locally. This load shows conversations
attached to the current runtime; All chats includes earlier loads. This does
not identify the same saved world across reloads. Sending in an older chat
connects the next question to the loaded game; earlier messages stay historical.
Install and restart the paired mod and helper together when updating.

The question box supports up to 240 characters with wrapping. Use follow-up
messages for longer questions. Send/Stop control the reply. The assistant uses
read-only game queries internally and cites retrieved guidance in its answers.
You can also ask: "Show the original warehouse teaching layout and cite its source."
This is an authored example with versioned furniture-footprint evidence, not a
validated building, storage-capacity estimate or automatic construction command.
Community/Workshop/video layout import and gameplay control are not included.
API requests use your DeepSeek balance; no request is sent until you Send.

Local chat history: ~/.local/share/syx-assistant-chat
Game bridge data: ~/.local/share/syx-assistant
Private key file: ~/.config/syx-ai-assistant/deepseek.env
Stop the helper with Ctrl+C. Re-run start-chat.sh to restart it.

Still experimental: game data and UI context are partial, not all menus or
all variables. Returning to the main menu can retain the prior observation
for up to 30 seconds before it becomes unknown. Physical keyboard/scaling
coverage is limited. Read the repository's validation reports for exact scope.

Latest tested download:
https://github.com/StudioCordillera/songs-of-syx-ai-assistant/raw/refs/heads/main/releases/latest-user-test.zip
Source and progress:
https://github.com/StudioCordillera/songs-of-syx-ai-assistant
