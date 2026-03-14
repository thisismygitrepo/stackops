#!/usr/bin/env -S uv run
# /// script
# dependencies = ["rich"]
# ///

from __future__ import annotations

import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal, TextIO

from rich import box
from rich.console import Console, Group, RenderableType
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table
from rich.text import Text


REPO_MARKER: Final[Path] = Path("pyproject.toml")
REPORTS_DIR: Final[Path] = Path(".ai/linters")
SUMMARY_PATH: Final[Path] = REPORTS_DIR / "timing_summary.md"
CHECKER_REFRESH_SECONDS: Final[float] = 0.15
SUCCESS_LABEL: Final[str] = "PASS"
FAILURE_LABEL: Final[str] = "FAIL"
RUNNING_LABEL: Final[str] = "RUNNING"


@dataclass(frozen=True, slots=True)
class ToolSpec:
    slug: str
    title: str
    report_path: Path
    command: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ReportStats:
    line_count: int
    byte_count: int


@dataclass(frozen=True, slots=True)
class CleanupResult:
    exit_code: int
    started_at: float
    finished_at: float
    report_path: Path
    report_stats: ReportStats

    @property
    def duration_seconds(self) -> float:
        return self.finished_at - self.started_at

    @property
    def status(self) -> Literal["PASS", "FAIL"]:
        return SUCCESS_LABEL if self.exit_code == 0 else FAILURE_LABEL


@dataclass(frozen=True, slots=True)
class ToolResult:
    spec: ToolSpec
    exit_code: int
    started_at: float
    finished_at: float
    report_stats: ReportStats

    @property
    def duration_seconds(self) -> float:
        return self.finished_at - self.started_at

    @property
    def status(self) -> Literal["PASS", "FAIL"]:
        return SUCCESS_LABEL if self.exit_code == 0 else FAILURE_LABEL


@dataclass(slots=True)
class RunningTool:
    spec: ToolSpec
    process: subprocess.Popen[bytes]
    report_handle: TextIO
    started_at: float


CLEANUP_COMMANDS: Final[tuple[tuple[str, ...], ...]] = (
    ("uv", "run", "--frozen", "--with", "cleanpy", "-m", "cleanpy", "."),
    ("uv", "run", "--frozen", "--with", "ruff", "-m", "ruff", "clean"),
    ("uv", "run", "--frozen", "--with", "ruff", "ruff", "check", ".", "--fix"),
)

CHECKER_SPECS: Final[tuple[ToolSpec, ...]] = (
    ToolSpec(
        slug="pyright",
        title="Pyright Type Checker",
        report_path=REPORTS_DIR / "issues_pyright.md",
        command=("uv", "run", "--frozen", "--with", "pyright", "pyright", "."),
    ),
    ToolSpec(
        slug="mypy",
        title="MyPy Type Checker",
        report_path=REPORTS_DIR / "issues_mypy.md",
        command=("uv", "run", "--frozen", "--with", "mypy", "mypy", "."),
    ),
    ToolSpec(
        slug="pylint",
        title="Pylint Code Analysis",
        report_path=REPORTS_DIR / "issues_pylint.md",
        command=(
            "uv",
            "run",
            "--frozen",
            "--with",
            "pylint",
            "pylint",
            "--recursive=y",
            ".",
        ),
    ),
    ToolSpec(
        slug="pyrefly",
        title="Pyrefly Type Checker",
        report_path=REPORTS_DIR / "issues_pyrefly.md",
        command=("uv", "run", "--frozen", "--with", "pyrefly", "pyrefly", "check", "."),
    ),
    ToolSpec(
        slug="ty",
        title="Ty Type Checker",
        report_path=REPORTS_DIR / "issues_ty.md",
        command=("uv", "run", "--frozen", "--with", "ty", "ty", "check", "."),
    ),
    ToolSpec(
        slug="ruff",
        title="Ruff Linter",
        report_path=REPORTS_DIR / "issues_ruff.md",
        command=("uv", "run", "--frozen", "--with", "ruff", "ruff", "check", "."),
    ),
)


