from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table
from rich.text import Text

from stackops.scripts.python.helpers.helpers_devops.devops_status_repos import render_local_repository_status
from stackops.scripts.python.helpers.helpers_repos.local_status import inspect_local_repository


def list_repositories(
    specs_path: Annotated[str | None, typer.Option("--specs-path", "-s", help="Path to repos.json specification file.")] = None,
    guarded: Annotated[bool, typer.Option("--guarded", "-g", help="Show only registered repositories using encrypted guard sync.")] = False,
) -> None:
    from stackops.scripts.python.helpers.helpers_repos.spec_store import load_repos_spec, resolve_repos_spec_path

    try:
        path = resolve_repos_spec_path(specs_path=specs_path)
        spec = load_repos_spec(path=path)
    except FileNotFoundError as error:
        typer.echo(
            f"""❌ {error}. Run devops repos register first, or provide another file using --specs-path.""",
            err=True,
        )
        raise typer.Exit(code=1) from error
    except (OSError, ValueError) as error:
        typer.echo(f"""❌ {error}""", err=True)
        raise typer.Exit(code=1) from error

    repositories = sorted(
        (record for record in spec["repos"] if not guarded or record["sync"]["mode"] == "guard"),
        key=lambda record: (record["name"].casefold(), record["parentDir"], record["name"]),
    )
    git_count = sum(record["sync"]["mode"] == "git" for record in repositories)
    guard_count = len(repositories) - git_count
    console = Console()
    console.print(
        f"""Registered: {len(repositories)} · Git sync: {git_count} · Encrypted guard sync: {guard_count}""",
        style="bold",
        markup=False,
        highlight=False,
    )
    console.print(f"""Specification: {path}""", markup=False, highlight=False)
    if not repositories:
        console.print("No guarded repositories registered." if guarded else "No repositories registered. Run devops repos register to add repositories.")
        return

    table = Table(
        title="Guarded repositories" if guarded else "Registered repositories", header_style="bold cyan",
        caption="Files: m modified · n new · d deleted · r renamed · u conflicted. Commit dates use local time.",
    )
    table.add_column("Repository", style="cyan")
    table.add_column("Destination", overflow="fold")
    table.add_column("Status", no_wrap=True)
    table.add_column("Last commit", no_wrap=True)
    table.add_column("Sync mode")
    table.add_column("Cloud profile")
    for record in repositories:
        sync = record["sync"]
        destination = Path(record["parentDir"]).joinpath(record["name"])
        local = inspect_local_repository(destination=destination)
        status, last_commit = render_local_repository_status(status=local)
        table.add_row(
            Text(record["name"]),
            Text(destination.as_posix()),
            status,
            last_commit,
            "Encrypted guard" if sync["mode"] == "guard" else "Git",
            Text(sync["cloud"]) if sync["mode"] == "guard" else "—",
        )
    console.print(table)
