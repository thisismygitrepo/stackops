

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest

from stackops.utils.cloud.onedrive import auth


@dataclass(slots=True)
class FakeResponse:
    status_code: int
    payload: dict[str, object]
    text: str = ""

    def json(self) -> dict[str, object]:
        return self.payload


@pytest.fixture(autouse=True)
def clear_auth_cache() -> Iterator[None]:
    auth.clear_config_cache()
    yield
    auth.clear_config_cache()


def test_get_config_parses_rclone_token_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get_rclone_token(section: str) -> dict[str, str] | None:
        assert section == "work"
        return {"token": """{"access_token": "abc", "expiry": "2030-01-01T00:00:00"}""", "drive_id": "drive-123"}

    monkeypatch.setattr(auth, "get_rclone_token", fake_get_rclone_token)

    config = auth.get_config("work")

    assert config["token"] == {"access_token": "abc", "expiry": "2030-01-01T00:00:00"}
    assert config["drive_id"] == "drive-123"
    assert config["drive_type"] == "personal"


def test_is_token_valid_requires_more_than_five_minutes(monkeypatch: pytest.MonkeyPatch) -> None:
    future_expiry = (auth.datetime.now() + auth.timedelta(minutes=10)).isoformat() + "Z"
    near_expiry = (auth.datetime.now() + auth.timedelta(minutes=4)).isoformat() + "+00:00"
    tokens: dict[str, dict[str, str]] = {"fresh": {"expiry": future_expiry}, "stale": {"expiry": near_expiry}}

    def fake_get_token(section: str) -> dict[str, object]:
        return tokens[section]

    monkeypatch.setattr(auth, "get_token", fake_get_token)

    assert auth.is_token_valid("fresh")
    assert not auth.is_token_valid("stale")


def test_load_token_from_file_updates_cached_token(tmp_path: Path) -> None:
    token_path = tmp_path.joinpath("token.json")
    token_path.write_text("""{"access_token": "loaded-token"}""", encoding="utf-8")
    auth._cached_config = {"token": {"access_token": "stale-token"}}

    loaded = auth.load_token_from_file(str(token_path))

    assert loaded == {"access_token": "loaded-token"}
    assert auth._cached_config == {"token": {"access_token": "loaded-token"}}


def test_refresh_access_token_updates_cache_and_persists_token(monkeypatch: pytest.MonkeyPatch) -> None:
    saved_payloads: list[tuple[dict[str, object], str]] = []

    def fake_get_token(section: str) -> dict[str, object]:
        assert section == "work"
        return {"refresh_token": "old-refresh"}

    def fake_post(url: str, data: dict[str, str], headers: dict[str, str]) -> FakeResponse:
        assert url == auth.OAUTH_TOKEN_ENDPOINT
        assert data["refresh_token"] == "old-refresh"
        assert data["client_secret"] == "configured-secret"
        assert headers["Content-Type"] == "application/x-www-form-urlencoded"
        return FakeResponse(
            status_code=200, payload={"access_token": "new-access", "refresh_token": "new-refresh", "expires_in": 600, "token_type": "Bearer"}
        )

    def fake_save_token_to_file(token_data: dict[str, object], file_path: str) -> bool:
        saved_payloads.append((token_data, file_path))
        return True

    monkeypatch.setattr(auth, "CLIENT_SECRET", "configured-secret")
    monkeypatch.setattr(auth, "get_token", fake_get_token)
    monkeypatch.setattr(auth.requests, "post", fake_post)
    monkeypatch.setattr(auth, "save_token_to_file", fake_save_token_to_file)
    auth._cached_config = {"token": {"refresh_token": "old-refresh"}}

    refreshed = auth.refresh_access_token("work")

    assert refreshed is not None
    assert refreshed["access_token"] == "new-access"
    assert refreshed["refresh_token"] == "new-refresh"
    assert auth._cached_config == {"token": refreshed}
    assert len(saved_payloads) == 1
    assert saved_payloads[0][0]["access_token"] == "new-access"
    assert saved_payloads[0][1] == auth.DEFAULT_TOKEN_FILE


def test_make_graph_request_adds_bearer_header(monkeypatch: pytest.MonkeyPatch) -> None:
    request_calls: list[tuple[str, str, dict[str, str]]] = []
    response = FakeResponse(status_code=200, payload={})

    def fake_get_access_token(section: str) -> str | None:
        assert section == "work"
        return "access-token"

    def fake_request(method: str, url: str, headers: dict[str, str]) -> FakeResponse:
        request_calls.append((method, url, headers))
        return response

    monkeypatch.setattr(auth, "get_access_token", fake_get_access_token)
    monkeypatch.setattr(auth.requests, "request", fake_request)

    result = auth.make_graph_request("GET", "/me/drive", section="work", headers={"X-Test": "1"})

    assert result is response
    assert request_calls == [("GET", f"{auth.GRAPH_API_BASE}/me/drive", {"X-Test": "1", "Authorization": "Bearer access-token"})]
