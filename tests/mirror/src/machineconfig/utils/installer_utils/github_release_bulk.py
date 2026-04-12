from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest

import machineconfig.utils.installer_utils.github_release_bulk as github_release_bulk


@dataclass(frozen=True, slots=True)
class FakeApiResponse:
    status_code: int
    payload: dict[str, object]

    def json(self) -> dict[str, object]:
        return self.payload


def test_extract_github_repos_from_json_filters_non_github_and_duplicates(tmp_path: Path) -> None:
    json_path = tmp_path.joinpath("installers.json")
    json_path.write_text(
        json.dumps(
            {
                "installers": [
                    {"repoURL": "https://github.com/example/tool"},
                    {"repoURL": "https://github.com/example/tool"},
                    {"repoURL": "https://example.com/not-github"},
                ]
            }
        ),
        encoding="utf-8",
    )

    result = github_release_bulk.extract_github_repos_from_json(json_path)

    assert result == {"https://github.com/example/tool"}


def test_fetch_github_release_data_falls_back_to_scraper_on_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    scraper_calls: list[tuple[str, str, str | None]] = []

    def fake_get(url: str, *args: object, **kwargs: object) -> FakeApiResponse:
        assert url.endswith("/releases/tags/v1.2.3")
        _ = args, kwargs
        return FakeApiResponse(status_code=404, payload={})

    def fake_scraper(username: str, repo_name: str, version: str | None) -> dict[str, object]:
        scraper_calls.append((username, repo_name, version))
        return {"tag_name": "v1.2.3"}

    monkeypatch.setattr(github_release_bulk.requests, "get", fake_get)
    monkeypatch.setattr(github_release_bulk, "scrape_github_release_page", fake_scraper)

    result = github_release_bulk.fetch_github_release_data("owner", "repo", "v1.2.3")

    assert result == {"tag_name": "v1.2.3"}
    assert scraper_calls == [("owner", "repo", "v1.2.3")]


def test_fetch_github_release_data_falls_back_to_scraper_on_rate_limit_message(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get(url: str, *args: object, **kwargs: object) -> FakeApiResponse:
        assert url.endswith("/releases/latest")
        _ = args, kwargs
        return FakeApiResponse(status_code=200, payload={"message": "API rate limit exceeded for 203.0.113.10."})

    def fake_scraper(username: str, repo_name: str, version: str | None) -> dict[str, object]:
        return {"tag_name": "v9.9.9", "repo": f"{username}/{repo_name}", "version": version or "latest"}

    monkeypatch.setattr(github_release_bulk.requests, "get", fake_get)
    monkeypatch.setattr(github_release_bulk, "scrape_github_release_page", fake_scraper)

    result = github_release_bulk.fetch_github_release_data("owner", "repo")

    assert result == {"tag_name": "v9.9.9", "repo": "owner/repo", "version": "latest"}


def test_extract_release_info_normalizes_missing_asset_fields() -> None:
    release_info = github_release_bulk.extract_release_info(
        {
            "tag_name": "v1.0.0",
            "name": "Release 1",
            "published_at": "2024-01-02T03:04:05Z",
            "assets": [{"name": "tool.tar.gz", "browser_download_url": "https://downloads.example/tool.tar.gz"}],
        }
    )

    assert release_info == {
        "tag_name": "v1.0.0",
        "name": "Release 1",
        "published_at": "2024-01-02T03:04:05Z",
        "assets": [
            {
                "name": "tool.tar.gz",
                "size": 0,
                "download_count": 0,
                "content_type": "",
                "created_at": "",
                "updated_at": "",
                "browser_download_url": "https://downloads.example/tool.tar.gz",
            }
        ],
        "assets_count": 1,
    }