def format_duration(seconds: float) -> str:
    minutes = int(seconds // 60)
    remainder = seconds - (minutes * 60)
    if minutes > 0:
        return f"{minutes}m {remainder:05.2f}s"
    return f"{remainder:.2f}s"


def format_bytes(byte_count: int) -> str:
    units: tuple[str, ...] = ("B", "KB", "MB", "GB")
    size = float(byte_count)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} {unit}"
        size /= 1024
    return f"{byte_count} B"


def format_share(value: float, total: float) -> str:
    if total <= 0:
        return "0.0%"
    return f"{(value / total) * 100:.1f}%"


def relative_path(path: Path) -> str:
    return f"./{path.as_posix()}"


def read_report_stats(report_path: Path) -> ReportStats:
    if report_path.exists() is False:
        return ReportStats(line_count=0, byte_count=0)
    with report_path.open("r", encoding="utf-8", errors="replace") as handle:
        line_count = sum(1 for _ in handle)
    return ReportStats(line_count=line_count, byte_count=report_path.stat().st_size)


def write_start_failure(
    report_path: Path, title: str, command: tuple[str, ...], error: OSError
) -> None:
    report_path.write_text(
        data="\n".join(
            (
                f"# {title}",
                "",
                f"- Command: `{' '.join(command)}`",
                f"- Start failure: `{error}`",
                "",
            )
        )
        + "\n",
        encoding="utf-8",
    )


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


def checker_status_text(result: ToolResult | None) -> Text:
    if result is None:
        return Text(RUNNING_LABEL, style="yellow")
    if result.exit_code == 0:
        return Text(SUCCESS_LABEL, style="green")
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
    failed_count = sum(
        1 for result in completed_tools.values() if result.exit_code != 0
    )
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
        Text(f"passed {finished_count - failed_count}", style="green"),
        Text(f"failed {failed_count}", style="red" if failed_count > 0 else "green"),
        Text(f"reports {relative_path(REPORTS_DIR)}", style="cyan"),
    )

    checker_table = Table(box=box.SIMPLE_HEAVY, expand=True)
    checker_table.add_column("Tool", style="bold")
    checker_table.add_column("State", justify="center")
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
            checker_status_text(result),
            format_duration(elapsed_seconds),
            exit_text,
            relative_path(spec.report_path),
            format_bytes(report_size),
        )

    return Group(
        Panel(header_grid, box=box.DOUBLE, border_style="cyan"),
        build_progress(
            total_checkers=total_checkers, completed_checkers=finished_count
        ),
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
    failed_count = sum(1 for result in checker_results if result.exit_code != 0)

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
        f"parallel speedup: {checker_sum / checker_wall:.2f}x"
        if checker_wall > 0
        else "parallel speedup: 0.00x",
        f"slowest: {slowest_result.spec.title} ({format_duration(slowest_result.duration_seconds)})",
    )
    summary_grid.add_row(
        f"failed tools: {failed_count}/{len(checker_results)}",
        f"summary file: {relative_path(SUMMARY_PATH)}",
    )

    table = Table(box=box.SIMPLE_HEAVY, expand=True)
    table.add_column("Tool", style="bold")
    table.add_column("Status", justify="center")
    table.add_column("Exit", justify="right")
    table.add_column("Duration", justify="right")
    table.add_column("Share", justify="right")
    table.add_column("Lines", justify="right")
    table.add_column("Size", justify="right")
    table.add_column("Report", overflow="fold")
    for result in sorted(
        checker_results, key=lambda item: item.duration_seconds, reverse=True
    ):
        table.add_row(
            result.spec.title,
            checker_status_text(result),
            str(result.exit_code),
            format_duration(result.duration_seconds),
            format_share(result.duration_seconds, checker_sum),
            str(result.report_stats.line_count),
            format_bytes(result.report_stats.byte_count),
            relative_path(result.spec.report_path),
        )

    border_style = (
        "red" if failed_count > 0 or cleanup_result.exit_code != 0 else "green"
    )
    return Group(
        Panel(summary_grid, title="Summary", border_style=border_style),
        Panel(table, title="Timings", border_style=border_style),
    )


