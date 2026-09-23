from pathlib import Path
from typing import Final

DEEPSEEK_PRIVACY_PATCH_PATH: Final[Path] = Path(__file__).with_name("agentic_frameworks") / "deepseek_privacy.yaml"

CODEX_WORKSPACE_PERMISSION_ARGS: Final[tuple[str, ...]] = (
    "--sandbox",
    "workspace-write",
    "-c",
    "sandbox_workspace_write.network_access=true",
)

CODEX_EXEC_PERMISSION_ARGS: Final[tuple[str, ...]] = (
    *CODEX_WORKSPACE_PERMISSION_ARGS,
    "--skip-git-repo-check",
)
