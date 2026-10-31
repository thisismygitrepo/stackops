from pathlib import Path

import pytest

from stackops.utils.repos.stackops_paths import current_workspace_stackops_paths


def test_workspace_paths_include_root_and_existing_member_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for member_name in ("repo_a", "repo_b", "repo_c"):
        tmp_path.joinpath(member_name, ".git").mkdir(parents=True)
    for member_name in ("repo_c", "repo_a"):
        member_yaml = tmp_path / member_name / ".stackops" / "agents" / "prompts.yaml"
        member_yaml.parent.mkdir(parents=True)
        member_yaml.write_text("entry: prompt\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    assert current_workspace_stackops_paths(path_kind="prompts_yaml") == (
        ("workspace", tmp_path / ".stackops" / "agents" / "prompts.yaml"),
        ("workspace:repo_a", tmp_path / "repo_a" / ".stackops" / "agents" / "prompts.yaml"),
        ("workspace:repo_c", tmp_path / "repo_c" / ".stackops" / "agents" / "prompts.yaml"),
    )


def test_workspace_paths_are_empty_outside_a_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    tmp_path.joinpath("only_repo", ".git").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)

    assert current_workspace_stackops_paths(path_kind="layout_yaml") == ()
