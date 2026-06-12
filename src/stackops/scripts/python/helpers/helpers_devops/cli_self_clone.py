from pathlib import Path
from typing import Annotated

import typer

STACKOPS_REPO_HTTPS = "https://github.com/thisismygitrepo/stackops.git"
STACKOPS_REPO_SSH = "git@github.com:thisismygitrepo/stackops.git"


def _stackops_clone_remote(remote: str | None, use_ssh: bool) -> str:
    if remote is not None:
        if use_ssh:
            typer.echo("ℹ️ --remote was provided, so --ssh is ignored.")
        return remote
    return STACKOPS_REPO_SSH if use_ssh else STACKOPS_REPO_HTTPS


def _run_git_command(args: list[str], *, cwd: Path | None = None, dry_run: bool = False) -> None:
    import shlex
    import subprocess

    command_text = shlex.join(args)
    if cwd is not None:
        command_text = f"cd {shlex.quote(cwd.as_posix())} && {command_text}"
    typer.echo(f"➤ {command_text}")
    if dry_run:
        return

    try:
        proc = subprocess.run(args, cwd=str(cwd) if cwd is not None else None, check=False)
    except FileNotFoundError as exc:
        typer.echo("❌ git executable not found. Install git and retry.", err=True)
        raise typer.Exit(code=1) from exc
    if proc.returncode != 0:
        raise typer.Exit(code=proc.returncode)


def _install_editable_stackops_checkout(checkout_path: Path, *, dry_run: bool) -> None:
    import platform

    from stackops.utils.code import get_uv_command, run_shell_script

    uv_command = get_uv_command(platform=platform.system())
    shell_script = f"""
cd "{str(checkout_path)}"
{uv_command} sync --no-dev
{uv_command} tool install --upgrade --editable "{str(checkout_path)}"
"""
    if dry_run:
        typer.echo("➤ Editable install script:")
        for line in shell_script.strip().splitlines():
            typer.echo(f"  {line}")
        return

    proc = run_shell_script(shell_script, display_script=True, clean_env=False)
    if proc.returncode != 0:
        raise typer.Exit(code=proc.returncode)


def _clone_stackops_repo(destination: Path, *, remote_url: str, branch: str | None, depth: int | None, dry_run: bool) -> None:
    clone_args = ["git", "clone"]
    if branch is not None:
        clone_args.extend(["--branch", branch])
    if depth is not None:
        clone_args.extend(["--depth", str(depth)])
    clone_args.extend([remote_url, str(destination)])
    _run_git_command(clone_args, dry_run=dry_run)
    if dry_run:
        typer.echo(f"ℹ️ Dry run only. StackOps checkout would be: {destination}")
    else:
        typer.echo(f"✅ StackOps checkout ready: {destination}")


def clone(
    directory: Annotated[
        Path | None,
        typer.Argument(help="Directory for the StackOps checkout. Defaults to the current directory."),
    ] = None,
    remote: Annotated[
        str | None,
        typer.Option("--remote", "-r", help="Git remote URL. Defaults to the StackOps HTTPS remote, or SSH when --ssh is set."),
    ] = None,
    ssh: Annotated[
        bool,
        typer.Option("--ssh", "-s", help="Use the built-in git@github.com SSH remote instead of HTTPS."),
    ] = False,
    branch: Annotated[
        str | None,
        typer.Option("--branch", "-b", help="Branch or tag to check out during clone, or in an existing checkout."),
    ] = None,
    depth: Annotated[
        int | None,
        typer.Option("--depth", "-d", help="Create a shallow clone with the given depth."),
    ] = None,
    pull: Annotated[
        bool,
        typer.Option("--pull", "-p", help="If DIRECTORY already exists as a git repo, pull with --ff-only."),
    ] = False,
    install_editable: Annotated[
        bool,
        typer.Option("--install", "-i", help="Run uv sync and install the checkout as an editable stackops tool."),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", "-n", help="Print the git and uv actions without changing files."),
    ] = False,
) -> None:
    """📥 Clone the StackOps source checkout."""
    if depth is not None and depth < 1:
        typer.echo("❌ --depth must be 1 or greater.", err=True)
        raise typer.Exit(code=1)

    destination = Path.cwd().absolute() if directory is None else directory.expanduser().absolute()
    remote_url = _stackops_clone_remote(remote=remote, use_ssh=ssh)
    git_marker = destination.joinpath(".git")

    if destination.exists():
        if not destination.is_dir():
            typer.echo(f"❌ Destination exists but is not a directory: {destination}", err=True)
            raise typer.Exit(code=1)
        if git_marker.exists():
            typer.echo(f"ℹ️ Reusing existing checkout: {destination}")
            if branch is not None:
                _run_git_command(["git", "fetch", "--all", "--prune"], cwd=destination, dry_run=dry_run)
                _run_git_command(["git", "checkout", branch], cwd=destination, dry_run=dry_run)
            if pull:
                _run_git_command(["git", "pull", "--ff-only"], cwd=destination, dry_run=dry_run)
            elif branch is None:
                typer.echo("ℹ️ Existing checkout left unchanged. Use --pull to update it.")
        elif any(destination.iterdir()):
            typer.echo(f"❌ Destination exists but is neither empty nor a git repository: {destination}", err=True)
            raise typer.Exit(code=1)
        else:
            _clone_stackops_repo(destination, remote_url=remote_url, branch=branch, depth=depth, dry_run=dry_run)
    else:
        if not destination.parent.exists():
            import shlex

            typer.echo(f"➤ mkdir -p {shlex.quote(destination.parent.as_posix())}")
            if not dry_run:
                destination.parent.mkdir(parents=True, exist_ok=True)
        _clone_stackops_repo(destination, remote_url=remote_url, branch=branch, depth=depth, dry_run=dry_run)

    if install_editable:
        _install_editable_stackops_checkout(destination, dry_run=dry_run)
    elif not dry_run:
        typer.echo(f"Next: cd {destination}")
