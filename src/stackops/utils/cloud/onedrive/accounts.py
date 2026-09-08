from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from stackops.secrets.constants import SECRETS_FILE_VERSION
from stackops.secrets.loader import SecretsSchemaError, load_secrets_file
from stackops.secrets.models import Login, SecretRecord, SecretsFile, SecretValueMap
from stackops.secrets.writer import create_secrets_file, replace_secrets_file
from stackops.utils.cloud.onedrive.constants import CLIENT_ID_KEY, LOGIN_NAME, LOGIN_TAG, REFRESH_TOKEN_KEY, SCOPES, SECRET_NAME
from stackops.utils.cloud.onedrive.errors import OneDriveError


type AuthenticationStatus = Literal["required", "authenticated"]


@dataclass(frozen=True)
class OneDriveAccount:
    account_name: str
    client_id: str
    refresh_token: str | None
    secret: SecretRecord


@dataclass(frozen=True)
class OneDriveAccountSummary:
    account_name: str
    authentication: AuthenticationStatus


type LoadedAccountRegistry = tuple[SecretsFile, tuple[OneDriveAccount, ...]]


def validate_account_name(account_name: str) -> None:
    if account_name == "" or account_name != account_name.strip():
        raise OneDriveError("Account name must be non-empty and must not start or end with whitespace.")


def validate_client_id(client_id: str) -> None:
    if client_id == "" or client_id != client_id.strip():
        raise OneDriveError("Microsoft Application (client) ID must be non-empty and must not start or end with whitespace.")


def build_account_login(account_name: str, client_id: str, refresh_token: str | None) -> Login:
    key_values: SecretValueMap = {CLIENT_ID_KEY: client_id}
    if refresh_token is not None:
        key_values[REFRESH_TOKEN_KEY] = refresh_token
    return {
        "name": LOGIN_NAME,
        "accountName": account_name,
        "tags": [LOGIN_TAG],
        "secrets": [{"name": SECRET_NAME, "tags": [SECRET_NAME], "scopes": list(SCOPES), "keyValues": key_values}],
    }


def load_account_registry(secrets_path: Path) -> LoadedAccountRegistry:
    try:
        secrets_file = load_secrets_file(secrets_path)
    except (OSError, SecretsSchemaError) as exc:
        raise OneDriveError(str(exc)) from exc

    accounts: list[OneDriveAccount] = []
    account_names: set[str] = set()
    for login in secrets_file["entries"]:
        if login["name"] != LOGIN_NAME or LOGIN_TAG not in login.get("tags", ()):
            continue
        account_name = login.get("accountName")
        if account_name is None:
            raise OneDriveError(f"OneDrive CLI login tagged {LOGIN_TAG!r} must define accountName in {secrets_path}.")
        validate_account_name(account_name)
        if account_name in account_names:
            raise OneDriveError(f"OneDrive CLI account {account_name!r} is defined multiple times in {secrets_path}.")

        oauth_secrets = [secret for secret in login["secrets"] if secret["name"] == SECRET_NAME]
        if len(oauth_secrets) != 1:
            raise OneDriveError(
                f"OneDrive CLI account {account_name!r} must define exactly one secret named {SECRET_NAME!r} in {secrets_path}; "
                f"found {len(oauth_secrets)}."
            )
        secret = oauth_secrets[0]
        client_id_value = secret["keyValues"].get(CLIENT_ID_KEY)
        if not isinstance(client_id_value, str):
            raise OneDriveError(f"OneDrive CLI account {account_name!r} must define a string at {CLIENT_ID_KEY} in {secrets_path}.")
        validate_client_id(client_id_value)

        refresh_token_value = secret["keyValues"].get(REFRESH_TOKEN_KEY)
        if refresh_token_value is not None and (
            not isinstance(refresh_token_value, str) or refresh_token_value == "" or refresh_token_value != refresh_token_value.strip()
        ):
            raise OneDriveError(
                f"OneDrive CLI account {account_name!r} must define a non-empty string without edge whitespace at {REFRESH_TOKEN_KEY} in {secrets_path}."
            )
        account_names.add(account_name)
        accounts.append(
            OneDriveAccount(
                account_name=account_name,
                client_id=client_id_value,
                refresh_token=refresh_token_value,
                secret=secret,
            )
        )
    return secrets_file, tuple(sorted(accounts, key=lambda account: account.account_name))


def add_account(secrets_path: Path, account_name: str, client_id: str) -> None:
    validate_account_name(account_name)
    validate_client_id(client_id)
    create_catalog = not secrets_path.exists()
    if create_catalog:
        secrets_file: SecretsFile = {"version": SECRETS_FILE_VERSION, "entries": []}
        accounts: tuple[OneDriveAccount, ...] = ()
    else:
        secrets_file, accounts = load_account_registry(secrets_path)
    if any(account.account_name == account_name for account in accounts):
        raise OneDriveError(f"OneDrive CLI account {account_name!r} is already defined in {secrets_path}.")
    secrets_file["entries"].append(build_account_login(account_name=account_name, client_id=client_id, refresh_token=None))
    try:
        if create_catalog:
            create_secrets_file(secrets_path=secrets_path, secrets_file=secrets_file)
        else:
            replace_secrets_file(secrets_path=secrets_path, secrets_file=secrets_file)
    except (OSError, SecretsSchemaError) as exc:
        raise OneDriveError(f"Unable to add OneDrive CLI account {account_name!r} to {secrets_path}: {exc}") from exc


def list_accounts(secrets_path: Path) -> tuple[OneDriveAccountSummary, ...]:
    _, accounts = load_account_registry(secrets_path)
    return tuple(
        OneDriveAccountSummary(
            account_name=account.account_name,
            authentication="authenticated" if account.refresh_token is not None else "required",
        )
        for account in accounts
    )
