"""Developer-only reference loop in the unchanged simple file-IPC coordinator.

Explicit construction only: no player entry point, key loading, server startup or
production global changes. The caller owns the MCP session, provider and history.
"""
from syx_chat_service import Coordinator
from syx_chat import INSTRUCTIONS
from dev.blueprint_chat_candidate import BlueprintConversation
from dev.blueprint_mcp_candidate import isolated_state_dir


class BlueprintCoordinator(Coordinator):
    def __init__(self, store, mcp, state_dir, api_key, *, provider_factory):
        directory = isolated_state_dir(str(state_dir))
        # Both data roots must be disposable before the parent writes its action journal.
        isolated_state_dir(str(store.directory))
        super().__init__(store, mcp, directory, api_key, simple=True)
        original_instructions = self.loop.instructions
        reference_loop = BlueprintConversation(store, mcp, provider_factory)
        # Preserve the exact simple-player presentation policy as well as reference caveats.
        reference_loop.instructions = original_instructions + reference_loop.instructions.removeprefix(INSTRUCTIONS)
        self.loop = reference_loop
