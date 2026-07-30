import shutil
from pathlib import Path
from time import monotonic
from typing import Literal, TypedDict

from git.exc import InvalidGitRepositoryError, NoSuchPathError
from git.repo import Repo
from rich import box
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.progress import BarColumn, MofNCompleteColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from stackops.scripts.python.helpers.helpers_repos.discovery import repository_candidates


type CleanStatus = Literal["removed", "missing"]


class CleanResult(TypedDict):
    repository_path: Path
    status: CleanStatus
    elapsed_seconds: float


def clean_agent_directories(*, directory: str | None, recursive: bool) -> bool:
    console = Console()
    requested_root = Path.cwd() if directory is None else Path(directory).expanduser()
    with console.status(f"[bold cyan]Resolving target[/bold cyan] {escape(str(requested_root))}", spinner="dots"):
        repos_root = requested_root.absolute().resolve()

    mode = "recursive" if recursive else "direct children"
    console.print(
        Panel.fit(
            f"[bold]Target[/bold]  {escape(str(repos_root))}\n[bold]Scope[/bold]   {mode}",
            title="Agents Clean",
            border_style="cyan",
        )
    )
    with console.status(f"[bold cyan]Discovering repositories[/bold cyan] under {escape(str(repos_root))}", spinner="dots"):
        candidate_paths = repository_candidates(repos_root=repos_root, recursive=recursive)

    repository_paths: list[Path] = []
    with Progress(
        SpinnerColumn(style="cyan"),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        console=console,
        expand=True,
    ) as progress:
        validation_task = progress.add_task("Checking repository candidates", total=len(candidate_paths))
        for path in candidate_paths:
            progress.update(validation_task, description=f"[cyan]Checking[/cyan] {escape(str(path))}")
            try:
                Repo(path, search_parent_directories=False)
            except (InvalidGitRepositoryError, NoSuchPathError):
                progress.advance(validation_task)
                continue
            repository_paths.append(path)
            progress.advance(validation_task)

    if len(repository_paths) == 0:
        console.print(Panel(f"No Git repositories found at {escape(str(repos_root))}.", title="Nothing to clean", border_style="red"))
        return False

    console.print(f"[bold cyan]Found[/bold cyan] {len(repository_paths)} Git repositories. Starting cleanup...")
    results: list[CleanResult] = []
    with Progress(
        SpinnerColumn(style="yellow"),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        console=console,
        expand=True,
    ) as progress:
        clean_task = progress.add_task("Cleaning repositories", total=len(repository_paths))
        for repository_path in repository_paths:
            started_at = monotonic()
            ai_directory = repository_path.joinpath(".ai")
            if not ai_directory.exists():
                progress.update(clean_task, description=f"[dim]No .ai directory[/dim] {escape(str(repository_path))}")
                results.append({"repository_path": repository_path, "status": "missing", "elapsed_seconds": monotonic() - started_at})
                progress.advance(clean_task)
                continue

            progress.update(clean_task, description=f"[bold yellow]Removing[/bold yellow] {escape(str(ai_directory))}")
            shutil.rmtree(ai_directory)
            results.append({"repository_path": repository_path, "status": "removed", "elapsed_seconds": monotonic() - started_at})
            progress.advance(clean_task)

    result_table = Table(title="Repository cleanup results", box=box.ROUNDED, expand=True)
    result_table.add_column("Repository", style="cyan", overflow="fold", ratio=5)
    result_table.add_column("Result", no_wrap=True, ratio=2)
    result_table.add_column("Time", justify="right", no_wrap=True)
    for result in results:
        result_label = "[bold green]removed .ai[/bold green]" if result["status"] == "removed" else "[dim]no .ai directory[/dim]"
        result_table.add_row(escape(str(result["repository_path"])), result_label, f"{result['elapsed_seconds']:.1f}s")
    console.print(result_table)

    removed_count = sum(result["status"] == "removed" for result in results)
    console.print(
        Panel.fit(
            f"[bold green]Cleanup complete[/bold green]\nRemoved [bold]{removed_count}[/bold] of [bold]{len(repository_paths)}[/bold] .ai directories.",
            border_style="green",
        )
    )
    return True
