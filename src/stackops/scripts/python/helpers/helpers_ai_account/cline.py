from pathlib import Path
from typing import Final, cast

from stackops.scripts.python.helpers.helpers_ai_account.json_values import JsonObject, read_json_object, read_optional_json_string
from stackops.scripts.python.helpers.helpers_ai_account.models import CredentialIdentity, FileAgentSupport, RuntimeContext


def _resolve_active_credential(context: RuntimeContext) -> Path:
    explicit_settings_path = context.environment.get("CLINE_PROVIDER_SETTINGS_PATH", "").strip()
    if explicit_settings_path:
        return Path(explicit_settings_path)

    explicit_data_directory = context.environment.get("CLINE_DATA_DIR", "").strip()
    if explicit_data_directory:
        data_directory = Path(explicit_data_directory)
    else:
        explicit_cline_directory = context.environment.get("CLINE_DIR", "").strip()
        cline_directory = Path(explicit_cline_directory) if explicit_cline_directory else context.home / ".cline"
        data_directory = cline_directory / "data"

    return data_directory / "settings" / "providers.json"


def _read_identity(path: Path) -> CredentialIdentity | None:
    document = read_json_object(path)
    version = document.get("version")
    if type(version) is not int or version != 1:
        raise ValueError(f"Cline credential file must have version 1: {path}")

    providers_value = document.get("providers")
    if not isinstance(providers_value, dict):
        raise ValueError(f"Cline credential file must contain a providers object: {path}")
    providers = cast(JsonObject, providers_value)

    cline_entry_value = providers.get("cline")
    if cline_entry_value is None:
        return None
    if not isinstance(cline_entry_value, dict):
        raise ValueError(f"Cline provider entry must contain an object: {path}")
    cline_entry = cast(JsonObject, cline_entry_value)

    settings_value = cline_entry.get("settings")
    if not isinstance(settings_value, dict):
        raise ValueError(f"Cline provider entry must contain a settings object: {path}")
    settings = cast(JsonObject, settings_value)
    if settings.get("provider") != "cline":
        raise ValueError(f"Cline provider settings must identify the cline provider: {path}")

    token_source = cline_entry.get("tokenSource")
    if token_source not in {"manual", "oauth", "migration"}:
        raise ValueError(f"Cline provider entry has an invalid tokenSource: {path}")
    if token_source != "oauth":
        return None

    account_id = read_optional_json_string(
        data=document,
        keys=("providers", "cline", "settings", "auth", "accountId"),
        path=path,
    )
    if account_id is None:
        return None
    return (account_id,)


SUPPORT: Final[FileAgentSupport] = FileAgentSupport(
    agent="cline",
    display_name="Cline",
    aliases=("cl",),
    backup_directory_name="cline",
    profile_file_name=Path("providers.json"),
    resolve_active_credential=_resolve_active_credential,
    read_identity=_read_identity,
    warning=None,
)
