from pathlib import Path

import pytest

from stackops.utils import repo_stackops


def test_current_repo_stackops_path_resolves_known_paths(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def fake_get_repo_root(_path: Path) -> Path:
        return tmp_path

    monkeypatch.setattr(repo_stackops, "get_repo_root", fake_get_repo_root)

    assert repo_stackops.current_repo_stackops_path(path_kind="prompts_yaml") == tmp_path / ".stackops" / "prompts.yaml"
    assert repo_stackops.current_repo_stackops_path(path_kind="mcp_json") == tmp_path / ".stackops" / "mcp.json"
    assert repo_stackops.current_repo_stackops_path(path_kind="scripts") == tmp_path / ".stackops" / "scripts"


def test_require_current_repo_stackops_path_rejects_non_repo(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get_repo_root(_path: Path) -> Path | None:
        return None

    monkeypatch.setattr(repo_stackops, "get_repo_root", fake_get_repo_root)

    with pytest.raises(ValueError, match="--where repo requires running inside a git repository"):
        repo_stackops.require_current_repo_stackops_path(path_kind="prompts_yaml")
