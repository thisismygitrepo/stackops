from pathlib import Path
from typing import Final

from support.models import FileAgentSupport, RuntimeContext


def _resolve_active_credential(context: RuntimeContext) -> Path:
    crush_data_directory = context.environment.get("CRUSH_GLOBAL_DATA")
    if crush_data_directory:
        return Path(crush_data_directory) / "crush.json"

    xdg_data_home = context.environment.get("XDG_DATA_HOME")
    if xdg_data_home:
        return Path(xdg_data_home) / "crush" / "crush.json"

    if context.system == "Windows":
        local_app_data = context.environment.get("LOCALAPPDATA")
        if local_app_data:
            return Path(local_app_data) / "crush" / "crush.json"

        user_profile = context.environment.get("USERPROFILE")
        windows_home = Path(user_profile) if user_profile else context.home
        return windows_home / "AppData" / "Local" / "crush" / "crush.json"

    return context.home / ".local" / "share" / "crush" / "crush.json"


SUPPORT: Final[FileAgentSupport] = FileAgentSupport(
    agent="crush",
    display_name="Crush",
    aliases=("cr",),
    backup_directory_name="crush",
    profile_file_name=Path("crush.json"),
    resolve_active_credential=_resolve_active_credential,
    read_identity=None,
    warning=(
        "A Crush profile replaces its aggregate global data file; environment-, cloud-SDK-, and project-config-backed "
        "credentials are unchanged, and automatic refresh requires --profile."
    ),
)
