import json
import os
import tempfile
from pathlib import Path
from stat import S_IMODE
from typing import TypedDict, cast

from stackops.secrets.models import Login, SecretValueMap
from stackops.secrets.paths import SECRETS_DOFILE
from stackops.secrets.search import SecretsFileError, search_logins
from stackops.utils.cloud.onedrive.constants import CLIENT_ID_KEY, LOGIN_NAME, REFRESH_TOKEN_KEY, SCOPES, SECRET_NAME
from stackops.utils.cloud.onedrive.errors import OneDriveError


class OneDriveCredentials(TypedDict):
    account_name: str
    client_id: str
    refresh_token: str | None


def _expected_entry(account_name: str, include_refresh_token: bool) -> Login:
    key_values: SecretValueMap = {CLIENT_ID_KEY: "<client-id>"}
    if include_refresh_token:
        key_values[REFRESH_TOKEN_KEY] = "<created by cloud onedrive auth>"
    return {
        "name": LOGIN_NAME,
        "accountName": account_name,
        "tags": [LOGIN_NAME],
        "secrets": [{"name": SECRET_NAME, "tags": [SECRET_NAME], "scopes": list(SCOPES), "keyValues": key_values}],
    }


def load_credentials(account_name: str, require_refresh_token: bool) -> OneDriveCredentials:
    if account_name == "" or account_name != account_name.strip():
        raise OneDriveError("--account-name must be non-empty and must not start or end with whitespace.")

    try:
        matches = search_logins(path=SECRETS_DOFILE, login_name=LOGIN_NAME, account_name=account_name, secret_name=SECRET_NAME)
    except (OSError, SecretsFileError) as exc:
        raise OneDriveError(str(exc)) from exc

    expected_json = json.dumps(_expected_entry(account_name=account_name, include_refresh_token=False), indent=2, ensure_ascii=False)
    authenticated_json = json.dumps(_expected_entry(account_name=account_name, include_refresh_token=True), indent=2, ensure_ascii=False)
    if not matches:
        raise OneDriveError(
            f"No OneDrive OAuth secret matched account {account_name!r} in {SECRETS_DOFILE}.\n"
            f"Expected exactly one entry shaped like:\n{expected_json}"
        )
    if len(matches) != 1:
        raise OneDriveError(
            f"Multiple OneDrive OAuth secrets matched account {account_name!r} in {SECRETS_DOFILE}.\n"
            f"Keep exactly one entry shaped like:\n{expected_json}"
        )

    key_values = matches[0]["secrets"][0]["keyValues"]
    client_id = key_values.get(CLIENT_ID_KEY)
    if not isinstance(client_id, str) or client_id.strip() == "":
        raise OneDriveError(f"OneDrive account {account_name!r} must define a non-empty string at {CLIENT_ID_KEY}.\nExpected entry:\n{expected_json}")

    refresh_token_value = key_values.get(REFRESH_TOKEN_KEY)
    if refresh_token_value is None:
        if require_refresh_token:
            raise OneDriveError(
                f"OneDrive account {account_name!r} is not authenticated because {REFRESH_TOKEN_KEY} is missing.\n"
                f"Run: cloud onedrive auth --account-name {account_name}"
            )
        refresh_token: str | None = None
    elif not isinstance(refresh_token_value, str) or refresh_token_value.strip() == "":
        raise OneDriveError(
            f"OneDrive account {account_name!r} must define a non-empty string at {REFRESH_TOKEN_KEY}.\n"
            f"Expected authenticated entry:\n{authenticated_json}"
        )
    else:
        refresh_token = refresh_token_value

    return {"account_name": account_name, "client_id": client_id, "refresh_token": refresh_token}


def save_refresh_token(account_name: str, client_id: str, refresh_token: str) -> None:
    if client_id.strip() == "":
        raise OneDriveError("Microsoft client ID must be non-empty.")
    if refresh_token.strip() == "":
        raise OneDriveError("Microsoft refresh token must be non-empty.")

    credentials = load_credentials(account_name=account_name, require_refresh_token=False)
    if credentials["client_id"] != client_id:
        raise OneDriveError(f"Refusing to save authentication for OneDrive account {account_name!r}: {CLIENT_ID_KEY} changed in {SECRETS_DOFILE}.")

    try:
        raw_payload: object = json.loads(SECRETS_DOFILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise OneDriveError(f"Unable to read StackOps secrets from {SECRETS_DOFILE}: {exc}") from exc
    if not isinstance(raw_payload, dict):
        raise OneDriveError(f"StackOps secrets must contain a JSON object: {SECRETS_DOFILE}")
    payload = cast(dict[str, object], raw_payload)
    raw_entries = payload.get("entries")
    if not isinstance(raw_entries, list):
        raise OneDriveError(f"StackOps secrets must define an entries array: {SECRETS_DOFILE}")

    matching_key_values: list[dict[str, object]] = []
    for raw_entry in raw_entries:
        if not isinstance(raw_entry, dict):
            raise OneDriveError(f"StackOps secrets contains a non-object login entry: {SECRETS_DOFILE}")
        entry = cast(dict[str, object], raw_entry)
        if entry.get("name") != LOGIN_NAME or entry.get("accountName") != account_name:
            continue
        raw_secrets = entry.get("secrets")
        if not isinstance(raw_secrets, list):
            raise OneDriveError(f"OneDrive account {account_name!r} must define a secrets array in {SECRETS_DOFILE}.")
        for raw_secret in raw_secrets:
            if not isinstance(raw_secret, dict):
                raise OneDriveError(f"OneDrive account {account_name!r} contains a non-object secret in {SECRETS_DOFILE}.")
            secret = cast(dict[str, object], raw_secret)
            if secret.get("name") != SECRET_NAME:
                continue
            raw_key_values = secret.get("keyValues")
            if not isinstance(raw_key_values, dict):
                raise OneDriveError(f"OneDrive account {account_name!r} secret {SECRET_NAME!r} must define keyValues in {SECRETS_DOFILE}.")
            matching_key_values.append(cast(dict[str, object], raw_key_values))

    if len(matching_key_values) != 1:
        raise OneDriveError(
            f"Expected exactly one OneDrive OAuth secret for account {account_name!r} in {SECRETS_DOFILE}; found {len(matching_key_values)}."
        )
    key_values = matching_key_values[0]
    if key_values.get(CLIENT_ID_KEY) != client_id:
        raise OneDriveError(f"Refusing to save authentication for OneDrive account {account_name!r}: {CLIENT_ID_KEY} changed in {SECRETS_DOFILE}.")
    key_values[REFRESH_TOKEN_KEY] = refresh_token

    descriptor: int | None = None
    temporary_path: Path | None = None
    try:
        descriptor, temporary_name = tempfile.mkstemp(prefix=f".{SECRETS_DOFILE.name}.", dir=SECRETS_DOFILE.parent)
        temporary_path = Path(temporary_name)
        os.chmod(temporary_path, S_IMODE(SECRETS_DOFILE.stat().st_mode))
        stream = os.fdopen(descriptor, "w", encoding="utf-8")
        descriptor = None
        with stream:
            json.dump(payload, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, SECRETS_DOFILE)
        temporary_path = None
    except OSError as exc:
        raise OneDriveError(f"Unable to update OneDrive authentication in {SECRETS_DOFILE}: {exc}") from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
