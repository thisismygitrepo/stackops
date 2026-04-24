from pathlib import Path

import pytest

from stackops.scripts.python.helpers.helpers_agents import agents_run_context
from stackops.utils import repo_stackops


def test_resolve_prompts_yaml_paths_uses_repo_stackops_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def fake_get_repo_root(_path: Path) -> Path:
        return tmp_path

    monkeypatch.setattr(repo_stackops, "get_repo_root", fake_get_repo_root)

    assert agents_run_context.resolve_prompts_yaml_paths(prompts_yaml_path=None, where="repo") == [
        ("repo", tmp_path / ".stackops" / "prompts.yaml")
    ]


def test_resolve_prompts_yaml_paths_prioritizes_repo_for_all(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def fake_get_repo_root(_path: Path) -> Path:
        return tmp_path

    monkeypatch.setattr(repo_stackops, "get_repo_root", fake_get_repo_root)

    locations = agents_run_context.resolve_prompts_yaml_paths(prompts_yaml_path=None, where="all")

    assert locations[0] == ("repo", tmp_path / ".stackops" / "prompts.yaml")


def test_resolve_prompts_yaml_paths_rejects_repo_outside_git_repo(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get_repo_root(_path: Path) -> Path | None:
        return None

    monkeypatch.setattr(repo_stackops, "get_repo_root", fake_get_repo_root)

    with pytest.raises(ValueError, match="--where repo requires running inside a git repository"):
        agents_run_context.resolve_prompts_yaml_paths(prompts_yaml_path=None, where="repo")
