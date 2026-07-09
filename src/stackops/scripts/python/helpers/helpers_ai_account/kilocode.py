from pathlib import Path
from typing import Final

from stackops.scripts.python.helpers.helpers_ai_account.models import FileAgentSupport, RuntimeContext


def _resolve_active_credential(context: RuntimeContext) -> Path:
    configured_data_home = context.environment.get("XDG_DATA_HOME")
    data_home = Path(configured_data_home) if configured_data_home else context.home / ".local" / "share"
    return data_home / "kilo" / "auth.json"


SUPPORT: Final[FileAgentSupport] = FileAgentSupport(
    agent="kilocode",
    display_name="Kilo Code",
    aliases=("kilo", "k"),
    backup_directory_name="kilocode",
    profile_file_name=Path("auth.json"),
    resolve_active_credential=_resolve_active_credential,
    read_identity=None,
    warning=(
        "Kilo Code profiles cover every persisted provider credential in auth.json; "
        "environment-backed credentials are unchanged."
    ),
)