def run_cleanup(console: Console) -> CleanupResult:
    cleanup_path = REPORTS_DIR / "log_cleanup.md"
    started_at = time.monotonic()
    exit_code = 0
    with cleanup_path.open("w", encoding="utf-8") as handle:
        for command in CLEANUP_COMMANDS:
            handle.write(f"$ {' '.join(command)}\n")
            handle.flush()
            completed = subprocess.run(
                command, stdout=handle, stderr=subprocess.STDOUT, check=False
            )
            if completed.returncode != 0 and exit_code == 0:
                exit_code = completed.returncode
            handle.write("\n")
            handle.flush()
    finished_at = time.monotonic()
    result = CleanupResult(
        exit_code=exit_code,
        started_at=started_at,
        finished_at=finished_at,
        report_path=cleanup_path,
        report_stats=read_report_stats(cleanup_path),
    )
    style = "green" if result.exit_code == 0 else "red"
    console.print(
        Panel(
            Text(
                f"cleanup {result.status.lower()} in {format_duration(result.duration_seconds)}\nlog: {relative_path(result.report_path)}",
                style=style,
            ),
            title="Preparation",
            border_style=style,
        )
    )
    return result


def start_checker_processes() -> tuple[dict[str, RunningTool], dict[str, ToolResult]]:
    running_tools: dict[str, RunningTool] = {}
    completed_tools: dict[str, ToolResult] = {}
    for spec in CHECKER_SPECS:
        spec.report_path.unlink(missing_ok=True)
        report_handle = spec.report_path.open("w", encoding="utf-8")
        started_at = time.monotonic()
        try:
            process = subprocess.Popen(
                spec.command, stdout=report_handle, stderr=subprocess.STDOUT
            )
        except OSError as error:
            report_handle.close()
            write_start_failure(
                report_path=spec.report_path,
                title=spec.title,
                command=spec.command,
                error=error,
            )
            finished_at = time.monotonic()
            completed_tools[spec.slug] = ToolResult(
                spec=spec,
                exit_code=1,
                started_at=started_at,
                finished_at=finished_at,
                report_stats=read_report_stats(spec.report_path),
            )
            continue
        running_tools[spec.slug] = RunningTool(
            spec=spec,
            process=process,
            report_handle=report_handle,
            started_at=started_at,
        )
    return running_tools, completed_tools


def finish_ready_processes(
    running_tools: dict[str, RunningTool], completed_tools: dict[str, ToolResult]
) -> None:
    finished_slugs: list[str] = []
    for slug, running_tool in running_tools.items():
        exit_code = running_tool.process.poll()
        if exit_code is None:
            continue
        running_tool.report_handle.flush()
        running_tool.report_handle.close()
        finished_at = time.monotonic()
        completed_tools[slug] = ToolResult(
            spec=running_tool.spec,
            exit_code=exit_code,
            started_at=running_tool.started_at,
            finished_at=finished_at,
            report_stats=read_report_stats(running_tool.spec.report_path),
        )
        finished_slugs.append(slug)
    for slug in finished_slugs:
        del running_tools[slug]


def terminate_running_tools(running_tools: dict[str, RunningTool]) -> None:
    for running_tool in running_tools.values():
        if running_tool.process.poll() is None:
            running_tool.process.terminate()
    for running_tool in running_tools.values():
        if running_tool.process.poll() is None:
            running_tool.process.wait(timeout=5)
        running_tool.report_handle.close()


