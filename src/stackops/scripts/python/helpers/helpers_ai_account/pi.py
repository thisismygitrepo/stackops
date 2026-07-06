from pathlib import Path
from typing import Final

from stackops.scripts.python.helpers.helpers_ai_account.models import FileAgentSupport, RuntimeContext


def _resolve_active_credential(context: RuntimeContext) -> Path:
    configured_directory = context.environment.get("PI_CODING_AGENT_DIR")
    if not configured_directory:
        agent_directory = context.home / ".pi" / "agent"
    elif configured_directory == "~":
        agent_directory = context.home
    elif configured_directory.startswith("~/"):
        agent_directory = context.home / configured_directory[2:]
    elif context.system == "Windows" and configured_directory.startswith("~\\"):
        agent_directory = context.home.joinpath(*configured_directory[2:].split("\\"))
    else:
        agent_directory = Path(configured_directory)
    return agent_directory / "auth.json"


SUPPORT: Final[FileAgentSupport] = FileAgentSupport(
    agent="pi",
    display_name="Pi",
    aliases=("p",),
    backup_directory_name="pi",
    profile_file_name=Path("auth.json"),
    resolve_active_credential=_resolve_active_credential,
    read_identity=None,
    warning="Pi profiles replace the complete multi-provider credential store; automatic refresh requires --profile.",
)
