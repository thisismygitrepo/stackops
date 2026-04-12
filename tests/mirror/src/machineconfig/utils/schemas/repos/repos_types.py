from __future__ import annotations

from machineconfig.utils.schemas.repos import repos_types as repos_types_module


def test_repo_remote_and_git_version_info_require_expected_keys() -> None:
    assert repos_types_module.RepoRemote.__required_keys__ == frozenset({"name", "url"})
    assert repos_types_module.GitVersionInfo.__required_keys__ == frozenset({"branch", "commit"})


def test_repo_record_shapes_expose_runtime_required_keys() -> None:
    assert repos_types_module.RepoRecordDict.__required_keys__ == frozenset(
        {
            "name",
            "parentDir",
            "currentBranch",
            "remotes",
            "version",
            "isDirty",
        }
    )
    assert repos_types_module.RepoRecordFile.__required_keys__ == frozenset(
        {"version", "repos"}
    )
