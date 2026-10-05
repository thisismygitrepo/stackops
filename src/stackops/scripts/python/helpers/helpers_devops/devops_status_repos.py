from dataclasses import dataclass
from pathlib import Path
from typing import assert_never

from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from stackops.scripts.python.helpers.helpers_repos.local_status import LocalRepositoryStatus, inspect_local_repository
from stackops.scripts.python.helpers.helpers_repos.spec_store import load_repos_spec, resolve_repos_spec_path
from stackops.utils.schemas.repos.repos_types import RepoSync


@dataclass(frozen=True)
class RegisteredRepositoryStatus:
    name: str
    sync: RepoSync
    local: LocalRepositoryStatus


@dataclass(frozen=True)
class RepositoriesStatus:
    spec_path: Path
    repositories: tuple[RegisteredRepositoryStatus, ...]


def check_repos_status() -> RepositoriesStatus:
    path = resolve_repos_spec_path(specs_path=None)
    spec = load_repos_spec(path=path)
    repositories = tuple(
        RegisteredRepositoryStatus(
            name=record["name"],
            sync=record["sync"],
            local=inspect_local_repository(destination=Path(record["parentDir"]).joinpath(record["name"])),
        )
        for record in sorted(spec["repos"], key=lambda record: (record["name"].casefold(), record["parentDir"], record["name"]))
    )
    return RepositoriesStatus(spec_path=path, repositories=repositories)


def render_local_repository_status(status: LocalRepositoryStatus) -> tuple[Text, Text]:
    match status.state:
        case "Changed":
            label = Text(status.changes, style="red" if "u" in status.changes else "yellow")
        case "Clean":
            label = Text(status.state, style="green")
        case "Missing":
            label = Text(status.state, style="yellow")
        case "Not a Git repo":
            label = Text(status.state, style="red")
        case "Bare":
            label = Text(status.state, style="dim")
        case _:
            assert_never(status.state)
    if status.state in {"Missing", "Not a Git repo"}:
        last_commit = Text("—", style="dim")
    elif status.committed_at is None:
        last_commit = Text("No commits", style="dim")
    else:
        last_commit = Text(status.committed_at.strftime("%Y-%m-%d %H:%M"))
    return label, last_commit


def render_repos_status(status: RepositoriesStatus) -> Panel:
    source = Text(f"""Specification: {status.spec_path}""", style="dim")
    if not status.repositories:
        return Panel(
            Group(source, Text("No repositories registered. Run devops repos register to add repositories.")),
            title="Repositories (0)", border_style="yellow", padding=(1, 2),
        )

    table = Table(show_lines=True, header_style="bold cyan")
    table.add_column("Repository", style="bold")
    table.add_column("Status")
    table.add_column("Details")
    table.add_column("Sync mode")
    for repository in status.repositories:
        local = repository.local
        label, _last_commit = render_local_repository_status(status=local)
        details = Text(f"""Path: {local.path}""")
        if local.state not in {"Missing", "Not a Git repo"}:
            details.append(f"""\nBranch: {local.branch if local.branch is not None else 'detached'}""")
        sync = repository.sync
        table.add_row(
            Text(repository.name), label, details,
            Text(f"""Encrypted guard · {sync['cloud']}""" if sync["mode"] == "guard" else "Git"),
        )
    caption = Text("Files: m modified · n new · d deleted · r renamed · u conflicted.", style="dim")
    attention = any(repository.local.state not in {"Clean", "Bare"} for repository in status.repositories)
    return Panel(
        Group(source, table, caption), title=f"""Repositories ({len(status.repositories)})""",
        border_style="yellow" if attention else "green", padding=(1, 2),
    )
