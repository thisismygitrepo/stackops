import time
from pathlib import Path

from rich import box
from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table
from rich.text import Text

try:
    import models as models_module  # type: ignore[import-not-found] # sibling script, resolved at runtime via sys.path
except ModuleNotFoundError:
    from machineconfig.scripts.python.ai.scripts import models as models_module


CHECKER_SPECS = models_module.CHECKER_SPECS
CLEANUP_COMMANDS = models_module.CLEANUP_COMMANDS
DONE_LABEL = models_module.DONE_LABEL
ERROR_LABEL = models_module.ERROR_LABEL
FAILURE_LABEL = models_module.FAILURE_LABEL
ISSUES_LABEL = models_module.ISSUES_LABEL
RUNNING_LABEL = models_module.RUNNING_LABEL
START_FAILED_KIND = models_module.START_FAILED_KIND
SUCCESS_LABEL = models_module.SUCCESS_LABEL
SUMMARY_PATH = models_module.SUMMARY_PATH
CleanupResult = models_module.CleanupResult
RunningTool = models_module.RunningTool
ToolResult = models_module.ToolResult
format_bytes = models_module.format_bytes
format_command = models_module.format_command
format_diagnostic_distribution = models_module.format_diagnostic_distribution
format_duration = models_module.format_duration
format_share = models_module.format_share
read_report_stats = models_module.read_report_stats
relative_path = models_module.relative_path


def build_command_preview() -> RenderableType:
    command_table = Table(box=box.SIMPLE_HEAVY, expand=True)
    command_table.add_column("Phase", style="bold")
    command_table.add_column("Tool", style="bold cyan")
    command_table.add_column("Command", overflow="fold")
    for index, command in enumerate(CLEANUP_COMMANDS, start=1):
        command_table.add_row("cleanup", f"step {index}", format_command(command))
    for spec in CHECKER_SPECS:
        command_table.add_row("checker", spec.title, format_command(spec.command))
    return Panel(command_table, title="Commands To Execute", border_style="blue")


def build_progress(total_checkers: int, completed_checkers: int) -> Progress:
    progress = Progress(
        SpinnerColumn(style="cyan"),
        TextColumn("[bold cyan]{task.description}"),
        BarColumn(bar_width=None),
        TextColumn("{task.completed}/{task.total} finished"),
        TimeElapsedColumn(),
        expand=True,
    )
    progress.add_task(
        description="Parallel linters and type checkers",
        total=total_checkers,
        completed=completed_checkers,
    )
    return progress


def checker_state_text(result: ToolResult | None) -> Text:
    if result is None:
        return Text(RUNNING_LABEL, style="yellow")
    if result.run_state == ERROR_LABEL:
        return Text(ERROR_LABEL, style="red")
    return Text(DONE_LABEL, style="cyan")


def checker_status_text(result: ToolResult | None) -> Text:
    if result is None:
        return Text("-", style="dim")
    if result.status == SUCCESS_LABEL:
        return Text(SUCCESS_LABEL, style="green")
    if result.status == ISSUES_LABEL:
        return Text(ISSUES_LABEL, style="yellow")
    return Text(FAILURE_LABEL, style="red")


def build_live_renderable(
    repo_root: Path,
    cleanup_result: CleanupResult,
    running_tools: dict[str, RunningTool],
    completed_tools: dict[str, ToolResult],
    wall_started_at: float,
) -> RenderableType:
    finished_count = len(completed_tools)
    total_checkers = len(CHECKER_SPECS)
    passed_count = sum(1 for result in completed_tools.values() if result.status == SUCCESS_LABEL)
    issue_count = sum(1 for result in completed_tools.values() if result.status == ISSUES_LABEL)
    error_count = sum(1 for result in completed_tools.values() if result.status == FAILURE_LABEL)
    running_count = len(running_tools)

    header_grid = Table.grid(expand=True)
    header_grid.add_column(ratio=1)
    header_grid.add_column(justify="right")
    header_grid.add_row(
        Text("Lint And Type Check Dashboard", style="bold cyan"),
        Text(format_duration(time.monotonic() - wall_started_at), style="bold white"),
    )
    header_grid.add_row(
        Text(str(repo_root), style="dim"),
        Text(
            f"cleanup {cleanup_result.status.lower()} in {format_duration(cleanup_result.duration_seconds)}",
            style="dim",
        ),
    )

    stats_grid = Table.grid(expand=True)
    stats_grid.add_column(justify="left")
    stats_grid.add_column(justify="center")
    stats_grid.add_column(justify="center")
    stats_grid.add_column(justify="right")
    stats_grid.add_row(
        Text(f"running {running_count}", style="yellow"),
        Text(f"passed {passed_count}", style="green"),
        Text(f"issues {issue_count}", style="yellow"),
        Text(f"errors {error_count}", style="red" if error_count > 0 else "green"),
    )

    checker_table = Table(box=box.SIMPLE_HEAVY, expand=True)
    checker_table.add_column("Tool", style="bold")
    checker_table.add_column("State", justify="center")
    checker_table.add_column("Outcome", justify="center")
    checker_table.add_column("Elapsed", justify="right")
    checker_table.add_column("Exit", justify="right")
    checker_table.add_column("Report", overflow="fold")
    checker_table.add_column("Size", justify="right")
    for spec in CHECKER_SPECS:
        result = completed_tools.get(spec.slug)
        running_tool = running_tools.get(spec.slug)
        if result is not None:
            elapsed_seconds = result.duration_seconds
        elif running_tool is not None:
            elapsed_seconds = time.monotonic() - running_tool.started_at
        else:
            elapsed_seconds = 0.0
        exit_text = "-" if result is None else str(result.exit_code)
        report_size = read_report_stats(spec.report_path).byte_count
        checker_table.add_row(
            spec.title,
            checker_state_text(result),
            checker_status_text(result),
            format_duration(elapsed_seconds),
            exit_text,
            relative_path(spec.report_path),
            format_bytes(report_size),
        )

    return Group(
        Panel(header_grid, box=box.DOUBLE, border_style="cyan"),
        build_progress(total_checkers=total_checkers, completed_checkers=finished_count),
        Panel(stats_grid, title="Status", border_style="blue"),
        Panel(checker_table, title="Checkers", border_style="magenta"),
    )


