from pathlib import Path

import pytest

from stackops.scripts.python.helpers.helpers_agents import mcp_catalog
from stackops.utils import repo_stackops


def test_resolve_mcp_catalog_locations_uses_repo_stackops_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def fake_get_repo_root(_path: Path) -> Path:
        return tmp_path

    monkeypatch.setattr(repo_stackops, "get_repo_root", fake_get_repo_root)

    assert mcp_catalog.resolve_mcp_catalog_locations(where="repo") == ({"scope": "repo", "path": tmp_path / ".stackops" / "mcp.json"},)


def test_resolve_mcp_catalog_locations_prioritizes_repo_for_all(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def fake_get_repo_root(_path: Path) -> Path:
        return tmp_path

    monkeypatch.setattr(repo_stackops, "get_repo_root", fake_get_repo_root)

    locations = mcp_catalog.resolve_mcp_catalog_locations(where="all")

    assert locations[0] == {"scope": "repo", "path": tmp_path / ".stackops" / "mcp.json"}


def test_resolve_mcp_catalog_locations_rejects_repo_outside_git_repo(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get_repo_root(_path: Path) -> Path | None:
        return None

    monkeypatch.setattr(repo_stackops, "get_repo_root", fake_get_repo_root)

    with pytest.raises(ValueError, match="--where repo requires running inside a git repository"):
        mcp_catalog.resolve_mcp_catalog_locations(where="repo")
