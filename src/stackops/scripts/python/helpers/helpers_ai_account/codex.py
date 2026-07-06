from pathlib import Path
from typing import Final, cast

from stackops.scripts.python.helpers.helpers_ai_account.json_values import JsonObject, decode_jwt_payload, read_json_object, read_optional_json_string
from stackops.scripts.python.helpers.helpers_ai_account.models import CredentialIdentity, FileAgentSupport, RuntimeContext


_AUTH_CLAIMS_KEY: Final[str] = "https://api.openai.com/auth"


def _resolve_active_credential(context: RuntimeContext) -> Path:
    configured_codex_home = context.environment.get("CODEX_HOME")
    if configured_codex_home is None:
        codex_home = context.home / ".codex"
    else:
        if configured_codex_home == "":
            raise ValueError("CODEX_HOME must not be empty")
        codex_home = Path(configured_codex_home)
    return codex_home / "auth.json"


def _read_identity(path: Path) -> CredentialIdentity | None:
    credential = read_json_object(path)
    tokens_value = credential.get("tokens")
    if tokens_value is None:
        api_key = read_optional_json_string(credential, ("OPENAI_API_KEY",), path)
        if api_key is not None:
            return None
        raise ValueError(f"Codex credential contains neither ChatGPT tokens nor an API key: {path}")
    if not isinstance(tokens_value, dict):
        raise ValueError(f"Credential field tokens must contain a JSON object: {path}")

    id_token = read_optional_json_string(credential, ("tokens", "id_token"), path)
    if id_token is None:
        raise ValueError(f"Credential file is missing required field tokens.id_token: {path}")
    payload = decode_jwt_payload(id_token, path)

    claims_value = payload.get(_AUTH_CLAIMS_KEY)
    if claims_value is None:
        return None
    if not isinstance(claims_value, dict):
        raise ValueError(f"Credential JWT field {_AUTH_CLAIMS_KEY} must contain a JSON object: {path}")
    claims = cast(JsonObject, claims_value)

    chatgpt_user_id = read_optional_json_string(claims, ("chatgpt_user_id",), path)
    legacy_user_id = read_optional_json_string(claims, ("user_id",), path)
    user_id = chatgpt_user_id if chatgpt_user_id is not None else legacy_user_id
    chatgpt_account_id = read_optional_json_string(claims, ("chatgpt_account_id",), path)
    if user_id is None or chatgpt_account_id is None:
        return None

    stored_account_id = read_optional_json_string(credential, ("tokens", "account_id"), path)
    if stored_account_id is not None and stored_account_id != chatgpt_account_id:
        raise ValueError(f"Codex credential workspace identifiers do not match: {path}")
    return (user_id, chatgpt_account_id)


SUPPORT: Final[FileAgentSupport] = FileAgentSupport(
    agent="codex",
    display_name="Codex",
    aliases=("x",),
    backup_directory_name="codex",
    profile_file_name=Path("auth.json"),
    resolve_active_credential=_resolve_active_credential,
    read_identity=_read_identity,
    warning="Requires Codex file credential storage; keyring-only credentials are not profile-backed.",
)
