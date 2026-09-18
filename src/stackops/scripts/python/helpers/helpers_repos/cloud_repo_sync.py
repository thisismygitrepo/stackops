import os
from pathlib import Path
from typing import Annotated, Literal, Never

import typer

from stackops.scripts.python.helpers.helpers_repos.cloud_repo_sync_conflicts import ConflictResolutionOption
from stackops.scripts.python.helpers.helpers_repos.guard_transport import GuardOperation
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
        str | None, typer.Option(..., "--cloud", "-C", help="Cloud storage profile; otherwise use the registered or default profile.")
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
        bool | None,
        typer.Option("--ignore-gitignore/--respect-gitignore", help="Override whether the archive includes Git-ignored files."),
    ] = None,
    specs_path: Annotated[str | None, typer.Option("--specs-path", help="Repository specification containing saved guard settings.")] = None,
) -> str | None:
    from git.exc import InvalidGitRepositoryError, NoSuchPathError
    from git.repo import Repo
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text

    from stackops.scripts.python.helpers.helpers_repos.cloud_repo_sync_archive import get_repo_remote_archive_path
    from stackops.scripts.python.helpers.helpers_repos.cloud_repo_sync_conflicts import resolve_conflict_action
    from stackops.scripts.python.helpers.helpers_repos.guard_transport import run_guard_repository
    from stackops.scripts.python.helpers.helpers_repos.spec_store import load_repository_syncs
    from stackops.utils.cloud.default_remote import DefaultRcloneRemoteConfigError, read_default_rclone_remote
    from stackops.utils.source_of_truth import DOTFILES_STACKOPS_CONFIG_PATH

    operation: GuardOperation
    match mode:
        case "m" | "merge":
            operation = "sync"
        case "l" | "overwrite-local":
            operation = "overwrite-local"
        case "r" | "overwrite-remote":
            operation = "overwrite-remote"

    console = Console()
    requested_repo_root = Path(os.path.abspath(Path.cwd() if repo == "." else Path(repo).expanduser()))
    step = "Opening the local Git repository"
    try:
        try:
            with Repo(requested_repo_root, search_parent_directories=requested_repo_root == Path.cwd()) as local_repo:
                repo_root = Path(local_repo.working_dir)
        except InvalidGitRepositoryError as error:
            raise InvalidGitRepositoryError(
                f"""Git does not recognize {requested_repo_root} as a repository. """
                """Check the repository path and whether its .git metadata is missing or invalid."""
            ) from error
        except NoSuchPathError:
            if os.path.lexists(requested_repo_root):
                raise
            repo_root = requested_repo_root
        step = "Loading repository settings"
        sync = load_repository_syncs(specs_path=specs_path).get(repo_root.resolve())
        step = "Resolving cloud storage"
        if cloud is not None:
            cloud_resolved = cloud
        elif sync is not None and sync["mode"] == "guard":
            cloud_resolved = sync["cloud"]
        else:
            try:
                cloud_resolved = read_default_rclone_remote()
            except DefaultRcloneRemoteConfigError as exc:
                raise ValueError(f"""{exc}. Use devops repos guard REPO --cloud REMOTE.""") from exc
            console.print(Panel(f"Using default cloud `{cloud_resolved}` from {DOTFILES_STACKOPS_CONFIG_PATH}", title="Default Cloud"))
        step = "Resolving the remote archive path"
        if sync is not None and sync["mode"] == "guard":
            remote_path = Path(sync["remotePath"])
            include_ignored = sync["ignoreGitignore"] if ignore_gitignore is None else ignore_gitignore
        else:
            repo_root.resolve().relative_to(Path.home().resolve())
            remote_path = get_repo_remote_archive_path(repo_root=repo_root)
            include_ignored = ignore_gitignore is True
        step = f"""Running repository operation: {operation}"""
        result = run_guard_repository(
            repo_root=repo_root,
            cloud=cloud_resolved,
            remote_path=remote_path,
            operation=operation,
            pwd=pwd,
            message=message,
            on_conflict=resolve_conflict_action(on_conflict=on_conflict),
            ignore_gitignore=include_ignored,
        )
    except GpgCommandError as error:
        _exit_after_gpg_error(error=error)
    except typer.Exit:
        raise
    except Exception as error:
        details = Text(f"""❌ {step}
Repository: {requested_repo_root}
Mode: {mode}

{type(error).__name__}: {error}""")
        console.print(Panel(details, title="Guard Failed", border_style="red"))
        raise typer.Exit(code=1) from error
    console.print(Panel(f"✅ Guard repository {result}: {repo_root}", title="Repo Guard", border_style="green"))
    return result
