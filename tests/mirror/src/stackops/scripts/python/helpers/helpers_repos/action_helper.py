

from pathlib import Path
from typing import cast

import pytest
import rich.console
from rich.columns import Columns
from rich.panel import Panel
from rich.table import Table

from stackops.scripts.python.helpers.helpers_repos.action_helper import (
    GitOperationResult,
    GitOperationSummary,
    print_git_operations_summary,
)


class RecordingConsole:
    def __init__(self) -> None:
        self.printed: list[object] = []

    def print(self, value: object, *_args: object, **_kwargs: object) -> None:
        self.printed.append(value)


def _printed_strings(console: RecordingConsole) -> list[str]:
    return [value for value in console.printed if isinstance(value, str)]


def test_git_operation_summary_initializes_independent_runtime_lists() -> None:
    first = GitOperationSummary()
    second = GitOperationSummary()

    first.failed_operations.append(
        GitOperationResult(
            repo_path=Path("/tmp/alpha"),
            action="push",
            success=False,
            message="boom",
        )
    )
    first.repos_without_remotes.append(Path("/tmp/no-remote"))

    assert second.failed_operations == []
    assert second.repos_without_remotes == []


def test_print_git_operations_summary_reports_success(monkeypatch: pytest.MonkeyPatch) -> None:
    console = RecordingConsole()
    monkeypatch.setattr(rich.console, "Console", lambda: console)

    summary = GitOperationSummary(
        total_paths_processed=2,
        git_repos_found=2,
        pushes_attempted=2,
        pushes_successful=2,
    )

    print_git_operations_summary(summary=summary, operations_performed=["push"])

    summary_panel = cast(Panel, console.printed[0])
    assert "Total paths processed: 2" in str(summary_panel.renderable)
    assert any(isinstance(value, Columns) for value in console.printed)
    assert "[green]✅ All repositories have remote configurations.[/green]" in _printed_strings(console)
    assert "[green]✅ All git operations completed successfully![/green]" in _printed_strings(console)
    assert any("2 operations completed successfully" in value for value in _printed_strings(console))


def test_print_git_operations_summary_reports_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    console = RecordingConsole()
    monkeypatch.setattr(rich.console, "Console", lambda: console)

    summary = GitOperationSummary(
        total_paths_processed=2,
        git_repos_found=1,
        non_git_paths=1,
        pushes_attempted=1,
        pushes_failed=1,
    )
    summary.repos_without_remotes.append(Path("/repos/demo"))
    summary.failed_operations.append(
        GitOperationResult(
            repo_path=Path("/repos/demo"),
            action="push",
            success=False,
            message="permission denied",
        )
    )

    print_git_operations_summary(summary=summary, operations_performed=["push"])

    assert any(
        isinstance(value, Table) and value.title == "[bold yellow]⚠️ Repositories Without Remotes[/bold yellow]"
        for value in console.printed
    )
    assert any(
        isinstance(value, Table) and value.title == "[bold red]❌ Failed Operations (1 total)[/bold red]"
        for value in console.printed
    )
    assert "[yellow]These repositories cannot be pushed to remote servers.[/yellow]" in _printed_strings(console)
    assert any("0/1 operations succeeded" in value for value in _printed_strings(console))
