import json
from pathlib import Path

import pytest

from stackops.secrets.loader import load_secrets_file
from stackops.secrets.models import Login, SecretsFile
from stackops.utils.cloud.onedrive import credentials
from stackops.utils.cloud.onedrive.accounts import build_account_login
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


def test_missing_credentials_points_to_the_dedicated_add_command_and_tag(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    secrets_path = tmp_path / "secrets.json"
    _write_secrets_file(secrets_path=secrets_path, entries=[_generic_onedrive_login(account_name="odp", client_id="generic-client")])
    monkeypatch.setattr(credentials, "SECRETS_DOFILE", secrets_path)

    with pytest.raises(OneDriveError) as error:
        credentials.load_credentials(account_name="odp", require_refresh_token=False)

    message = str(error.value)
    assert "cloud onedrive add --account-name odp" in message
    assert "login name 'onedrive'" in message
    assert "required login tag 'onedrive-stackops-cli'" in message
    assert '"tags": [\n    "onedrive-stackops-cli"' in message


def test_load_and_save_credentials_ignore_an_untagged_onedrive_collision(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    secrets_path = tmp_path / "secrets.json"
    generic_login = _generic_onedrive_login(account_name="odp", client_id="generic-client")
    tagged_login = build_account_login(account_name="odp", client_id="stackops-client", refresh_token=None)
    _write_secrets_file(secrets_path=secrets_path, entries=[generic_login, tagged_login])
    monkeypatch.setattr(credentials, "SECRETS_DOFILE", secrets_path)

    loaded_credentials = credentials.load_credentials(account_name="odp", require_refresh_token=False)
    credentials.save_refresh_token(account_name="odp", client_id="stackops-client", refresh_token="new-refresh-token")

    assert loaded_credentials == {"account_name": "odp", "client_id": "stackops-client", "refresh_token": None}
    updated_file = load_secrets_file(secrets_path)
    assert "ONEDRIVE_REFRESH_TOKEN" not in updated_file["entries"][0]["secrets"][0]["keyValues"]
    assert updated_file["entries"][1]["secrets"][0]["keyValues"]["ONEDRIVE_REFRESH_TOKEN"] == "new-refresh-token"
