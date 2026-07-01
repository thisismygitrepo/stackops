from pathlib import Path

import pytest

from stackops.secrets import passwords
from stackops.secrets.models import Login


def test_read_named_password_returns_unique_match(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_search_logins(*, path: str | Path | None, login_name: str | None, keys: tuple[str, ...]) -> list[Login]:
        assert path == passwords.SECRETS_DOFILE
        assert login_name == "bitsense"
        assert keys == ("PASSWORD",)
        return [{"name": "bitsense", "secrets": [{"name": "archive", "tags": [], "scopes": [], "keyValues": {"PASSWORD": "not-a-real-secret"}}]}]

    monkeypatch.setattr(passwords, "search_logins", fake_search_logins)

    assert passwords.read_named_password(password_name=" bitsense ") == "not-a-real-secret"


def test_read_named_password_prompts_for_multiple_matches(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    matches: list[Login] = [
        {"name": "bitsense", "secrets": [{"name": "old-archive", "tags": [], "scopes": [], "keyValues": {"PASSWORD": "first-placeholder"}}]},
        {"name": "bitsense", "secrets": [{"name": "current-archive", "tags": [], "scopes": [], "keyValues": {"PASSWORD": "second-placeholder"}}]},
    ]

    def fake_search_logins(*, path: str | Path | None, login_name: str | None, keys: tuple[str, ...]) -> list[Login]:
        _ = path, login_name, keys
        return matches

    def fake_prompt(text: str, **kwargs: object) -> int:
        assert text == "Select password"
        assert kwargs == {"type": int}
        return 2

    monkeypatch.setattr(passwords, "search_logins", fake_search_logins)
    monkeypatch.setattr(passwords.typer, "prompt", fake_prompt)

    assert passwords.read_named_password(password_name="bitsense") == "second-placeholder"
    output = capsys.readouterr().out
    assert "old-archive" in output
    assert "current-archive" in output
    assert "first-placeholder" not in output
    assert "second-placeholder" not in output


def test_read_named_password_rejects_missing_match(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_search_logins(*, path: str | Path | None, login_name: str | None, keys: tuple[str, ...]) -> list[Login]:
        _ = path, login_name, keys
        return []

    monkeypatch.setattr(passwords, "search_logins", fake_search_logins)

    with pytest.raises(ValueError, match="No StackOps secrets login"):
        passwords.read_named_password(password_name="bitsense")
