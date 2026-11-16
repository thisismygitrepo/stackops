from pathlib import Path
from typing import Literal

from git.repo import Repo
import pytest

from stackops.scripts.python.helpers.helpers_repos.guard_transport import run_guard_repository
from stackops.utils.cloud.rclone import RcloneCommandError
from stackops.utils.path_core import PathLike


REMOTE_PATH = Path("archives/repository.zip.gpg")


def _install_missing_remote_archive(monkeypatch: pytest.MonkeyPatch) -> list[Path]:
    uploads: list[Path] = []

    def download_repo_archive(repo_remote_root: Path, cloud: str, remote_path: Path, pwd: str | None) -> Path:
        raise RcloneCommandError(command=["rclone", "copyto"], returncode=3, stdout="", stderr="directory not found", hint=None)

    def upload_repo_archive(repo_root: Path, cloud: str, remote_path: Path, pwd: str | None, ignore_gitignore: bool) -> None:
        uploads.append(remote_path)

    def delete_path(target: PathLike, *, verbose: bool) -> None:
        return None

    monkeypatch.setattr("stackops.scripts.python.helpers.helpers_repos.cloud_repo_sync_archive.download_repo_archive", download_repo_archive)
    monkeypatch.setattr("stackops.scripts.python.helpers.helpers_repos.cloud_repo_sync_archive.upload_repo_archive", upload_repo_archive)
    monkeypatch.setattr("stackops.scripts.python.helpers.helpers_repos.cloud_repo_sync_git.commit_local_changes", lambda repo, message, console: None)
    monkeypatch.setattr(
        "stackops.scripts.python.helpers.helpers_repos.cloud_repo_sync_status.print_matching_repositories", lambda repo_root, console, title: None
    )
    monkeypatch.setattr("stackops.utils.path_core.delete_path", delete_path)
    return uploads


@pytest.mark.parametrize("operation", ["sync", "push"])
def test_missing_remote_archive_is_not_created_without_explicit_flag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, operation: Literal["sync", "push"]
) -> None:
    uploads = _install_missing_remote_archive(monkeypatch=monkeypatch)
    repo_root = tmp_path.joinpath("repository")
    Repo.init(repo_root).close()

    with pytest.raises(FileNotFoundError, match=r"No remote archive exists at fake-cloud:archives/repository\.zip\.gpg.*--create-remote"):
        run_guard_repository(
            repo_root=repo_root,
            cloud="fake-cloud",
            remote_path=REMOTE_PATH,
            operation=operation,
            pwd=None,
            message=None,
            on_conflict="stop-on-conflict",
            ignore_gitignore=False,
            create_remote=False,
        )

    assert uploads == []


def test_missing_remote_archive_is_created_with_explicit_flag(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    uploads = _install_missing_remote_archive(monkeypatch=monkeypatch)
    repo_root = tmp_path.joinpath("repository")
    Repo.init(repo_root).close()

    result = run_guard_repository(
        repo_root=repo_root,
        cloud="fake-cloud",
        remote_path=REMOTE_PATH,
        operation="sync",
        pwd=None,
        message=None,
        on_conflict="stop-on-conflict",
        ignore_gitignore=False,
        create_remote=True,
    )

    assert result == "created"
    assert uploads == [REMOTE_PATH]
