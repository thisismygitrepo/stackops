

from collections.abc import Callable
from dataclasses import dataclass
import json
from pathlib import Path
from runpy import run_path
import sys
from typing import Literal, cast

import pytest


REPO_ROOT = Path(__file__).resolve().parents[6]
SCRIPT_ROOT = REPO_ROOT / ".github" / "skills" / "make-github-installer-config" / "scripts"
SCRIPT_PATH = SCRIPT_ROOT / "build_installer_config.py"

type PlatformName = Literal["linux", "darwin", "windows"]


@dataclass(frozen=True, slots=True)
class FakeRepoSpec:
    owner: str
    repo: str


@dataclass(frozen=True, slots=True)
class FakeReleaseAsset:
    name: str


@dataclass(frozen=True, slots=True)
class FakeReleaseInfo:
    tag_name: str
    assets: list[FakeReleaseAsset]


@dataclass(frozen=True, slots=True)
class FakeResolvedLicense:
    value: str
    source: str
    warning: str | None


def _load_script_namespace() -> dict[str, object]:
    inserted = False
    script_root_text = str(SCRIPT_ROOT)
    if script_root_text not in sys.path:
        sys.path.insert(0, script_root_text)
        inserted = True
    try:
        return run_path(str(SCRIPT_PATH))
    finally:
        if inserted:
            sys.path.remove(script_root_text)


def _sample_releases() -> list[FakeReleaseInfo]:
    return [
        FakeReleaseInfo(
            tag_name="v2.0.0",
            assets=[FakeReleaseAsset(name="tool-v2.0.0-linux-amd64-musl.tar.gz"), FakeReleaseAsset(name="tool-v2.0.0-darwin-arm64.zip")],
        ),
        FakeReleaseInfo(
            tag_name="v1.9.0",
            assets=[
                FakeReleaseAsset(name="tool-v1.9.0-linux-amd64-musl.tar.gz"),
                FakeReleaseAsset(name="tool-v1.9.0-linux-arm64.tar.gz"),
                FakeReleaseAsset(name="tool-v1.9.0-windows-x64.zip"),
            ],
        ),
    ]


def test_infer_best_pattern_prefers_musl_on_linux() -> None:
    namespace = _load_script_namespace()
    infer_best_pattern = cast(Callable[[list[str], PlatformName], str | None], namespace["infer_best_pattern"])

    result = infer_best_pattern(
        ["tool-{version}-linux-amd64.tar.gz", "tool-{version}-linux-amd64-musl.tar.gz", "tool-{version}-linux-amd64.tar.gz"], "linux"
    )

    assert result == "tool-{version}-linux-amd64-musl.tar.gz"
    assert infer_best_pattern([], "windows") is None


def test_resolve_license_trims_override_and_rejects_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    namespace = _load_script_namespace()
    resolve_license = cast(Callable[[FakeRepoSpec, str | None], object], namespace["resolve_license"])

    def fail_fetch_repo_license(_spec: FakeRepoSpec) -> FakeResolvedLicense:
        raise AssertionError("override should bypass GitHub lookup")

    monkeypatch.setitem(resolve_license.__globals__, "fetch_repo_license", fail_fetch_repo_license)

    result = cast(FakeResolvedLicense, resolve_license(FakeRepoSpec(owner="acme", repo="rocket"), " MIT "))

    assert (result.value, result.source, result.warning) == ("MIT", "user", None)

    with pytest.raises(ValueError, match="cannot be empty"):
        resolve_license(FakeRepoSpec(owner="acme", repo="rocket"), "   ")


def test_main_writes_output_payload_and_collects_missing_latest_checks(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    namespace = _load_script_namespace()
    main = cast(Callable[[], None], namespace["main"])
    output_path = tmp_path / "generated.json"

    def fake_parse_repo_url(repo_url: str) -> FakeRepoSpec:
        assert repo_url == "https://github.com/acme/tool"
        return FakeRepoSpec(owner="acme", repo="tool")

    def fake_fetch_repo_license(spec: FakeRepoSpec) -> FakeResolvedLicense:
        return FakeResolvedLicense(value="MIT", source="github_api_spdx", warning=None)

    def fake_fetch_releases(spec: FakeRepoSpec, limit: int) -> list[FakeReleaseInfo]:
        assert (spec.owner, spec.repo, limit) == ("acme", "tool", 8)
        return _sample_releases()

    monkeypatch.setitem(main.__globals__, "parse_repo_url", fake_parse_repo_url)
    monkeypatch.setitem(main.__globals__, "fetch_repo_license", fake_fetch_repo_license)
    monkeypatch.setitem(main.__globals__, "fetch_releases", fake_fetch_releases)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "build_installer_config.py",
            "--repo-url",
            "https://github.com/acme/tool",
            "--app-name",
            "Tool",
            "--doc",
            "CLI helper",
            "--output",
            str(output_path),
        ],
    )

    main()

    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload["entry"]["appName"] == "tool"
    assert payload["entry"]["license"] == "MIT"
    assert payload["checks"]["latestTag"] == "v2.0.0"
    assert payload["checks"]["latestAssetCount"] == 2
    assert any("arm64/linux" in row for row in payload["checks"]["latestPatternChecks"])
    assert any("amd64/windows" in row for row in payload["checks"]["latestPatternChecks"])


def test_main_raises_in_strict_mode_when_latest_assets_do_not_match(monkeypatch: pytest.MonkeyPatch) -> None:
    namespace = _load_script_namespace()
    main = cast(Callable[[], None], namespace["main"])

    def fake_parse_repo_url(repo_url: str) -> FakeRepoSpec:
        return FakeRepoSpec(owner="acme", repo="tool")

    def fake_fetch_repo_license(spec: FakeRepoSpec) -> FakeResolvedLicense:
        return FakeResolvedLicense(value="MIT", source="github_api_spdx", warning=None)

    def fake_fetch_releases(spec: FakeRepoSpec, limit: int) -> list[FakeReleaseInfo]:
        return _sample_releases()

    monkeypatch.setitem(main.__globals__, "parse_repo_url", fake_parse_repo_url)
    monkeypatch.setitem(main.__globals__, "fetch_repo_license", fake_fetch_repo_license)
    monkeypatch.setitem(main.__globals__, "fetch_releases", fake_fetch_releases)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "build_installer_config.py",
            "--repo-url",
            "https://github.com/acme/tool",
            "--app-name",
            "Tool",
            "--doc",
            "CLI helper",
            "--strict-latest-check",
        ],
    )

    with pytest.raises(RuntimeError, match="Missing latest asset"):
        main()
