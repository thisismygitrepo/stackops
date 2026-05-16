from pathlib import Path

import pytest

from stackops.scripts.python.helpers.helpers_repos import cloud_repo_sync_conflicts


def test_resolve_conflict_action_accept_merge_modes() -> None:
    assert cloud_repo_sync_conflicts.resolve_conflict_action("merge-accept-remote") == "merge-accept-remote"
    assert cloud_repo_sync_conflicts.resolve_conflict_action("merge-accept-local") == "merge-accept-local"


def test_build_merge_accept_remote_program_uses_theirs_for_only_conflicted_files() -> None:
    program = cloud_repo_sync_conflicts.build_merge_accept_program(
        repo_local_root=Path("/tmp/repo with spaces"),
        conflict_paths=("alpha.txt", "nested dir/beta file.py"),
        accept_side="remote",
        push_local_program="uv run push-local.py",
        platform_name="Linux",
    )

    assert "cd '/tmp/repo with spaces'" in program
    assert "git checkout --theirs -- alpha.txt 'nested dir/beta file.py'" in program
    assert "git add -- alpha.txt 'nested dir/beta file.py'" in program
    assert "git commit --no-edit" in program
    assert "uv run push-local.py" in program


def test_build_merge_accept_local_program_uses_ours_for_only_conflicted_files_on_windows() -> None:
    program = cloud_repo_sync_conflicts.build_merge_accept_program(
        repo_local_root=Path(r"C:\Repos\demo repo"),
        conflict_paths=("alpha.txt", "nested dir/beta file.py"),
        accept_side="local",
        push_local_program="uv run push-local.py",
        platform_name="Windows",
    )

    assert r"Set-Location -LiteralPath 'C:\Repos\demo repo'" in program
    assert "git checkout --ours -- 'alpha.txt' 'nested dir/beta file.py'" in program
    assert "git add -- 'alpha.txt' 'nested dir/beta file.py'" in program
    assert "git commit --no-edit" in program
    assert "uv run push-local.py" in program


def test_build_conflict_path_arguments_rejects_empty_conflict_list() -> None:
    with pytest.raises(ValueError, match="conflicted paths"):
        cloud_repo_sync_conflicts._build_conflict_path_arguments((), "bash")
