

import pytest

from stackops.utils.cloud.onedrive import setup_oauth


def test_main_prints_setup_guidance_when_client_id_missing(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    calls: list[str] = []

    def fake_setup() -> None:
        calls.append("setup")

    monkeypatch.setattr(setup_oauth, "CLIENT_ID", "your_client_id_here")
    monkeypatch.setattr(setup_oauth, "CLIENT_SECRET", "your_client_secret_here")
    monkeypatch.setattr(setup_oauth, "REDIRECT_URI", "http://localhost:8080/callback")
    monkeypatch.setattr(setup_oauth, "setup_oauth_authentication", fake_setup)

    setup_oauth.main()

    captured = capsys.readouterr()
    assert "ONEDRIVE_CLIENT_ID environment variable not set" in captured.out
    assert "Azure App Registration Setup" in captured.out
    assert calls == []


def test_main_calls_setup_when_client_is_configured(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    calls: list[str] = []

    def fake_setup() -> None:
        calls.append("setup")

    monkeypatch.setattr(setup_oauth, "CLIENT_ID", "client-id")
    monkeypatch.setattr(setup_oauth, "CLIENT_SECRET", "client-secret")
    monkeypatch.setattr(setup_oauth, "REDIRECT_URI", "http://localhost:8080/callback")
    monkeypatch.setattr(setup_oauth, "setup_oauth_authentication", fake_setup)

    setup_oauth.main()

    captured = capsys.readouterr()
    assert "Client ID: client-id" in captured.out
    assert "Client Secret: [SET]" in captured.out
    assert "Starting OAuth setup" in captured.out
    assert calls == ["setup"]
