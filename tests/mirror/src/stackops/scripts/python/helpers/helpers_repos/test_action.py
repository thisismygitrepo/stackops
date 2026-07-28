from pathlib import Path

from git.repo import Repo

from stackops.scripts.python.helpers.helpers_repos.action import git_action
from stackops.scripts.python.helpers.helpers_repos.action_helper import GitAction


def test_status_reports_clean_and_changed_working_trees(tmp_path: Path) -> None:
    repository_path = tmp_path / "repository"
    Repo.init(repository_path)

    clean_result = git_action(path=repository_path, action=GitAction.status, message=None, auto_uv_sync=False)

    assert clean_result.success
    assert not clean_result.had_changes
    assert clean_result.message.startswith("##")

    (repository_path / "untracked.txt").write_text("changed\n")
    changed_result = git_action(path=repository_path, action=GitAction.status, message=None, auto_uv_sync=False)

    assert changed_result.success
    assert changed_result.had_changes
    assert "?? untracked.txt" in changed_result.message
