from pathlib import Path
from typing import Final, Literal

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

AGENTS_STATUS_EVENT_LIMIT: Final[int] = 256
AGENTS_STATUS_TIMEOUT_SECONDS: Final[float] = 10.0
AGENTS_STATUS_WORKERS: Final[int] = 8

T3_SERVER_URL: Final[str] = "http://127.0.0.1:10000"
T3_MCP_PROTOCOL_VERSION: Final[str] = "2025-06-18"
T3_OAUTH_REDIRECT_URI: Final[str] = "http://127.0.0.1/stackops-t3-callback"
T3_PAIRING_TTL: Final[str] = "5m"
T3_HTTP_TIMEOUT_SECONDS: Final[float] = 120.0
T3_RUNTIME_MODE: Final[Literal["full-access"]] = "full-access"
T3_FULL_ACCESS_SCOPES: Final[tuple[str, ...]] = ("orchestration:read", "orchestration:operate", "settings:write", "source-control:write")
T3_REASONING_OPTION_IDS: Final[tuple[str, ...]] = ("effort", "reasoningEffort")
T3_TITLE_MAX_CHARS: Final[int] = 60
