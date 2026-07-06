from pathlib import Path
from typing import Final

from support.models import CredentialStorageUnavailableError, FileAgentSupport, RuntimeContext


def resolve_active_credential(context: RuntimeContext) -> Path:
    match context.system:
        case "Darwin":
            raise CredentialStorageUnavailableError(
                "Claude Code stores credentials in the encrypted macOS Keychain; filesystem credential profiles are unavailable"
            )
        case "Linux" | "Windows":
            configured_directory = context.environment.get("CLAUDE_CONFIG_DIR")
            if configured_directory is not None:
                if configured_directory == "":
                    raise ValueError("CLAUDE_CONFIG_DIR must not be empty")
                return Path(configured_directory) / ".credentials.json"
            return context.home / ".claude" / ".credentials.json"
        case unsupported_system:
            raise CredentialStorageUnavailableError(
                f"Claude Code filesystem credential profiles are unavailable on {unsupported_system}"
            )


SUPPORT: Final[FileAgentSupport] = FileAgentSupport(
    agent="claude",
    display_name="Claude Code",
    aliases=("cc",),
    backup_directory_name="claude",
    profile_file_name=Path(".credentials.json"),
    resolve_active_credential=resolve_active_credential,
    read_identity=None,
    warning="Automatic refresh requires --profile because Claude Code credentials have no verified safe account identity.",
)
