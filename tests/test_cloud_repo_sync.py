from io import StringIO
from pathlib import Path

from git.repo import Repo
from rich.console import Console

from machineconfig.scripts.python.helpers.helpers_repos import cloud_repo_sync
from machineconfig.utils.path_extended import PathExtended


def _make_console() -> Console:
    return Console(file=StringIO(), force_terminal=False, color_system=None)


def _worktree_path(repo: Repo) -> Path:
    working_tree_dir = repo.working_tree_dir
    if working_tree_dir is None:
        raise AssertionError("Expected repository to have a working tree.")
    return Path(working_tree_dir)


def _configure_git_identity(repo: Repo) -> None:
    with repo.config_writer() as config_writer:
        config_writer.set_value("user", "name", "Machineconfig Test")
        config_writer.set_value("user", "email", "machineconfig@example.com")


def _commit_all(repo: Repo, message: str) -> None:
    repo.git.add(A=True)
    repo.index.commit(message)


def _create_repo_triplet(tmp_path: Path) -> tuple[Repo, Repo]:
    source_path = tmp_path / "source"
    source_repo = Repo.init(source_path)
    _configure_git_identity(repo=source_repo)

    tracked_file = source_path / "tracked.txt"
    tracked_file.write_text("base\n", encoding="utf-8")
    _commit_all(repo=source_repo, message="initial")
    source_repo.git.branch("-M", cloud_repo_sync.REMOTE_BRANCH_NAME)

    local_repo = Repo.clone_from(source_path.as_posix(), (tmp_path / "local").as_posix())
    remote_repo = Repo.clone_from(source_path.as_posix(), (tmp_path / "remote").as_posix())
    _configure_git_identity(repo=local_repo)
    _configure_git_identity(repo=remote_repo)
    return local_repo, remote_repo


def test_merge_remote_copy_reports_success_for_clean_merge(tmp_path: Path) -> None:
    local_repo, remote_repo = _create_repo_triplet(tmp_path=tmp_path)

    local_path = _worktree_path(repo=local_repo)
    remote_path = _worktree_path(repo=remote_repo)

    (local_path / "local.txt").write_text("local change\n", encoding="utf-8")
    _commit_all(repo=local_repo, message="local change")

    (remote_path / "remote.txt").write_text("remote change\n", encoding="utf-8")
    _commit_all(repo=remote_repo, message="remote change")

    result = cloud_repo_sync._merge_remote_copy(  # pyright: ignore[reportPrivateUsage]
        repo=local_repo,
        remote_path=PathExtended(remote_path),
        console=_make_console(),
    )

    assert result.status == "success"
    assert result.conflict_paths == ()
    assert (local_path / "remote.txt").read_text(encoding="utf-8") == "remote change\n"


def test_merge_remote_copy_reports_conflicts_from_git_state(tmp_path: Path) -> None:
    local_repo, remote_repo = _create_repo_triplet(tmp_path=tmp_path)

    local_path = _worktree_path(repo=local_repo)
    remote_path = _worktree_path(repo=remote_repo)

    (local_path / "tracked.txt").write_text("local version\n", encoding="utf-8")
    _commit_all(repo=local_repo, message="local change")

    (remote_path / "tracked.txt").write_text("remote version\n", encoding="utf-8")
    _commit_all(repo=remote_repo, message="remote change")

    result = cloud_repo_sync._merge_remote_copy(  # pyright: ignore[reportPrivateUsage]
        repo=local_repo,
        remote_path=PathExtended(remote_path),
        console=_make_console(),
    )

    assert result.status == "merge_conflict"
    assert result.conflict_paths == ("tracked.txt",)
