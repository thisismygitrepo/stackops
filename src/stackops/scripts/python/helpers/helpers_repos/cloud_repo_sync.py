import os
from pathlib import Path
from typing import Annotated, Literal, Never

import typer

from stackops.scripts.python.helpers.helpers_repos.cloud_repo_sync_conflicts import ConflictResolutionOption
from stackops.utils.io import GpgCommandError


def _exit_after_gpg_error(error: GpgCommandError) -> Never:
    from rich.console import Console
    from rich.panel import Panel

    operation = "encrypt" if "--encrypt" in error.command else "decrypt"
    details = error.hint if error.hint is not None else str(error)
    Console().print(Panel(f"❌ Could not {operation} the repository archive.\n\n{details}", title="GPG Error", border_style="red"))
    raise typer.Exit(code=1) from None


def main(
    repo: Annotated[str, typer.Argument(help="Path to the local repository. Defaults to current working directory.")] = ".",
    cloud: Annotated[
        str | None, typer.Option(..., "--cloud", "-C", help="Cloud storage profile name. If not provided, uses default from config.")
    ] = None,
    message: Annotated[str | None, typer.Option(..., "--message", "-m", help="Commit message for local changes.")] = None,
    mode: Annotated[
        Literal["merge", "m", "overwrite-local", "l", "overwrite-remote", "r"],
        typer.Option(
            "--mode",
            "-M",
            help="merge (m): merge both copies; overwrite-local (l): replace local with remote; "
            "overwrite-remote (r): replace remote with local. Overwrite modes never merge.",
        ),
    ] = "merge",
    on_conflict: Annotated[
        ConflictResolutionOption,
        typer.Option(
            ...,
            "--on-conflict",
            "-c",
            help="Merge conflicts only: ask (a), stop-on-conflict (s), merge-accept-remote (r), or merge-accept-local (l).",
        ),
    ] = "ask",
    pwd: Annotated[str | None, typer.Option(..., "--password", "-p", help="Password for encryption/decryption of the remote repository.")] = None,
    ignore_gitignore: Annotated[
        bool,
        typer.Option("--ignore-gitignore", help="Include files excluded by Git ignore rules in the repository archive."),
    ] = False,
) -> str | None:
    from git.exc import GitCommandError, InvalidGitRepositoryError, NoSuchPathError
    from git.repo import Repo
    from rich.console import Console
    from rich.panel import Panel

    from stackops.scripts.python.helpers.helpers_repos.cloud_repo_sync_actions import (
        overwrite_local_with_remote,
        publish_local_repository,
        restore_local_repository,
        validate_integration_transport,
    )
    from stackops.scripts.python.helpers.helpers_repos.cloud_repo_sync_archive import (
        download_repo_archive,
        get_repo_remote_archive_path,
        upload_repo_archive,
    )
    from stackops.scripts.python.helpers.helpers_repos.cloud_repo_sync_conflicts import resolve_conflict_action
    from stackops.scripts.python.helpers.helpers_repos.cloud_repo_sync_git import commit_local_changes, restore_downloaded_file_modes
    from stackops.scripts.python.helpers.helpers_repos.cloud_repo_sync_integration import integrate_remote_repository
    from stackops.utils.accessories import randstr
    from stackops.utils.cloud.default_remote import DefaultRcloneRemoteConfigError, read_default_rclone_remote
    from stackops.utils.cloud.rclone import RcloneCommandError, is_missing_remote_path_error
    from stackops.utils.path_core import delete_path
    from stackops.utils.source_of_truth import CONFIG_ROOT, DOTFILES_STACKOPS_CONFIG_PATH

    match mode:
        case "m" | "merge":
            mode = "merge"
        case "l" | "overwrite-local":
            mode = "overwrite-local"
        case "r" | "overwrite-remote":
            mode = "overwrite-remote"

    console = Console()
    if cloud is None:
        try:
            cloud_resolved = read_default_rclone_remote()
        except DefaultRcloneRemoteConfigError as exc:
            console.print(Panel(f"❌ {exc}\n\nUse: devops repos guard REPO --cloud REMOTE", title="Cloud Configuration Required", border_style="red"))
            raise typer.Exit(code=1) from exc
        console.print(
            Panel(f"⚠️  Using default cloud `{cloud_resolved}` from {DOTFILES_STACKOPS_CONFIG_PATH}", title="Default Cloud", border_style="yellow")
        )
    else:
        cloud_resolved = cloud

    requested_repo_root = Path(os.path.abspath(Path.cwd() if repo == "." else Path(repo).expanduser()))
    try:
        repo_local_obj = Repo(requested_repo_root, search_parent_directories=requested_repo_root == Path.cwd())
    except InvalidGitRepositoryError as exc:
        typer.echo(typer.style("Error: ", fg=typer.colors.RED) + f"'{requested_repo_root}' is not a git repository.")
        raise typer.Exit(code=1) from exc
    except NoSuchPathError as exc:
        if os.path.lexists(requested_repo_root):
            typer.echo(typer.style("Error: ", fg=typer.colors.RED) + f"'{requested_repo_root}' is not a git repository.")
            raise typer.Exit(code=1) from exc
        repo_local_obj = None
        repo_local_root = requested_repo_root
    else:
        repo_local_root = Path(repo_local_obj.working_dir)
    try:
        repo_local_root.resolve().relative_to(Path.home().resolve())
    except ValueError as exc:
        console.print(Panel(f"Repository must live under {Path.home()}\nLocation: {repo_local_root}", title="Error", border_style="red"))
        raise typer.Exit(code=1) from exc

    if repo_local_obj is not None and os.name == "nt":
        repo_local_obj.git.config("--local", "core.filemode", "false")

    message_resolved = "sync" if message is None or message.strip() == "" else message
    run_name = randstr(8)
    repo_remote_root = Path(CONFIG_ROOT).joinpath("remote", run_name, repo_local_root.name)
    integration_root = Path(CONFIG_ROOT).joinpath("integration", run_name, repo_local_root.name)
    remote_path = get_repo_remote_archive_path(repo_root=repo_local_root)
    if mode == "overwrite-remote":
        if repo_local_obj is None:
            console.print(Panel(f"No local repository exists at {repo_local_root}", title="Repository Not Found", border_style="red"))
            raise typer.Exit(code=1)
        try:
            commit_local_changes(repo=repo_local_obj, message=message_resolved, console=console)
        except GitCommandError as exc:
            console.print(Panel(f"❌ COMMIT FAILED\n{exc}", title="Commit Failed", border_style="red"))
            raise typer.Exit(code=1) from exc
        try:
            upload_repo_archive(
                repo_root=repo_local_root, cloud=cloud_resolved, remote_path=remote_path, pwd=pwd, ignore_gitignore=ignore_gitignore
            )
        except GpgCommandError as error:
            _exit_after_gpg_error(error=error)
        console.print(Panel("✅ Cloud repository replaced with the local repository.", title="Overwrite Remote", border_style="green"))
        return "overwritten-remote"

    if repo_local_obj is None:
        console.print(
            Panel(
                f"Local repository does not exist at {repo_local_root}\nLooking for {cloud_resolved}:{remote_path.as_posix()}",
                title="First Sync",
                border_style="blue",
            )
        )
    try:
        console.print(Panel("📥 DOWNLOADING REMOTE REPOSITORY", title_align="left", border_style="blue"))
        download_repo_archive(repo_remote_root=repo_remote_root, cloud=cloud_resolved, remote_path=remote_path, pwd=pwd)
    except GpgCommandError as error:
        _exit_after_gpg_error(error=error)
    except RcloneCommandError as error:
        if not is_missing_remote_path_error(error):
            raise
        delete_path(repo_remote_root.parent, verbose=False)
        if repo_local_obj is None or mode == "overwrite-local":
            missing_source = f"No remote archive exists at {cloud_resolved}:{remote_path.as_posix()}"
            if repo_local_obj is None:
                missing_source = f"No local repository exists at {repo_local_root}\n{missing_source}"
            console.print(
                Panel(
                    missing_source,
                    title="Repository Not Found",
                    border_style="red",
                )
            )
            raise typer.Exit(code=1) from error
        console.print(Panel("🆕 Remote repository does not exist; creating it from local.", border_style="green"))
        try:
            commit_local_changes(repo=repo_local_obj, message=message_resolved, console=console)
        except GitCommandError as exc:
            console.print(Panel(f"❌ COMMIT FAILED\n{exc}", title="Commit Failed", border_style="red"))
            raise typer.Exit(code=1) from exc
        try:
            publish_local_repository(
                repo_local_root=repo_local_root,
                repo_remote_root=repo_remote_root,
                cloud=cloud_resolved,
                remote_path=remote_path,
                pwd=pwd,
                ignore_gitignore=ignore_gitignore,
            )
        except GpgCommandError as gpg_error:
            _exit_after_gpg_error(error=gpg_error)
        return "created"

    repo_remote_obj = Repo(repo_remote_root)
    try:
        restore_downloaded_file_modes(repo=repo_remote_obj)
        remote_repo_is_dirty = repo_remote_obj.is_dirty(untracked_files=True)
    finally:
        repo_remote_obj.close()
    if remote_repo_is_dirty:
        console.print(
            Panel(
                f"Downloaded repository is dirty and was preserved at {repo_remote_root}\n\n"
                f"Remote location: {cloud_resolved}:{remote_path.as_posix()}\n"
                f"Delete remote: rclone deletefile {cloud_resolved}:{remote_path.as_posix()}",
                title="Invalid Remote Archive",
                border_style="red",
            )
        )
        raise typer.Exit(code=1)

    if repo_local_obj is None:
        validate_integration_transport(repo_local_root=repo_local_root, integration_root=repo_remote_root, cloud=cloud_resolved)
        restore_local_repository(repo_local_root=repo_local_root, repo_remote_root=repo_remote_root)
        console.print(Panel(f"✅ Repository restored to {repo_local_root}", title="First Sync", border_style="green"))
        return "restored"

    if mode == "overwrite-local":
        repo_local_obj.close()
        result = overwrite_local_with_remote(repo_local_root=repo_local_root, repo_remote_root=repo_remote_root)
        console.print(Panel("✅ Local repository replaced with the cloud repository.", title="Overwrite Local", border_style="green"))
        return result

    try:
        commit_local_changes(repo=repo_local_obj, message=message_resolved, console=console)
    except GitCommandError as exc:
        console.print(Panel(f"❌ COMMIT FAILED\n{exc}", title="Commit Failed", border_style="red"))
        raise typer.Exit(code=1) from exc

    integrate_remote_repository(
        local_repo=repo_local_obj,
        repo_remote_root=repo_remote_root,
        integration_root=integration_root,
        cloud=cloud_resolved,
        on_conflict=resolve_conflict_action(on_conflict=on_conflict),
        console=console,
    )

    try:
        publish_local_repository(
            repo_local_root=repo_local_root,
            repo_remote_root=repo_remote_root,
            cloud=cloud_resolved,
            remote_path=remote_path,
            pwd=pwd,
            ignore_gitignore=ignore_gitignore,
        )
    except GpgCommandError as error:
        _exit_after_gpg_error(error=error)
    console.print(Panel("✅ Repository integrated and published successfully.", title="Repo Sync", border_style="green"))
    return "success"