def write_summary(
    cleanup_result: CleanupResult,
    checker_results: tuple[ToolResult, ...],
    wall_started_at: float,
) -> None:
    checker_sum = sum(result.duration_seconds for result in checker_results)
    checker_wall_start = min(
        (result.started_at for result in checker_results),
        default=cleanup_result.finished_at,
    )
    checker_wall_end = max(
        (result.finished_at for result in checker_results),
        default=cleanup_result.finished_at,
    )
    checker_wall = checker_wall_end - checker_wall_start
    total_duration = time.monotonic() - wall_started_at
    slowest_result = max(checker_results, key=lambda result: result.duration_seconds)
    failed_count = sum(1 for result in checker_results if result.exit_code != 0)
    lines = [
        "# Lint And Type Check Timing Summary",
        "",
        f"- Cleanup status: {cleanup_result.status}",
        f"- Cleanup runtime: {format_duration(cleanup_result.duration_seconds)}",
        f"- Cleanup log: `{relative_path(cleanup_result.report_path)}`",
        f"- Checker wall runtime: {format_duration(checker_wall)}",
        f"- Sum of checker runtimes: {format_duration(checker_sum)}",
        f"- Parallel speedup: {checker_sum / checker_wall:.2f}x"
        if checker_wall > 0
        else "- Parallel speedup: 0.00x",
        f"- End-to-end runtime: {format_duration(total_duration)}",
        f"- Failed tools: {failed_count}/{len(checker_results)}",
        f"- Slowest tool: {slowest_result.spec.title} ({format_duration(slowest_result.duration_seconds)})",
        "",
        "| Tool | Status | Exit | Duration | Share | Lines | Size | Report |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for result in sorted(
        checker_results, key=lambda item: item.duration_seconds, reverse=True
    ):
        lines.append(
            f"| {result.spec.title} | {result.status} | {result.exit_code} | {format_duration(result.duration_seconds)} | "
            f"{format_share(result.duration_seconds, checker_sum)} | {result.report_stats.line_count} | "
            f"{format_bytes(result.report_stats.byte_count)} | `{relative_path(result.spec.report_path)}` |"
        )
    SUMMARY_PATH.write_text(data="\n".join(lines) + "\n", encoding="utf-8")


def collect_results(completed_tools: dict[str, ToolResult]) -> tuple[ToolResult, ...]:
    return tuple(completed_tools[spec.slug] for spec in CHECKER_SPECS)


def validate_environment() -> Path:
    repo_root = Path.cwd()
    if REPO_MARKER.exists() is False:
        print(
            "Error: pyproject.toml not found in the current directory. Please run this script from the repo root.",
            file=sys.stderr,
        )
        raise SystemExit(1)
    if shutil.which("uv") is None:
        print("Error: uv is required but was not found on PATH.", file=sys.stderr)
        raise SystemExit(1)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    return repo_root


def main() -> int:
    repo_root = validate_environment()
    console = Console()
    wall_started_at = time.monotonic()
    console.print(
        Panel(
            Text("Linting and type checking suite", style="bold cyan"),
            box=box.DOUBLE,
            border_style="cyan",
        )
    )
    cleanup_result = run_cleanup(console=console)
    running_tools, completed_tools = start_checker_processes()
    try:
        with Live(
            build_live_renderable(
                repo_root=repo_root,
                cleanup_result=cleanup_result,
                running_tools=running_tools,
                completed_tools=completed_tools,
                wall_started_at=wall_started_at,
            ),
            console=console,
            refresh_per_second=12,
            transient=False,
        ) as live:
            while len(running_tools) > 0:
                finish_ready_processes(
                    running_tools=running_tools, completed_tools=completed_tools
                )
                live.update(
                    build_live_renderable(
                        repo_root=repo_root,
                        cleanup_result=cleanup_result,
                        running_tools=running_tools,
                        completed_tools=completed_tools,
                        wall_started_at=wall_started_at,
                    )
                )
                time.sleep(CHECKER_REFRESH_SECONDS)
    except KeyboardInterrupt:
        terminate_running_tools(running_tools=running_tools)
        console.print(
            Panel(
                Text("Interrupted. Running tools were terminated.", style="bold red"),
                border_style="red",
            )
        )
        return 130

    checker_results = collect_results(completed_tools=completed_tools)
    write_summary(
        cleanup_result=cleanup_result,
        checker_results=checker_results,
        wall_started_at=wall_started_at,
    )
    console.print(
        build_final_summary(
            cleanup_result=cleanup_result,
            checker_results=checker_results,
            wall_started_at=wall_started_at,
        )
    )
    console.print(
        Text(f"Reports written under {relative_path(REPORTS_DIR)}", style="bold cyan")
    )
    if cleanup_result.exit_code != 0 or any(
        result.exit_code != 0 for result in checker_results
    ):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
