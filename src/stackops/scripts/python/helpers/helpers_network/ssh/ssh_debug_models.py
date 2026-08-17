from dataclasses import dataclass
from typing import Literal

from rich import box
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table


CheckStatus = Literal["ok", "error", "unknown"]
CheckGroup = Literal["installation", "service", "configuration", "permissions", "network", "firewall"]


@dataclass(frozen=True, slots=True)
class SSHDebugCheck:
    identifier: str
    group: CheckGroup
    label: str
    status: CheckStatus
    message: str
    command_suggestions: tuple[str, ...]
    manual_advice: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SSHDebugSummary:
    status: CheckStatus
    total_checks: int
    error_count: int
    unknown_count: int
    has_errors: bool
    ready: bool


@dataclass(frozen=True, slots=True)
class SSHDebugResult:
    checks: tuple[SSHDebugCheck, ...]
    summary: SSHDebugSummary


def build_debug_result(checks: list[SSHDebugCheck]) -> SSHDebugResult:
    frozen_checks = tuple(checks)
    error_count = sum(check.status == "error" for check in frozen_checks)
    unknown_count = sum(check.status == "unknown" for check in frozen_checks)
    if not frozen_checks:
        status: CheckStatus = "unknown"
    elif error_count:
        status = "error"
    elif unknown_count:
        status = "unknown"
    else:
        status = "ok"
    summary = SSHDebugSummary(
        status=status,
        total_checks=len(frozen_checks),
        error_count=error_count,
        unknown_count=unknown_count,
        has_errors=error_count > 0,
        ready=bool(frozen_checks) and error_count == 0 and unknown_count == 0,
    )
    return SSHDebugResult(checks=frozen_checks, summary=summary)


def render_debug_result(result: SSHDebugResult, console: Console) -> None:
    group_labels: dict[CheckGroup, str] = {
        "installation": "Installation",
        "service": "Service",
        "configuration": "Configuration",
        "permissions": "Permissions",
        "network": "Network",
        "firewall": "Firewall",
    }
    status_labels: dict[CheckStatus, str] = {
        "ok": "[green]OK[/green]",
        "error": "[red]ERROR[/red]",
        "unknown": "[yellow]UNKNOWN[/yellow]",
    }
    diagnostics = Table(title="SSH server diagnostics", box=box.ROUNDED, show_lines=True)
    diagnostics.add_column("Group", style="cyan", no_wrap=True)
    diagnostics.add_column("Check", style="bold")
    diagnostics.add_column("Status", no_wrap=True)
    diagnostics.add_column("Detail")
    for check in result.checks:
        diagnostics.add_row(
            group_labels[check.group],
            escape(check.label),
            status_labels[check.status],
            escape(check.message),
        )
    console.print(diagnostics)

    command_rows = [
        (check.label, command)
        for check in result.checks
        if check.status != "ok"
        for command in check.command_suggestions
    ]
    if command_rows:
        commands = Table(title="Command suggestions (not executed)", box=box.ROUNDED, show_lines=True)
        commands.add_column("Check", style="yellow")
        commands.add_column("Command", style="green")
        for label, command in command_rows:
            commands.add_row(escape(label), escape(command))
        console.print(commands)

    manual_rows = [
        (check.label, advice)
        for check in result.checks
        if check.status != "ok"
        for advice in check.manual_advice
    ]
    if manual_rows:
        advice_table = Table(title="Manual advice", box=box.ROUNDED, show_lines=True)
        advice_table.add_column("Check", style="yellow")
        advice_table.add_column("Action")
        for label, advice in manual_rows:
            advice_table.add_row(escape(label), escape(advice))
        console.print(advice_table)

    if result.summary.ready:
        summary_text = f"[bold green]All {result.summary.total_checks} required checks passed[/bold green]"
        border_style = "green"
    elif result.summary.has_errors:
        summary_text = (
            f"[bold red]{result.summary.error_count} definite error(s)[/bold red], "
            f"[yellow]{result.summary.unknown_count} unknown check(s)[/yellow]"
        )
        border_style = "red"
    else:
        summary_text = f"[bold yellow]{result.summary.unknown_count} required check(s) could not be verified[/bold yellow]"
        border_style = "yellow"
    console.print(Panel(summary_text, title="Summary", border_style=border_style))
