import json
import shlex
from typing import TypedDict

from stackops.secrets.loader import SecretsSchemaError
from stackops.secrets.models import SecretsFile
from stackops.secrets.paths import SECRETS_DOFILE
from stackops.secrets.writer import replace_secrets_file
from stackops.utils.cloud.onedrive.accounts import (
    OneDriveAccount,
    build_account_login,
    load_account_registry,
    validate_account_name,
    validate_client_id,
)
from stackops.utils.cloud.onedrive.constants import CLIENT_ID_KEY, LOGIN_NAME, LOGIN_TAG, REFRESH_TOKEN_KEY, SECRET_NAME
from stackops.utils.cloud.onedrive.errors import OneDriveError


class OneDriveCredentials(TypedDict):
    account_name: str
    client_id: str
    refresh_token: str | None


def _load_account(account_name: str) -> tuple[SecretsFile, OneDriveAccount]:
    validate_account_name(account_name)
    secrets_file, accounts = load_account_registry(SECRETS_DOFILE)
    matches = [account for account in accounts if account.account_name == account_name]
    expected_entry = build_account_login(account_name=account_name, client_id="<client-id>", refresh_token=None)
    expected_json = json.dumps(expected_entry, indent=2, ensure_ascii=False)
    if not matches:
        setup_command = f"cloud onedrive add {shlex.quote(account_name)}"
        raise OneDriveError(
            f"No OneDrive CLI OAuth secret matched account {account_name!r} in {SECRETS_DOFILE}.\n"
            f"Create the correctly tagged entry with:\n  {setup_command}\n"
            f"This uses login name {LOGIN_NAME!r}, required login tag {LOGIN_TAG!r}, and secret name {SECRET_NAME!r}.\n"
            f"Expected exactly one object inside the top-level entries array:\n{expected_json}"
        )
    if len(matches) != 1:
        raise OneDriveError(
            f"Multiple OneDrive CLI OAuth secrets matched account {account_name!r} in {SECRETS_DOFILE}.\n"
            f"Run: cloud onedrive accounts\n"
            f"Keep exactly one object inside the top-level entries array shaped like:\n{expected_json}"
        )
    return secrets_file, matches[0]


def load_credentials(account_name: str, require_refresh_token: bool) -> OneDriveCredentials:
    _, account = _load_account(account_name)
    if require_refresh_token and account.refresh_token is None:
        raise OneDriveError(
            f"OneDrive account {account_name!r} is not authenticated because {REFRESH_TOKEN_KEY} is missing.\n"
            f"Run: cloud onedrive auth {shlex.quote(account_name)}"
        )
    return {"account_name": account.account_name, "client_id": account.client_id, "refresh_token": account.refresh_token}


def save_refresh_token(account_name: str, client_id: str, refresh_token: str) -> None:
    validate_client_id(client_id)
    if refresh_token == "" or refresh_token != refresh_token.strip():
        raise OneDriveError("Microsoft refresh token must be non-empty and must not start or end with whitespace.")

    secrets_file, account = _load_account(account_name)
    if account.client_id != client_id:
        raise OneDriveError(f"Refusing to save authentication for OneDrive account {account_name!r}: {CLIENT_ID_KEY} changed in {SECRETS_DOFILE}.")
    account.secret["keyValues"][REFRESH_TOKEN_KEY] = refresh_token
    try:
        replace_secrets_file(secrets_path=SECRETS_DOFILE, secrets_file=secrets_file)
    except (OSError, SecretsSchemaError) as exc:
        raise OneDriveError(f"Unable to update OneDrive authentication in {SECRETS_DOFILE}: {exc}") from exc
