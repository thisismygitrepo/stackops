from pathlib import Path
from typing import Final

from support.models import CredentialStorageUnavailableError, FileAgentSupport, RuntimeContext


def _resolve_active_credential(context: RuntimeContext) -> Path:
    match context.system:
        case "Darwin":
            data_local_directory = context.home / "Library" / "Application Support"
        case "Linux":
            xdg_data_home = context.environment.get("XDG_DATA_HOME")
            if xdg_data_home is None or xdg_data_home == "":
                data_local_directory = context.home / ".local" / "share"
            else:
                data_local_directory = Path(xdg_data_home)
                if not data_local_directory.is_absolute():
                    raise ValueError("XDG_DATA_HOME must be an absolute path")
        case unsupported_system:
            raise CredentialStorageUnavailableError(
                f"Amazon Q Developer CLI file credential storage is not verified on {unsupported_system}"
            )

    return data_local_directory / "amazon-q" / "data.sqlite3"


SUPPORT: Final[FileAgentSupport] = FileAgentSupport(
    agent="q",
    display_name="Amazon Q Developer CLI",
    aliases=(),
    backup_directory_name="q",
    profile_file_name=Path("data.sqlite3"),
    resolve_active_credential=_resolve_active_credential,
    read_identity=None,
    warning=(
        "Amazon Q stores credentials in a mixed-state SQLite database; stop q before installing or refreshing because "
        "the entire database, including conversations and persistent state, is replaced."
    ),
)
