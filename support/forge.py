from pathlib import Path
from typing import Final

from support.models import FileAgentSupport, RuntimeContext


def resolve_active_credential(context: RuntimeContext) -> Path:
    configured_base_path = context.environment.get("FORGE_CONFIG")
    if configured_base_path is not None:
        return Path(configured_base_path) / ".credentials.json"

    legacy_base_path = context.home / "forge"
    if legacy_base_path.exists():
        return legacy_base_path / ".credentials.json"
    return context.home / ".forge" / ".credentials.json"


SUPPORT: Final[FileAgentSupport] = FileAgentSupport(
    agent="forge",
    display_name="Forge",
    aliases=("f",),
    backup_directory_name="forge",
    profile_file_name=Path(".credentials.json"),
    resolve_active_credential=resolve_active_credential,
    read_identity=None,
    warning="Automatic refresh requires an explicit --profile because Forge credentials have no safe account identity.",
)
