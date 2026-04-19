

from collections.abc import Callable
from dataclasses import dataclass
import json
from pathlib import Path
from runpy import run_path
import sys
from typing import cast

import pytest


REPO_ROOT = Path(__file__).resolve().parents[6]
SCRIPT_ROOT = REPO_ROOT / ".github" / "skills" / "make-github-installer-config" / "scripts"
SCRIPT_PATH = SCRIPT_ROOT / "scan_github_releases.py"


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
            tag_name="v2.0.0", assets=[FakeReleaseAsset(name="tool-v2.0.0-linux-amd64.tar.gz"), FakeReleaseAsset(name="tool-v2.0.0-checksums.txt")]
        )
    ]


def test_main_writes_classified_rows_to_stdout(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    namespace = _load_script_namespace()
    main = cast(Callable[[], None], namespace["main"])

    def fake_parse_repo_url(repo_url: str) -> FakeRepoSpec:
        assert repo_url == "https://github.com/acme/tool"
        return FakeRepoSpec(owner="acme", repo="tool")

    def fake_fetch_releases(spec: FakeRepoSpec, limit: int) -> list[FakeReleaseInfo]:
        assert (spec.owner, spec.repo, limit) == ("acme", "tool", 8)
        return _sample_releases()

    monkeypatch.setitem(main.__globals__, "parse_repo_url", fake_parse_repo_url)
    monkeypatch.setitem(main.__globals__, "fetch_releases", fake_fetch_releases)
    monkeypatch.setattr(sys, "argv", ["scan_github_releases.py", "--repo-url", "https://github.com/acme/tool"])

    main()

    payload = json.loads(capsys.readouterr().out)

    assert payload["repo"] == {"owner": "acme", "name": "tool"}
    assert payload["releaseCount"] == 1
    assert payload["rows"][0]["binaryLike"] is True
    assert payload["rows"][0]["os"] == "linux"
    assert payload["rows"][0]["arch"] == "amd64"
    assert payload["rows"][1]["binaryLike"] is False


def test_main_writes_output_file_when_requested(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    namespace = _load_script_namespace()
    main = cast(Callable[[], None], namespace["main"])
    output_path = tmp_path / "scan.json"

    def fake_parse_repo_url(repo_url: str) -> FakeRepoSpec:
        return FakeRepoSpec(owner="acme", repo="tool")

    def fake_fetch_releases(spec: FakeRepoSpec, limit: int) -> list[FakeReleaseInfo]:
        return _sample_releases()

    monkeypatch.setitem(main.__globals__, "parse_repo_url", fake_parse_repo_url)
    monkeypatch.setitem(main.__globals__, "fetch_releases", fake_fetch_releases)
    monkeypatch.setattr(sys, "argv", ["scan_github_releases.py", "--repo-url", "https://github.com/acme/tool", "--output", str(output_path)])

    main()

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["rows"][0]["asset"] == "tool-v2.0.0-linux-amd64.tar.gz"
