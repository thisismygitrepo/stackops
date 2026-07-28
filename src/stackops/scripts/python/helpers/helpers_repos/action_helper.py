from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.table import Table


class GitAction(StrEnum):
    status = "status"
    pull = "pull"
    commit = "commit"
    push = "push"


@dataclass(frozen=True, slots=True)
class GitOperationResult:
    repo_path: Path
    action: GitAction
    success: bool
    message: str
    is_git_repo: bool
    had_changes: bool
    remote_count: int
    dry_run: bool


@dataclass(slots=True)
class GitOperationSummary:
    dry_run: bool
    total_paths_processed: int = 0
    git_repos_found: int = 0
    non_git_paths: int = 0
    statuses_attempted: int = 0
    statuses_clean: int = 0
    statuses_with_changes: int = 0
    statuses_failed: int = 0
    pulls_attempted: int = 0
    pulls_planned: int = 0
    pulls_successful: int = 0
    pulls_failed: int = 0
    commits_attempted: int = 0
    commits_planned: int = 0
    commits_successful: int = 0
    commits_no_changes: int = 0
    commits_failed: int = 0
    pushes_attempted: int = 0
    pushes_planned: int = 0
    pushes_successful: int = 0
    pushes_failed: int = 0
    operation_results: list[GitOperationResult] = field(default_factory=list)
    failed_operations: list[GitOperationResult] = field(default_factory=list)


def _operation_panel(summary: GitOperationSummary, action: GitAction) -> Panel:
    match action:
        case GitAction.pull:
            lines = [
                f"Attempted: {summary.pulls_attempted}",
                f"Planned: {summary.pulls_planned}",
                f"Successful: {summary.pulls_successful}",
                f"Failed: {summary.pulls_failed}",
            ]
            return Panel.fit("\n".join(lines), title="[bold cyan]⬇️ Pull Operations[/bold cyan]", border_style="cyan")
        case GitAction.commit:
            lines = [
                f"Attempted: {summary.commits_attempted}",
                f"Planned: {summary.commits_planned}",
                f"Successful: {summary.commits_successful}",
                f"No changes: {summary.commits_no_changes}",
                f"Failed: {summary.commits_failed}",
            ]
            return Panel.fit("\n".join(lines), title="[bold green]💾 Commit Operations[/bold green]", border_style="green")
        case GitAction.push:
            lines = [
                f"Attempted: {summary.pushes_attempted}",
                f"Planned: {summary.pushes_planned}",
                f"Successful: {summary.pushes_successful}",
                f"Failed: {summary.pushes_failed}",
            ]
            return Panel.fit("\n".join(lines), title="[bold magenta]🚀 Push Operations[/bold magenta]", border_style="magenta")
        case GitAction.status:
            lines = [
                f"Checked: {summary.statuses_attempted}",
                f"Clean: {summary.statuses_clean}",
                f"With changes: {summary.statuses_with_changes}",
                f"Failed: {summary.statuses_failed}",
            ]
            return Panel.fit("\n".join(lines), title="[bold blue]📋 Repository Status[/bold blue]", border_style="blue")


def _result_state(result: GitOperationResult) -> str:
    if not result.success:
        return "❌ Failed"
    if result.dry_run:
        return "🔎 Planned"
    if result.action is GitAction.commit and not result.had_changes:
        return "✅ No changes"
    return "✅ Success"


def print_git_operations_summary(summary: GitOperationSummary, operations_performed: tuple[GitAction, ...]) -> None:
    console = Console()
    summary_stats = [
        f"Total paths processed: {summary.total_paths_processed}",
        f"Git repositories found: {summary.git_repos_found}",
        f"Non-git paths skipped: {summary.non_git_paths}",
    ]
    console.print(Panel.fit("\n".join(summary_stats), title="[bold blue]📊 Git Operations Summary[/bold blue]", border_style="blue"))
    console.print(Columns([_operation_panel(summary=summary, action=action) for action in operations_performed], equal=True, expand=True))

    sorted_results = sorted(summary.operation_results, key=lambda result: (result.repo_path.as_posix(), operations_performed.index(result.action)))
    if operations_performed == (GitAction.status,):
        status_table = Table(title="[bold blue]📋 Repository Status[/bold blue]", expand=True)
        status_table.add_column("Repository", style="cyan", overflow="fold", max_width=36)
        status_table.add_column("State", no_wrap=True)
        status_table.add_column("Git status", style="dim", overflow="fold")
        for result in sorted_results:
            state = "❌ Failed" if not result.success else "🟠 Changes" if result.had_changes else "✅ Clean"
            status_table.add_row(result.repo_path.as_posix(), state, result.message)
        console.print(status_table)
    elif sorted_results:
        results_table = Table(title="[bold blue]📋 Repository Operation Results[/bold blue]", expand=True)
        results_table.add_column("Repository", style="cyan", overflow="fold", max_width=36)
        results_table.add_column("Action", style="bold", no_wrap=True)
        results_table.add_column("State", no_wrap=True)
        results_table.add_column("Details", overflow="fold")
        for result in sorted_results:
            results_table.add_row(result.repo_path.as_posix(), result.action.value, _result_state(result), result.message)
        console.print(results_table)

    total_operations = (
        summary.statuses_attempted
        + summary.pulls_attempted
        + summary.pulls_planned
        + summary.commits_attempted
        + summary.commits_planned
        + summary.pushes_attempted
        + summary.pushes_planned
    )
    total_failed = len(summary.failed_operations)
    operation_label = "operation" if total_operations == 1 else "operations"
    if total_operations == 0:
        console.print("[yellow]📝 No git operations were performed.[/yellow]")
    elif total_failed:
        succeeded = total_operations - total_failed
        console.print(f"[bold red]❌ FAILED: {succeeded}/{total_operations} {operation_label} succeeded.[/bold red]")
    elif summary.dry_run:
        console.print(f"[bold blue]🔎 DRY RUN: {total_operations} {operation_label} checked; no repositories were changed.[/bold blue]")
    else:
        console.print(f"[bold green]🎉 SUCCESS: All {total_operations} {operation_label} completed successfully![/bold green]")
