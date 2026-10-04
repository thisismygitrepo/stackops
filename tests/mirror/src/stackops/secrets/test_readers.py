from dataclasses import FrozenInstanceError
from unittest.mock import Mock

import pytest

from stackops.secrets import readers
from stackops.secrets.models import Login
from stackops.secrets.readers import VirusTotalApiKey


def _login(account_name: str | None, api_key: object) -> Login:
    login: Login = {
        "name": "virusTotal",
        "secrets": [{"name": "api-key", "tags": [], "scopes": [], "keyValues": {"API_KEY": api_key}}],
    }
    if account_name is not None:
        login["accountName"] = account_name
    return login


def test_read_virus_total_api_keys_returns_all_accounts(monkeypatch: pytest.MonkeyPatch) -> None:
    search = Mock(return_value=[_login("dummy-account-one", "dummy-key-one"), _login("dummy-account-two", "dummy-key-two")])
    monkeypatch.setattr(readers, "search_logins", search)

    result = readers.read_virus_total_api_keys()

    assert result == (
        VirusTotalApiKey(account_name="dummy-account-one", api_key="dummy-key-one"),
        VirusTotalApiKey(account_name="dummy-account-two", api_key="dummy-key-two"),
    )
    search.assert_called_once_with(path=readers.SECRETS_DOFILE, login_name="virusTotal", keys=("API_KEY",))
    assert "dummy-key-one" not in repr(result)
    assert "dummy-key-two" not in repr(result)
    with pytest.raises(FrozenInstanceError):
        setattr(result[0], "api_key", "dummy-replacement-key")


@pytest.mark.parametrize(
    ("entries", "error_message"),
    [
        ([], "No VirusTotal API keys found"),
        ([_login(None, "dummy-key-one")], "non-empty accountName"),
        ([_login("", "dummy-key-one")], "non-empty accountName"),
        ([_login("   ", "dummy-key-one")], "non-empty accountName"),
        ([_login("dummy-account-one", "")], "API_KEY must be a non-empty string"),
        ([_login("dummy-account-one", "   ")], "API_KEY must be a non-empty string"),
        ([_login("dummy-account-one", 17)], "API_KEY must be a non-empty string"),
        (
            [_login("dummy-account-one", "dummy-key-one"), _login("dummy-account-one", "dummy-key-two")],
            "accountName values must be unique",
        ),
        (
            [_login("dummy-account-one", "dummy-key-one"), _login("dummy-account-two", "dummy-key-one")],
            "API_KEY values must be unique",
        ),
    ],
)
def test_read_virus_total_api_keys_rejects_invalid_accounts_without_exposing_values(
    monkeypatch: pytest.MonkeyPatch, entries: list[Login], error_message: str
) -> None:
    monkeypatch.setattr(readers, "search_logins", Mock(return_value=entries))

    with pytest.raises(ValueError, match=error_message) as raised:
        readers.read_virus_total_api_keys()

    for dummy_value in ("dummy-account-one", "dummy-account-two", "dummy-key-one", "dummy-key-two"):
        assert dummy_value not in str(raised.value)
