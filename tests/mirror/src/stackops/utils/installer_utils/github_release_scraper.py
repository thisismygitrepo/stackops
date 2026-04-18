from __future__ import annotations

from dataclasses import dataclass

import pytest

import stackops.utils.installer_utils.github_release_scraper as github_release_scraper


@dataclass(frozen=True, slots=True)
class FakeHtmlResponse:
    status_code: int
    text: str


def test_extract_helpers_parse_release_metadata_from_html() -> None:
    html = """
    <a href="/owner/repo/releases/tag/v1.2.3">release</a>
    <h1 class="d-inline">Release Name</h1>
    <relative-time datetime="2024-05-06T07:08:09Z"></relative-time>
    """

    assert github_release_scraper.extract_tag_from_html(html, "owner", "repo") == "v1.2.3"
    assert github_release_scraper.extract_release_name(html) == "Release Name"
    assert github_release_scraper.extract_published_at(html) == "2024-05-06T07:08:09Z"


def test_fetch_expanded_assets_deduplicates_download_urls(monkeypatch: pytest.MonkeyPatch) -> None:
    html = """
    <a href="/owner/repo/releases/download/v1/tool.tar.gz">
      <span class="Truncate-text text-bold">tool.tar.gz</span>
    </a>
    <a href="/owner/repo/releases/download/v1/tool.tar.gz">
      <span class="Truncate-text text-bold">tool.tar.gz</span>
    </a>
    """

    def fake_get(url: str, *args: object, **kwargs: object) -> FakeHtmlResponse:
        assert url.endswith("/expanded_assets/v1")
        _ = args, kwargs
        return FakeHtmlResponse(status_code=200, text=html)

    monkeypatch.setattr(github_release_scraper.requests, "get", fake_get)

    assets = github_release_scraper.fetch_expanded_assets("owner", "repo", "v1", {"User-Agent": "test"})

    assert assets == [
        {
            "name": "tool.tar.gz",
            "size": 0,
            "download_count": 0,
            "content_type": "",
            "created_at": "",
            "updated_at": "",
            "browser_download_url": "https://github.com/owner/repo/releases/download/v1/tool.tar.gz",
        }
    ]


def test_scrape_github_release_page_returns_release_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    requested_urls: list[str] = []

    def fake_get(url: str, *args: object, **kwargs: object) -> FakeHtmlResponse:
        requested_urls.append(url)
        _ = args, kwargs
        return FakeHtmlResponse(
            status_code=200,
            text="""
            <a href="/owner/repo/releases/tag/v2.0.0">release</a>
            <h1 class="d-inline">Stable</h1>
            <relative-time datetime="2024-06-01T00:00:00Z"></relative-time>
            """,
        )

    def fake_fetch_assets(username: str, repo_name: str, tag_name: str, headers: dict[str, str]) -> list[dict[str, object]]:
        assert username == "owner"
        assert repo_name == "repo"
        assert tag_name == "v2.0.0"
        assert "User-Agent" in headers
        return [{"name": "tool.tar.gz", "browser_download_url": "https://downloads.example/tool.tar.gz"}]

    monkeypatch.setattr(github_release_scraper.requests, "get", fake_get)
    monkeypatch.setattr(github_release_scraper, "fetch_expanded_assets", fake_fetch_assets)

    result = github_release_scraper.scrape_github_release_page("owner", "repo", "v2.0.0")

    assert requested_urls == ["https://github.com/owner/repo/releases/tag/v2.0.0"]
    assert result == {
        "tag_name": "v2.0.0",
        "name": "Stable",
        "published_at": "2024-06-01T00:00:00Z",
        "assets": [{"name": "tool.tar.gz", "browser_download_url": "https://downloads.example/tool.tar.gz"}],
    }
