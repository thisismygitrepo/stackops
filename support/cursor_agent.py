from pathlib import Path
from typing import Final

from support.json_values import decode_jwt_payload, read_json_object, read_optional_json_string
from support.models import CredentialIdentity, CredentialStorageUnavailableError, FileAgentSupport, RuntimeContext


def _resolve_active_credential(context: RuntimeContext) -> Path:
    credential_store = context.environment.get("AGENT_CLI_CREDENTIAL_STORE")
    if credential_store == "memory":
        raise CredentialStorageUnavailableError("Cursor Agent is configured to keep credentials in memory")

    match context.system:
        case "Darwin":
            if credential_store != "file":
                raise CredentialStorageUnavailableError(
                    "Cursor Agent uses macOS Keychain by default; set AGENT_CLI_CREDENTIAL_STORE=file for file profiles"
                )
            return context.home / ".cursor" / "auth.json"
        case "Linux":
            xdg_config_home = context.environment.get("XDG_CONFIG_HOME")
            config_home = Path(xdg_config_home) if xdg_config_home else context.home / ".config"
            return config_home / "cursor" / "auth.json"
        case "Windows":
            app_data = context.environment.get("APPDATA")
            roaming_directory = Path(app_data) if app_data else context.home / "AppData" / "Roaming"
            return roaming_directory / "Cursor" / "auth.json"
        case unsupported_system:
            raise CredentialStorageUnavailableError(f"Cursor Agent credential storage is unsupported on {unsupported_system}")


def _read_identity(path: Path) -> CredentialIdentity | None:
    credential_data = read_json_object(path)
    access_token = read_optional_json_string(credential_data, ("accessToken",), path)
    refresh_token = read_optional_json_string(credential_data, ("refreshToken",), path)
    api_key = read_optional_json_string(credential_data, ("apiKey",), path)

    if access_token is None:
        if refresh_token is None and api_key is None:
            raise ValueError(f"Cursor Agent credential has no authentication fields: {path}")
        return None

    payload = decode_jwt_payload(access_token, path)
    subject = read_optional_json_string(payload, ("sub",), path)
    if subject is None:
        raise ValueError(f"Cursor Agent access-token JWT has no subject: {path}")
    return (subject,)


SUPPORT: Final[FileAgentSupport] = FileAgentSupport(
    agent="cursor-agent",
    display_name="Cursor Agent",
    aliases=("cursor", "agent"),
    backup_directory_name="cursor-agent",
    profile_file_name=Path("auth.json"),
    resolve_active_credential=_resolve_active_credential,
    read_identity=_read_identity,
    warning="macOS profile use requires AGENT_CLI_CREDENTIAL_STORE=file for every Cursor Agent invocation",
)
