from pathlib import Path
from typing import Annotated, Never, assert_never

import typer
from rich.console import Console
from rich.table import Table

from stackops.scripts.python.helpers.helpers_repos.version_capture import VersionOperationError, capture_declared_version
from stackops.scripts.python.helpers.helpers_repos.version_checkout import checkout_declared_version
from stackops.scripts.python.helpers.helpers_repos.version_constants import VERSIONS_FILE_NAME
from stackops.scripts.python.helpers.helpers_repos.version_models import (
    DeclaredVersion,
    RemoteSnapshot,
    RepositoryVersionStatus,
    VersionsFile,
    VersionRepositoryState,
)
from stackops.scripts.python.helpers.helpers_repos.version_paths import resolve_workspace
from stackops.scripts.python.helpers.helpers_repos.version_status import inspect_declared_version
from stackops.scripts.python.helpers.helpers_repos.version_store import (
    VersionStoreError,
    append_declared_version,
    find_declared_version,
    load_versions_file,
    save_versions_file,
)


def _abort(error: ValueError | VersionOperationError) -> Never:
    typer.echo(f"❌ {error}", err=True)
    raise typer.Exit(code=1) from error


def _remote_label(remotes: list[RemoteSnapshot]) -> str:
    labels: list[str] = []
    for remote in remotes:
        branches = ", ".join(f"{branch['name']}@{branch['commit'][:8]}" for branch in remote["branches"])
        labels.append(f"{remote['name']} [{branches or 'no branches'}]")
    return "; ".join(labels) if labels else "local only"


def _state_label(state: VersionRepositoryState) -> str:
    match state:
        case VersionRepositoryState.exact:
            return "✅ Exact"
        case VersionRepositoryState.different:
            return "🔵 Different"
        case VersionRepositoryState.dirty:
            return "🟠 Dirty"
        case VersionRepositoryState.missing:
            return "❌ Missing"
        case VersionRepositoryState.unverifiable:
            return "⚠️ Unverifiable"
    assert_never(state)


def _print_versions(versions_file: VersionsFile, path: Path) -> None:
    table = Table(title=f"Declared repository versions · {path}")
    table.add_column("Version", style="bold cyan", no_wrap=True)
    table.add_column("Message")
    table.add_column("Repositories", justify="right")
    table.add_column("Dirty", justify="right")
    for declared_version in versions_file["versions"]:
        repositories = declared_version["repositories"]
        dirty_count = sum(snapshot["isDirty"] for snapshot in repositories)
        table.add_row(declared_version["version"], declared_version["message"], str(len(repositories)), str(dirty_count))
    Console().print(table)


def _print_version_status(declared_version: DeclaredVersion, statuses: list[RepositoryVersionStatus]) -> None:
    table = Table(title=f"Version {declared_version['version']} · {declared_version['message']}")
    table.add_column("Repository", style="cyan")
    table.add_column("Captured", no_wrap=True)
    table.add_column("State", no_wrap=True)
    table.add_column("Advertised remotes", overflow="fold")
    table.add_column("Details", overflow="fold")
    for status in statuses:
        snapshot = status["snapshot"]
        branch = snapshot["branch"] if snapshot["branch"] is not None else "detached"
        dirty_suffix = " · dirty" if snapshot["isDirty"] else ""
        table.add_row(
            snapshot["path"],
            f"{branch}@{snapshot['commit'][:12]}{dirty_suffix}",
            _state_label(state=status["state"]),
            _remote_label(remotes=snapshot["remotes"]),
            status["detail"],
        )
    Console().print(table)


