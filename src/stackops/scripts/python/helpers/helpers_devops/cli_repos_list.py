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
            counts: dict[str, int] = {"m": 0, "n": 0, "d": 0, "r": 0, "u": 0}
            status_output = "" if repository.bare else repository.git.status(porcelain="v1", z=True, untracked_files="all", ignore_submodules="none")
            entries = iter(status_output.split("\0"))
            for entry in entries:
                if not entry:
                    continue
                change = entry[:2]
                if "R" in change or "C" in change:
                    next(entries)
                if "U" in change or change in {"AA", "DD"}:
                    counts["u"] += 1
                elif "D" in change:
                    counts["d"] += 1
                elif change == "??" or "A" in change or "C" in change:
                    counts["n"] += 1
                elif "R" in change:
                    counts["r"] += 1
                else:
                    counts["m"] += 1
            summary = "/".join(f"""{count}{kind}""" for kind, count in counts.items() if count)
            if repository.bare:
                status = Text("Bare", style="dim")
            else:
                status = Text(summary, style="red" if counts["u"] else "yellow") if summary else Text("Clean", style="green")
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
