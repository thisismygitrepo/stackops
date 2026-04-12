from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from runpy import run_path
from typing import Protocol, cast

import pytest


REPO_ROOT = Path(__file__).resolve().parents[6]
SCRIPT_PATH = REPO_ROOT / ".github" / "skills" / "make-github-installer-config" / "scripts" / "skill_lib.py"


class RepoLike(Protocol):
    owner: str
    repo: str


class AssetLike(Protocol):
    name: str


class ReleaseLike(Protocol):
    tag_name: str
    assets: list[AssetLike]


class ResolvedLicenseLike(Protocol):
    value: str
    source: str
    warning: str | None


@dataclass(frozen=True, slots=True)
class FakeRepoSpec:
    owner: str
    repo: str


def _load_script_namespace() -> dict[str, object]:
    return run_path(str(SCRIPT_PATH))


def test_parse_repo_url_trims_trailing_slash() -> None:
    namespace = _load_script_namespace()
    parse_repo_url = cast(Callable[[str], object], namespace["parse_repo_url"])

    result = cast(RepoLike, parse_repo_url("https://github.com/acme/rocket/"))

    assert (result.owner, result.repo) == ("acme", "rocket")


def test_fetch_releases_skips_invalid_rows_and_assets(monkeypatch: pytest.MonkeyPatch) -> None:
    namespace = _load_script_namespace()
    fetch_releases = cast(Callable[[RepoLike, int], list[object]], namespace["fetch_releases"])

    def fake_http_get_json(url: str) -> object:
        assert url.endswith("/repos/acme/rocket/releases?per_page=2")
        return [
            {"tag_name": "v1.2.3", "assets": [{"name": "tool-linux-amd64.tar.gz"}, {"name": 123}, "bad-row"]},
            {"tag_name": 5, "assets": []},
            "bad-row",
        ]

    monkeypatch.setitem(fetch_releases.__globals__, "_http_get_json", fake_http_get_json)

    releases = cast(list[ReleaseLike], fetch_releases(FakeRepoSpec(owner="acme", repo="rocket"), 2))

    assert [release.tag_name for release in releases] == ["v1.2.3"]
    assert [asset.name for asset in releases[0].assets] == ["tool-linux-amd64.tar.gz"]


def test_fetch_releases_raises_when_no_valid_release_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    namespace = _load_script_namespace()
    fetch_releases = cast(Callable[[RepoLike, int], list[object]], namespace["fetch_releases"])

    def fake_http_get_json(_url: str) -> object:
        return [{"assets": []}]

    monkeypatch.setitem(fetch_releases.__globals__, "_http_get_json", fake_http_get_json)

    with pytest.raises(RuntimeError, match="No releases found"):
        fetch_releases(FakeRepoSpec(owner="acme", repo="rocket"), 1)


def test_fetch_repo_license_uses_spdx_when_name_is_other(monkeypatch: pytest.MonkeyPatch) -> None:
    namespace = _load_script_namespace()
    fetch_repo_license = cast(Callable[[RepoLike], object], namespace["fetch_repo_license"])

    def fake_http_get_json(url: str) -> object:
        assert url.endswith("/repos/acme/rocket")
        return {"license": {"name": "Other", "spdx_id": "MIT"}}

    monkeypatch.setitem(fetch_repo_license.__globals__, "_http_get_json", fake_http_get_json)

    result = cast(ResolvedLicenseLike, fetch_repo_license(FakeRepoSpec(owner="acme", repo="rocket")))

    assert (result.value, result.source, result.warning) == ("MIT", "github_api_spdx", None)


def test_fetch_repo_license_falls_back_when_metadata_is_not_usable(monkeypatch: pytest.MonkeyPatch) -> None:
    namespace = _load_script_namespace()
    fetch_repo_license = cast(Callable[[RepoLike], object], namespace["fetch_repo_license"])

    def fake_http_get_json(_url: str) -> object:
        return {"license": {"name": "Other", "spdx_id": "NOASSERTION"}}

    monkeypatch.setitem(fetch_repo_license.__globals__, "_http_get_json", fake_http_get_json)

    result = cast(ResolvedLicenseLike, fetch_repo_license(FakeRepoSpec(owner="acme", repo="rocket")))

    assert result.value == "No license asserted"
    assert result.source == "fallback"
    assert result.warning is not None


def test_asset_helpers_classify_and_match_patterns() -> None:
    namespace = _load_script_namespace()
    classify_os = cast(Callable[[str], str | None], namespace["classify_os"])
    classify_arch = cast(Callable[[str], str | None], namespace["classify_arch"])
    looks_like_binary_asset = cast(Callable[[str], bool], namespace["looks_like_binary_asset"])
    to_placeholder_pattern = cast(Callable[[str, str], str], namespace["to_placeholder_pattern"])
    file_exists_for_pattern = cast(Callable[[set[str], str, str], bool], namespace["file_exists_for_pattern"])

    assert classify_os("tool-macos-arm64.zip") == "darwin"
    assert classify_os("tool-windows-x64.msi") == "windows"
    assert classify_arch("tool-linux-aarch64.tar.gz") == "arm64"
    assert classify_arch("tool-windows-x64.zip") == "amd64"
    assert looks_like_binary_asset("tool-linux-amd64.tar.gz") is True
    assert looks_like_binary_asset("tool-linux-amd64.sha256.txt") is False

    pattern = to_placeholder_pattern("tool-v1.2.3-linux-amd64.tar.gz", "v1.2.3")

    assert pattern == "tool-{version}-linux-amd64.tar.gz"
    assert file_exists_for_pattern({"tool-1.2.3-linux-amd64.tar.gz"}, pattern, "v1.2.3") is True