def declare(
    version: Annotated[str, typer.Argument(help="Unique version identifier.")],
    message: Annotated[str, typer.Option("--message", "-m", help="Message describing this version.")],
    directory: Annotated[str | None, typer.Option("--directory", "-d", help="Workspace containing repositories.")] = None,
    recursive: Annotated[bool, typer.Option("--recursive", "-r", help="Recurse into nested repository directories.")] = False,
) -> None:
    try:
        repos_root = resolve_workspace(directory=directory)
        path = repos_root.joinpath(VERSIONS_FILE_NAME)
        versions_file = load_versions_file(path=path, allow_missing=True)
        if any(existing["version"] == version.strip() for existing in versions_file["versions"]):
            raise VersionStoreError(f"Version {version.strip()!r} is already declared")
        declared_version = capture_declared_version(repos_root=repos_root, version=version, message=message, recursive=recursive)
        updated_file = append_declared_version(versions_file=versions_file, declared_version=declared_version)
        save_versions_file(versions_file=updated_file, path=path)
    except (ValueError, VersionOperationError) as error:
        _abort(error)
    dirty_count = sum(snapshot["isDirty"] for snapshot in declared_version["repositories"])
    typer.echo(f"✅ Declared version {declared_version['version']!r} with {len(declared_version['repositories'])} repositories in {path}")
    if dirty_count:
        typer.echo(f"⚠️ {dirty_count} captured repositories were dirty, so this version cannot be checked out exactly.")


def status(
    version: Annotated[str | None, typer.Argument(help="Version identifier to compare with current repository state.")] = None,
    directory: Annotated[str | None, typer.Option("--directory", "-d", help="Workspace containing versions.json.")] = None,
) -> None:
    try:
        repos_root = resolve_workspace(directory=directory)
        path = repos_root.joinpath(VERSIONS_FILE_NAME)
        versions_file = load_versions_file(path=path, allow_missing=False)
        if version is None:
            _print_versions(versions_file=versions_file, path=path)
            return
        declared_version = find_declared_version(versions_file=versions_file, version=version)
        statuses = inspect_declared_version(repos_root=repos_root, declared_version=declared_version)
    except (ValueError, VersionOperationError) as error:
        _abort(error)
    _print_version_status(declared_version=declared_version, statuses=statuses)


def checkout(
    version: Annotated[str, typer.Argument(help="Declared version identifier to restore.")],
    directory: Annotated[str | None, typer.Option("--directory", "-d", help="Workspace containing versions.json.")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run", "-n", help="Preview checkout without changing repositories.")] = False,
) -> None:
    try:
        repos_root = resolve_workspace(directory=directory)
        path = repos_root.joinpath(VERSIONS_FILE_NAME)
        versions_file = load_versions_file(path=path, allow_missing=False)
        declared_version = find_declared_version(versions_file=versions_file, version=version)
        results = checkout_declared_version(repos_root=repos_root, declared_version=declared_version, dry_run=dry_run)
    except (ValueError, VersionOperationError) as error:
        _abort(error)
    table = Table(title=f"{'Checkout preview' if dry_run else 'Checked out'} · {declared_version['version']}")
    table.add_column("Repository", style="cyan")
    table.add_column("Target")
    table.add_column("Result")
    table.add_column("Recovery ref", overflow="fold")
    for result in results:
        branch = result["branch"] if result["branch"] is not None else "detached"
        if not result["changed"]:
            result_label = "✅ Already exact"
        elif dry_run and result["needsFetch"]:
            result_label = "🔎 Would fetch and checkout"
        elif dry_run:
            result_label = "🔎 Would checkout"
        elif result["needsFetch"]:
            result_label = "✅ Fetched and checked out"
        else:
            result_label = "✅ Checked out"
        table.add_row(result["path"], f"{branch}@{result['commit'][:12]}", result_label, ", ".join(result["backupRefs"]) or "—")
    Console().print(table)


def get_app() -> typer.Typer:
    app = typer.Typer(
        help="🏷️ <V> Capture, inspect, and restore repository versions", no_args_is_help=True, add_help_option=True, add_completion=False
    )
    app.command(name="declare", help="🏷️ <d> Capture repository states as a named version")(declare)
    app.command(name="d", help="Capture repository states as a named version", hidden=True)(declare)
    app.command(name="status", help="📋 <s> Display declared versions or compare one with current repositories")(status)
    app.command(name="s", help="Display declared versions or compare one with current repositories", hidden=True)(status)
    app.command(name="checkout", help="🔀 <c> Restore repositories to a declared version")(checkout)
    app.command(name="c", help="Restore repositories to a declared version", hidden=True)(checkout)
    return app
