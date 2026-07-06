from pathlib import Path
from typing import Final

from stackops.scripts.python.helpers.helpers_ai_account.models import FileAgentSupport, RuntimeContext


def resolve_active_credential(context: RuntimeContext) -> Path:
    qwen_home = context.environment.get("QWEN_HOME")
    if not qwen_home:
        qwen_directory = context.home / ".qwen"
    elif qwen_home == "~":
        qwen_directory = context.home
    elif qwen_home.startswith("~/"):
        qwen_directory = context.home / qwen_home.removeprefix("~/")
    else:
        qwen_directory = Path(qwen_home)
    return qwen_directory / "settings.json"


SUPPORT: Final[FileAgentSupport] = FileAgentSupport(
    agent="qwen",
    display_name="Qwen Code",
    aliases=("qw",),
    backup_directory_name="qwen",
    profile_file_name=Path("settings.json"),
    resolve_active_credential=resolve_active_credential,
    read_identity=None,
    warning=(
        "Qwen Code credentials may be overridden by CLI flags, environment variables, .env files, or trusted-workspace settings; "
        "automatic refresh requires --profile because settings.json has no safe account identity."
    ),
)
