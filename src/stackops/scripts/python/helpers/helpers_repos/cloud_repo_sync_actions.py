import os
from pathlib import Path
import shutil
from typing import TYPE_CHECKING, Literal

from stackops.scripts.python.helpers.helpers_repos.cloud_repo_sync_conflicts import ConflictResolutionAction
from stackops.scripts.python.helpers.helpers_repos.cloud_repo_sync_integration import IntegrationWorktree


if TYPE_CHECKING:
    from git.repo import Repo


type SelectedConflictAction = ConflictResolutionAction | Literal["inspect", "overwrite-local", "overwrite-remote"]


def select_conflict_action(on_conflict: ConflictResolutionAction) -> SelectedConflictAction:
    if on_conflict != "ask":
        return on_conflict
    import questionary

    choices: dict[str, SelectedConflictAction] = {
        "Inspect local repository and isolated merge worktree": "inspect",
        "Finish merge and accept remote versions for conflicting paths": "merge-accept-remote",
        "Finish merge and accept local versions for conflicting paths": "merge-accept-local",
        "Overwrite local repository with remote copy (no merge)": "overwrite-local",
        "Overwrite remote repository with local copy (no merge)": "overwrite-remote",
        "Stop on conflict": "stop-on-conflict",
    }
    choice = questionary.select("Choose one option:", choices=tuple(choices)).ask()
    if choice is None:
        import typer

        raise typer.Exit(code=1)
    return choices[choice]


def remove_integration_state(local_repo: "Repo", integration_repo: "Repo", integration_worktree: IntegrationWorktree) -> None:
    from stackops.scripts.python.helpers.helpers_repos.cloud_repo_sync_integration import remove_integration_worktree

    integration_repo.close()
    remove_integration_worktree(local_repo=local_repo, integration_worktree=integration_worktree)


def validate_integration_transport(repo_local_root: Path, integration_root: Path, cloud: str) -> None:
    from stackops.utils.cloud.rclone import RcloneConfigError, list_remote_names_from_config
    from stackops.utils.source_of_truth import DOTFILES_RCLONE_CONF_PATH, DOTFILES_ROOT

    if repo_local_root.absolute() != DOTFILES_ROOT.absolute():
        return
    relative_config_path = DOTFILES_RCLONE_CONF_PATH.relative_to(DOTFILES_ROOT)
    candidate_config_path = integration_root.joinpath(relative_config_path)
    remote_names = list_remote_names_from_config(config_path=candidate_config_path)
    if cloud not in remote_names:
        raise RcloneConfigError(f"Resolved rclone config does not contain required remote '{cloud}'. Integration remains at {integration_root}.")


def publish_local_repository(
    repo_local_root: Path, repo_remote_root: Path, cloud: str, remote_path: Path, pwd: str | None, ignore_gitignore: bool
) -> None:
    from stackops.scripts.python.helpers.helpers_repos.cloud_repo_sync_archive import upload_repo_archive
    from stackops.utils.path_core import delete_path

    upload_repo_archive(repo_root=repo_local_root, cloud=cloud, remote_path=remote_path, pwd=pwd, ignore_gitignore=ignore_gitignore)
    delete_path(repo_remote_root.parent, verbose=True)


def validate_downloaded_repository(repo_remote_root: Path, cloud: str, remote_path: Path) -> None:
    from git.repo import Repo

    from stackops.scripts.python.helpers.helpers_repos.cloud_repo_sync_git import prepare_downloaded_repository

    with Repo(repo_remote_root) as repo:
        prepare_downloaded_repository(repo=repo)
        if repo.is_dirty(untracked_files=True):
            raise RuntimeError(
                f"Downloaded repository is dirty and was preserved at {repo_remote_root}. "
                f"Remote location: {cloud}:{remote_path.as_posix()}"
            )


def restore_local_repository(repo_local_root: Path, repo_remote_root: Path) -> None:
    if os.path.lexists(repo_local_root):
        raise FileExistsError(f"Refusing to restore over an existing path: {repo_local_root}")
    if not repo_remote_root.is_dir():
        raise FileNotFoundError(f"Downloaded repository was not found at: {repo_remote_root}")

    temporary_parent = repo_remote_root.parent
    repo_local_root.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(repo_remote_root), str(repo_local_root))
    if temporary_parent.exists() and not any(temporary_parent.iterdir()):
        temporary_parent.rmdir()

