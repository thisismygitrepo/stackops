import os
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from stackops.scripts.python.helpers.helpers_repos.cloud_repo_sync_conflicts import ConflictResolutionAction


if TYPE_CHECKING:
    from stackops.utils.schemas.repos.repos_types import GuardRepoSync


type GuardOperation = Literal["sync", "pull", "push", "overwrite-local", "overwrite-remote"]


def run_guard_repository(
    repo_root: Path,
    cloud: str,
    remote_path: Path,
    operation: GuardOperation,
    pwd: str | None,
    message: str | None,
    on_conflict: ConflictResolutionAction,
    ignore_gitignore: bool,
) -> str:
    from git.exc import NoSuchPathError
    from git.repo import Repo
    from rich.console import Console

    from stackops.scripts.python.helpers.helpers_repos.cloud_repo_sync_actions import (
        overwrite_local_with_remote,
        publish_local_repository,
        restore_local_repository,
        validate_downloaded_repository,
        validate_integration_transport,
    )
    from stackops.scripts.python.helpers.helpers_repos.cloud_repo_sync_archive import download_repo_archive, upload_repo_archive
    from stackops.scripts.python.helpers.helpers_repos.cloud_repo_sync_git import commit_local_changes
    from stackops.scripts.python.helpers.helpers_repos.cloud_repo_sync_integration import integrate_remote_repository
    from stackops.utils.accessories import randstr
    from stackops.utils.cloud.rclone import RcloneCommandError, is_missing_remote_path_error
    from stackops.utils.path_core import delete_path
    from stackops.utils.source_of_truth import CONFIG_ROOT

    console = Console()
    repo_root = repo_root.expanduser().absolute()
    try:
        local_repo = Repo(repo_root, search_parent_directories=False)
    except NoSuchPathError:
        if os.path.lexists(repo_root):
            raise
        local_repo = None

    try:
        if local_repo is None and operation in {"push", "overwrite-remote"}:
            raise FileNotFoundError(f"No local repository exists at {repo_root}")
        if local_repo is not None:
            if os.name == "nt":
                local_repo.git.config("--local", "core.filemode", "false")
            if operation in {"sync", "overwrite-remote"}:
                commit_local_changes(repo=local_repo, message=message if message is not None and message.strip() else "sync", console=console)
            elif operation != "overwrite-local" and local_repo.is_dirty(untracked_files=True):
                raise RuntimeError("Commit or stash local changes before pulling or pushing a guard repository.")

        if operation == "overwrite-remote":
            upload_repo_archive(repo_root=repo_root, cloud=cloud, remote_path=remote_path, pwd=pwd, ignore_gitignore=ignore_gitignore)
            return "overwritten-remote"

        run_name = randstr(8)
        remote_root = Path(CONFIG_ROOT).joinpath("remote", run_name, repo_root.name)
        integration_root = Path(CONFIG_ROOT).joinpath("integration", run_name, repo_root.name)
        try:
            download_repo_archive(repo_remote_root=remote_root, cloud=cloud, remote_path=remote_path, pwd=pwd)
        except RcloneCommandError as error:
            if not is_missing_remote_path_error(error):
                raise
            delete_path(remote_root.parent, verbose=False)
            if local_repo is None or operation not in {"sync", "push"}:
                raise FileNotFoundError(f"No remote archive exists at {cloud}:{remote_path.as_posix()}") from error
            upload_repo_archive(repo_root=repo_root, cloud=cloud, remote_path=remote_path, pwd=pwd, ignore_gitignore=ignore_gitignore)
            return "created"

        validate_downloaded_repository(repo_remote_root=remote_root, cloud=cloud, remote_path=remote_path)
        if local_repo is None:
            validate_integration_transport(repo_local_root=repo_root, integration_root=remote_root, cloud=cloud)
            restore_local_repository(repo_local_root=repo_root, repo_remote_root=remote_root)
            return "restored"
        if operation == "overwrite-local":
            local_repo.close()
            overwrite_local_with_remote(repo_local_root=repo_root, repo_remote_root=remote_root)
            return "overwritten-local"
        if operation == "push":
            with Repo(remote_root) as remote_repo:
                remote_has_commit = remote_repo.head.is_valid()
            if remote_has_commit:
                local_repo.git.fetch("--no-recurse-submodules", str(remote_root), "HEAD")
                if not local_repo.head.is_valid() or not local_repo.is_ancestor(local_repo.commit("FETCH_HEAD"), local_repo.head.commit):
                    raise RuntimeError("Guard archive contains changes missing locally; pull or sync before pushing.")
        else:
            integrate_remote_repository(
                local_repo=local_repo,
                repo_remote_root=remote_root,
                integration_root=integration_root,
                cloud=cloud,
                on_conflict=on_conflict,
                console=console,
            )
        if operation == "pull":
            delete_path(remote_root.parent, verbose=False)
            return "pulled"

        publish_local_repository(
            repo_local_root=repo_root,
            repo_remote_root=remote_root,
            cloud=cloud,
            remote_path=remote_path,
            pwd=pwd,
            ignore_gitignore=ignore_gitignore,
        )
        return "pushed" if operation == "push" else "success"
    finally:
        if local_repo is not None:
            local_repo.close()


def fetch_guard_repository(repo_root: Path, sync: "GuardRepoSync", pwd: str | None) -> None:
    from git.repo import Repo

    from stackops.scripts.python.helpers.helpers_repos.cloud_repo_sync_actions import validate_downloaded_repository
    from stackops.scripts.python.helpers.helpers_repos.cloud_repo_sync_archive import download_repo_archive
    from stackops.utils.accessories import randstr
    from stackops.utils.path_core import delete_path
    from stackops.utils.source_of_truth import CONFIG_ROOT

    remote_root = Path(CONFIG_ROOT).joinpath("remote", randstr(8), repo_root.name)
    remote_path = Path(sync["remotePath"])
    download_repo_archive(repo_remote_root=remote_root, cloud=sync["cloud"], remote_path=remote_path, pwd=pwd)
    validate_downloaded_repository(repo_remote_root=remote_root, cloud=sync["cloud"], remote_path=remote_path)
    try:
        reference_specs: list[str] = ["+refs/heads/*:refs/remotes/guard/*", "+refs/tags/*:refs/guard/tags/*"]
        with Repo(remote_root) as remote_repo:
            if remote_repo.head.is_valid():
                reference_specs.append("HEAD")
            elif not remote_repo.references:
                return
        with Repo(repo_root) as local_repo:
            local_repo.git.fetch("--no-recurse-submodules", str(remote_root), *reference_specs)
    finally:
        delete_path(remote_root.parent, verbose=False)