def build_final_summary(
    cleanup_result: CleanupResult,
    checker_results: tuple[ToolResult, ...],
    wall_started_at: float,
) -> RenderableType:
    checker_sum = sum(result.duration_seconds for result in checker_results)
    checker_wall = max(
        (result.finished_at for result in checker_results),
        default=cleanup_result.finished_at,
    ) - min(
        (result.started_at for result in checker_results),
        default=cleanup_result.finished_at,
    )
    total_duration = time.monotonic() - wall_started_at
    slowest_result = max(checker_results, key=lambda result: result.duration_seconds)
    passed_count = sum(1 for result in checker_results if result.status == SUCCESS_LABEL)
    issue_count = sum(1 for result in checker_results if result.status == ISSUES_LABEL)
    error_count = sum(1 for result in checker_results if result.status == FAILURE_LABEL)

    summary_grid = Table.grid(expand=True)
    summary_grid.add_column(ratio=1)
    summary_grid.add_column(ratio=1)
    summary_grid.add_row(
        f"cleanup: {cleanup_result.status} in {format_duration(cleanup_result.duration_seconds)}",
        f"end-to-end: {format_duration(total_duration)}",
    )
    summary_grid.add_row(
        f"checker wall time: {format_duration(checker_wall)}",
        f"sum of checker runtimes: {format_duration(checker_sum)}",
    )
    summary_grid.add_row(
        f"parallel speedup: {checker_sum / checker_wall:.2f}x" if checker_wall > 0 else "parallel speedup: 0.00x",
        f"slowest: {slowest_result.spec.title} ({format_duration(slowest_result.duration_seconds)})",
    )
    summary_grid.add_row(
        f"passed tools: {passed_count}/{len(checker_results)}",
        f"tools with issues: {issue_count}/{len(checker_results)}",
    )
    summary_grid.add_row(
        f"tool errors: {error_count}/{len(checker_results)}",
        f"summary file: {relative_path(SUMMARY_PATH)}",
    )

    table = Table(box=box.SIMPLE_HEAVY, expand=True)
    table.add_column("Tool", style="bold")
    table.add_column("State", justify="center")
    table.add_column("Outcome", justify="center")
    table.add_column("Exit", justify="right")
    table.add_column("Duration", justify="right")
    table.add_column("Share", justify="right")
    table.add_column("Lines", justify="right")
    table.add_column("Size", justify="right")
    table.add_column("Report", overflow="fold")
    for result in sorted(checker_results, key=lambda item: item.duration_seconds, reverse=True):
        table.add_row(
            result.spec.title,
            result.run_state,
            checker_status_text(result),
            str(result.exit_code),
            format_duration(result.duration_seconds),
            format_share(result.duration_seconds, checker_sum),
            str(result.report_stats.line_count),
            format_bytes(result.report_stats.byte_count),
            relative_path(result.spec.report_path),
        )

    diagnostics_table = Table(box=box.SIMPLE_HEAVY, expand=True)
    diagnostics_table.add_column("Tool", style="bold")
    diagnostics_table.add_column("Outcome", justify="center")
    diagnostics_table.add_column("Diagnostics", justify="right")
    diagnostics_table.add_column("By", justify="center")
    diagnostics_table.add_column("Distribution", overflow="fold")
    for result in checker_results:
        diagnostic_count = str(result.diagnostic_summary.total_count)
        classifier = result.diagnostic_summary.classifier
        distribution = format_diagnostic_distribution(result.diagnostic_summary)
        if result.result_kind == START_FAILED_KIND:
            diagnostic_count = "-"
            classifier = "-"
            distribution = "start failure"
        diagnostics_table.add_row(
            result.spec.title,
            checker_status_text(result),
            diagnostic_count,
            classifier,
            distribution,
        )

    border_style = "green"
    if cleanup_result.exit_code != 0 or error_count > 0:
        border_style = "red"
    elif issue_count > 0:
        border_style = "yellow"
    return Group(
        Panel(summary_grid, title="Summary", border_style=border_style),
        Panel(table, title="Timings", border_style=border_style),
        Panel(diagnostics_table, title="Diagnostics", border_style=border_style),
    )
