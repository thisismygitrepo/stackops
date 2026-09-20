from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table
from rich.text import Text


def _local_repository_status(destination: Path) -> tuple[Text, Text]:
    from git.exc import InvalidGitRepositoryError, NoSuchPathError
    from git.repo import Repo

    try:
        with Repo(destination.expanduser(), search_parent_directories=False) as repository:
            dirty = repository.is_dirty(untracked_files=True)
            status = Text("Dirty", style="yellow") if dirty else Text("Clean", style="green")
            if not repository.head.is_valid():
                return status, Text("No commits", style="dim")
            committed_at = repository.head.commit.committed_datetime.astimezone()
            return status, Text(committed_at.strftime("%Y-%m-%d %H:%M"))
    except NoSuchPathError:
        return Text("Missing", style="yellow"), Text("—", style="dim")
    except InvalidGitRepositoryError:
        return Text("Not a Git repo", style="red"), Text("—", style="dim")


def list_repositories(
    specs_path: Annotated[str | None, typer.Option("--specs-path", "-s", help="Path to repos.json specification file.")] = None,
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

    repositories = sorted(spec["repos"], key=lambda record: (record["name"].casefold(), record["parentDir"], record["name"]))
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
        console.print("No repositories registered. Run devops repos register to add repositories.")
        return

    table = Table(
        title="Registered repositories", header_style="bold cyan",
        caption="Status reflects local working trees; commit dates use local time.",
    )
    table.add_column("Repository", style="cyan")
    table.add_column("Destination", overflow="fold")
    table.add_column("Status")
    table.add_column("Last commit", no_wrap=True)
    table.add_column("Sync mode")
    table.add_column("Cloud profile")
    for record in repositories:
        sync = record["sync"]
        destination = Path(record["parentDir"]).joinpath(record["name"])
        status, last_commit = _local_repository_status(destination=destination)
        table.add_row(
            Text(record["name"]),
            Text(destination.as_posix()),
            status,
            last_commit,
            "Encrypted guard" if sync["mode"] == "guard" else "Git",
            Text(sync["cloud"]) if sync["mode"] == "guard" else "—",
        )
    console.print(table)
