from pathlib import Path
from typing import Final

from support.models import FileAgentSupport, RuntimeContext


def _resolve_active_credential(context: RuntimeContext) -> Path:
    configured_data_home = context.environment.get("XDG_DATA_HOME")
    data_home = Path(configured_data_home) if configured_data_home else context.home / ".local" / "share"
    return data_home / "opencode" / "auth.json"


SUPPORT: Final[FileAgentSupport] = FileAgentSupport(
    agent="opencode",
    display_name="OpenCode",
    aliases=("o", "omp"),
    backup_directory_name="opencode",
    profile_file_name=Path("auth.json"),
    resolve_active_credential=_resolve_active_credential,
    read_identity=None,
    warning=(
        "An OpenCode profile replaces every persisted provider credential in auth.json; "
        "environment-backed credentials are unchanged, and automatic refresh requires --profile."
    ),
)
