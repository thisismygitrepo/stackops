import json
import os
from pathlib import Path
from stat import S_IMODE

import pytest

from stackops.secrets.loader import load_secrets_file
from stackops.secrets.models import Login, SecretsFile
from stackops.utils.cloud.onedrive.accounts import OneDriveAccountSummary, add_account, build_account_login, list_accounts
from stackops.utils.cloud.onedrive.errors import OneDriveError


def _write_secrets_file(secrets_path: Path, entries: list[Login]) -> None:
    secrets_file: SecretsFile = {"version": "0.5", "entries": entries}
    secrets_path.write_text(json.dumps(secrets_file), encoding="utf-8")


def _generic_onedrive_login(account_name: str, client_id: str) -> Login:
    return {
        "name": "onedrive",
        "accountName": account_name,
        "tags": ["onedrive"],
        "secrets": [{"name": "oauth", "tags": ["oauth"], "scopes": [], "keyValues": {"ONEDRIVE_CLIENT_ID": client_id}}],
    }


def test_add_account_appends_a_tagged_entry_without_colliding_with_generic_onedrive(tmp_path: Path) -> None:
    secrets_path = tmp_path / "secrets.json"
    generic_login = _generic_onedrive_login(account_name="odp", client_id="generic-client")
    _write_secrets_file(secrets_path=secrets_path, entries=[generic_login])
    os.chmod(secrets_path, 0o640)

    add_account(secrets_path=secrets_path, account_name="odp", client_id="stackops-client")

    secrets_file = load_secrets_file(secrets_path)
    assert secrets_file["entries"] == [
        generic_login,
        {
            "name": "onedrive",
            "accountName": "odp",
            "tags": ["onedrive-stackops-cli"],
            "secrets": [
                {
                    "name": "oauth",
                    "tags": ["oauth"],
                    "scopes": ["User.Read", "Files.ReadWrite", "offline_access"],
                    "keyValues": {"ONEDRIVE_CLIENT_ID": "stackops-client"},
                }
            ],
        },
    ]
    assert S_IMODE(secrets_path.stat().st_mode) == 0o640


def test_add_account_creates_a_missing_private_secrets_catalog(tmp_path: Path) -> None:
    secrets_path = tmp_path / "new-secrets" / "secrets.json"

    add_account(secrets_path=secrets_path, account_name="odp", client_id="stackops-client")

    secrets_file = load_secrets_file(secrets_path)
    assert secrets_file == {
        "version": "0.5",
        "entries": [build_account_login(account_name="odp", client_id="stackops-client", refresh_token=None)],
    }
    assert S_IMODE(secrets_path.parent.stat().st_mode) == 0o700
    assert S_IMODE(secrets_path.stat().st_mode) == 0o600


def test_add_account_refuses_an_existing_tagged_account_without_rewriting(tmp_path: Path) -> None:
    secrets_path = tmp_path / "secrets.json"
    existing_login = build_account_login(account_name="odp", client_id="existing-client", refresh_token=None)
    _write_secrets_file(secrets_path=secrets_path, entries=[existing_login])
    original_bytes = secrets_path.read_bytes()

    with pytest.raises(OneDriveError, match="already defined"):
        add_account(secrets_path=secrets_path, account_name="odp", client_id="replacement-client")

    assert secrets_path.read_bytes() == original_bytes


def test_list_accounts_filters_generic_entries_and_reports_sorted_authentication_state(tmp_path: Path) -> None:
    secrets_path = tmp_path / "secrets.json"
    _write_secrets_file(
        secrets_path=secrets_path,
        entries=[
            _generic_onedrive_login(account_name="ignored", client_id="generic-client"),
            build_account_login(account_name="zeta", client_id="zeta-client", refresh_token=None),
            build_account_login(account_name="alpha", client_id="alpha-client", refresh_token="refresh-token"),
        ],
    )

    accounts = list_accounts(secrets_path)

    assert accounts == (
        OneDriveAccountSummary(account_name="alpha", authentication="authenticated"),
        OneDriveAccountSummary(account_name="zeta", authentication="required"),
    )
