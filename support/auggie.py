from pathlib import Path
from typing import Final

from support.models import FileAgentSupport, RuntimeContext


def resolve_active_credential(context: RuntimeContext) -> Path:
    return context.home / ".augment" / "session.json"


SUPPORT: Final[FileAgentSupport] = FileAgentSupport(
    agent="auggie",
    display_name="Auggie",
    aliases=("au",),
    backup_directory_name="auggie",
    profile_file_name=Path("session.json"),
    resolve_active_credential=resolve_active_credential,
    read_identity=None,
    warning="AUGMENT_SESSION_AUTH overrides the session file; automatic refresh requires --profile.",
)
