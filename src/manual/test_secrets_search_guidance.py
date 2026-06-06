import json
from pathlib import Path

import pytest

from stackops.secrets import MissingLoginError, build_missing_login_guidance, require_login


def _write_secrets(path: Path, entries: list[dict[str, object]]) -> None:
    path.write_text(json.dumps({"version": "0.5", "entries": entries}), encoding="utf-8")


def test_require_login_returns_one_matching_secret(tmp_path: Path) -> None:
    secrets_path = tmp_path / "secrets.json"
    _write_secrets(
        secrets_path,
        [
            {
                "name": "home-wifi",
                "tags": ["wifi"],
                "secrets": [
                    {
                        "name": "credentials",
                        "keyValues": {"ssid": "Home", "password": "redacted"},
                    }
                ],
            }
        ],
    )

    login = require_login(path=secrets_path, login_name="home-wifi", tags=("wifi",), keys=("ssid", "password"))

    assert login["name"] == "home-wifi"
    assert login["secrets"][0]["keyValues"] == {"ssid": "Home", "password": "redacted"}


def test_require_login_missing_entry_raises_guidance(tmp_path: Path) -> None:
    secrets_path = tmp_path / "secrets.json"
    _write_secrets(
        secrets_path,
        [
            {
                "name": "other-login",
                "secrets": [{"name": "credentials", "keyValues": {"TOKEN": "redacted"}}],
            }
        ],
    )

    with pytest.raises(MissingLoginError) as exc_info:
        require_login(
            path=secrets_path,
            login_name="bitwarden",
            account_name="work",
            keys=("BW_CLIENTID", "BW_CLIENTSECRET", "BW_PASSWORD"),
            key_examples={"BW_CLIENTID": "<client-id>"},
        )

    message = str(exc_info.value)
    assert "No StackOps login entry matched the requested selectors." in message
    assert f"Secrets file: {secrets_path}" in message
    assert "- entries[].name = 'bitwarden'" in message
    assert "- entries[].accountName = 'work'" in message
    assert "- secret keyValues keys: 'BW_CLIENTID', 'BW_CLIENTSECRET', 'BW_PASSWORD'" in message
    assert '"name": "bitwarden"' in message
    assert '"accountName": "work"' in message
    assert '"BW_CLIENTID": "<client-id>"' in message
    assert '"BW_CLIENTSECRET": "<BW_CLIENTSECRET>"' in message


def test_missing_login_guidance_includes_required_tags_and_scopes(tmp_path: Path) -> None:
    secrets_path = tmp_path / "secrets.json"

    message = build_missing_login_guidance(
        path=secrets_path,
        login_name="service",
        tags=("automation",),
        login_tags=("prod",),
        secret_tags=("api-token",),
        scopes=("read", "write"),
        keys=("TOKEN",),
    )

    assert "- each tag must appear on the login or the secret: 'automation'" in message
    assert "- login-level tags: 'prod'" in message
    assert "- secret-level tags: 'api-token'" in message
    assert "- secret scopes: 'read', 'write'" in message
    assert '"tags": [' in message
    assert '"automation"' in message
    assert '"prod"' in message
    assert '"api-token"' in message
    assert '"scopes": [' in message
    assert '"TOKEN": "<TOKEN>"' in message
