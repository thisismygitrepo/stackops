from typing import Final

CODEX_EXEC_PERMISSION_ARGS: Final[tuple[str, ...]] = (
    "--sandbox",
    "workspace-write",
    "-c",
    "sandbox_workspace_write.network_access=true",
)
