#!/usr/bin/env -S uv run
# /// script
# dependencies = ["rich"]
# ///


import json
import os
import signal
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from rich import box
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.text import Text

from stackops.scripts.python.ai.scripts import (
    dashboard as dashboard_module,
    models as models_module,
    tool_versions as tool_versions_module,
)
from stackops.scripts.python.ai.scripts.constants import REPORT_SCHEMA_VERSION
from stackops.scripts.python.ai.scripts.models_core import OUTPUT_FAILED_KIND
from stackops.scripts.python.ai.scripts.models_reports import build_tool_report
from stackops.scripts.python.ai.scripts.run_reports import (
    CleanupCommandReport,
    CleanupReport,
    format_timing_report,
)


CHECKER_REFRESH_SECONDS = models_module.CHECKER_REFRESH_SECONDS
CHECKER_SPECS = models_module.CHECKER_SPECS
CLEANUP_COMMANDS = models_module.CLEANUP_COMMANDS
COMPLETED_KIND = models_module.COMPLETED_KIND
DiagnosticSummary = models_module.DiagnosticSummary
FAILURE_LABEL = models_module.FAILURE_LABEL
TOOL_UPGRADE_COMMAND = models_module.TOOL_UPGRADE_COMMAND
REPORTS_DIR = models_module.REPORTS_DIR
REPO_MARKER = models_module.REPO_MARKER
START_FAILED_KIND = models_module.START_FAILED_KIND
SUCCESS_LABEL = models_module.SUCCESS_LABEL
SUMMARY_PATH = models_module.SUMMARY_PATH
TOOL_VERSION_SPECS = models_module.TOOL_VERSION_SPECS
TYPE_CHECK_TOOL_VERSIONS = models_module.TYPE_CHECK_TOOL_VERSIONS
CleanupResult = models_module.CleanupResult
RunningTool = models_module.RunningTool
ToolResult = models_module.ToolResult
ToolVersionResult = models_module.ToolVersionResult
build_diagnostic_summary = models_module.build_diagnostic_summary
format_duration = models_module.format_duration
read_report_stats = models_module.read_report_stats
relative_path = models_module.relative_path
write_start_failure = models_module.write_start_failure
build_command_preview = dashboard_module.build_command_preview
build_final_summary = dashboard_module.build_final_summary
build_live_renderable = dashboard_module.build_live_renderable
ToolVersionResolutionError = tool_versions_module.ToolVersionResolutionError
build_tool_versions_panel = tool_versions_module.build_tool_versions_panel
resolve_tool_versions = tool_versions_module.resolve_tool_versions


def build_subprocess_environment() -> dict[str, str]:
    subprocess_environment = dict(os.environ)
    subprocess_environment.pop("VIRTUAL_ENV", None)
    return subprocess_environment


def remove_temporary_paths(spec: models_module.ToolSpec) -> None:
    for temporary_path in spec.temporary_paths:
        temporary_path.unlink(missing_ok=True)


def run_cleanup(console: Console) -> CleanupResult:
    cleanup_path = REPORTS_DIR / "log_cleanup.json"
    started_at = time.monotonic()
    exit_code = 0
    command_reports: list[CleanupCommandReport] = []
    subprocess_environment = build_subprocess_environment()
    cleanup_command_count = len(CLEANUP_COMMANDS)
    with Progress(
        SpinnerColumn(style="cyan"),
        TextColumn("[bold cyan]{task.description}"),
        BarColumn(bar_width=None),
        TextColumn("{task.completed}/{task.total} finished"),
        TimeElapsedColumn(),
        console=console,
        expand=True,
    ) as progress:
        cleanup_task = progress.add_task(
            description="Starting cleanup commands",
            total=cleanup_command_count,
        )
        for index, command in enumerate(CLEANUP_COMMANDS, start=1):
            progress.update(
                cleanup_task,
                description=f"Cleanup step {index}/{cleanup_command_count} running — waiting for command to finish",
            )
            command_started_at = time.monotonic()
            completed = subprocess.run(
                command,
                env=subprocess_environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            command_reports.append(
                CleanupCommandReport(
                    command=list(command),
                    exitCode=completed.returncode,
                    stdout=completed.stdout or "",
                    stderr=completed.stderr or "",
                    durationSeconds=time.monotonic() - command_started_at,
                )
            )
            if completed.returncode != 0 and exit_code == 0:
                exit_code = completed.returncode
            progress.advance(cleanup_task)
        progress.update(cleanup_task, description="Cleanup commands finished")
    finished_at = time.monotonic()
    report = CleanupReport(
        schemaVersion=REPORT_SCHEMA_VERSION,
        title="Lint And Type Check Cleanup",
        exitCode=exit_code,
        status=SUCCESS_LABEL if exit_code == 0 else FAILURE_LABEL,
        durationSeconds=finished_at - started_at,
        commands=command_reports,
    )
    cleanup_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
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
    unavailable_summary = DiagnosticSummary(
        total_count=0, classifier="unknown", buckets=()
    )
    subprocess_environment = build_subprocess_environment()
    for spec in CHECKER_SPECS:
        spec.report_path.unlink(missing_ok=True)
        spec.report_path.write_text("", encoding="utf-8")
        report_handle = tempfile.TemporaryFile(mode="w+", encoding="utf-8")
        stderr_handle = tempfile.TemporaryFile(mode="w+", encoding="utf-8")
        started_at = time.monotonic()
        try:
            process = subprocess.Popen(
                spec.command,
                env=subprocess_environment,
                stdout=report_handle,
                stderr=stderr_handle,
            )
        except OSError as error:
            report_handle.close()
            stderr_handle.close()
            remove_temporary_paths(spec=spec)
            write_start_failure(spec=spec, error=error)
            finished_at = time.monotonic()
            completed_tools[spec.slug] = ToolResult(
                spec=spec,
                exit_code=1,
                started_at=started_at,
                finished_at=finished_at,
                report_stats=read_report_stats(spec.report_path),
                diagnostic_summary=unavailable_summary,
                result_kind=START_FAILED_KIND,
            )
            continue
        running_tools[spec.slug] = RunningTool(
            spec=spec,
            process=process,
            report_handle=report_handle,
            stderr_handle=stderr_handle,
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
        running_tool.report_handle.seek(0)
        raw_output = running_tool.report_handle.read()
        running_tool.stderr_handle.flush()
        running_tool.stderr_handle.seek(0)
        stderr = running_tool.stderr_handle.read()
        report = build_tool_report(
            spec=running_tool.spec,
            exit_code=exit_code,
            raw_output=raw_output,
            stderr=stderr,
        )
        running_tool.spec.report_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        running_tool.report_handle.close()
        running_tool.stderr_handle.close()
        remove_temporary_paths(spec=running_tool.spec)
        finished_at = time.monotonic()
        completed_tools[slug] = ToolResult(
            spec=running_tool.spec,
            exit_code=exit_code,
            started_at=running_tool.started_at,
            finished_at=finished_at,
            report_stats=read_report_stats(running_tool.spec.report_path),
            diagnostic_summary=build_diagnostic_summary(
                tool_slug=running_tool.spec.slug, raw_output=raw_output
            ),
            result_kind=COMPLETED_KIND if (
                report["status"] in ("ok", "empty")
                and (report["diagnosticCount"] != 0 or exit_code == 0)
            ) else OUTPUT_FAILED_KIND,
        )
        finished_slugs.append(slug)
    for slug in finished_slugs:
        del running_tools[slug]


def terminate_running_tools(running_tools: dict[str, RunningTool]) -> None:
    for running_tool in running_tools.values():
        if running_tool.process.poll() is None:
            running_tool.process.terminate()
    for running_tool in running_tools.values():
        exit_code = running_tool.process.poll()
        if exit_code is None:
            exit_code = running_tool.process.wait(timeout=5)
        running_tool.report_handle.flush()
        running_tool.report_handle.seek(0)
        raw_output = running_tool.report_handle.read()
        running_tool.stderr_handle.flush()
        running_tool.stderr_handle.seek(0)
        stderr = running_tool.stderr_handle.read()
        report = build_tool_report(
            spec=running_tool.spec,
            exit_code=exit_code,
            raw_output=raw_output,
            stderr=stderr,
        )
        running_tool.spec.report_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        running_tool.report_handle.close()
        running_tool.stderr_handle.close()
        remove_temporary_paths(spec=running_tool.spec)


def write_summary(
    cleanup_result: CleanupResult,
    checker_results: tuple[ToolResult, ...],
    tool_version_results: tuple[ToolVersionResult, ...],
    wall_started_at: float,
) -> None:
    SUMMARY_PATH.write_text(
        format_timing_report(
            cleanup_result=cleanup_result,
            checker_results=checker_results,
            tool_version_results=tool_version_results,
            total_duration=time.monotonic() - wall_started_at,
        ),
        encoding="utf-8",
    )


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
    signal.signal(signal.SIGTERM, signal.default_int_handler)
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
    if TYPE_CHECK_TOOL_VERSIONS == "upgrade":
        console.print(
            Panel(
                Text(" ".join(TOOL_UPGRADE_COMMAND)),
                title="Upgrading Tools In uv.lock",
                border_style="cyan",
            )
        )
        upgrade_exit_code = subprocess.run(
            TOOL_UPGRADE_COMMAND, env=build_subprocess_environment(), check=False
        ).returncode
        if upgrade_exit_code != 0:
            console.print(
                Panel(
                    Text(f"uv lock exited with code {upgrade_exit_code}.", style="bold red"),
                    title="Tool Upgrade Failed",
                    border_style="red",
                )
            )
            return 1
    try:
        with console.status(
            f"[bold cyan]Resolving CLI versions (--tool-versions {TYPE_CHECK_TOOL_VERSIONS})"
        ):
            tool_version_results = resolve_tool_versions(
                specs=TOOL_VERSION_SPECS,
                subprocess_environment=build_subprocess_environment(),
            )
    except ToolVersionResolutionError as error:
        console.print(
            Panel(
                Text(str(error), style="bold red"),
                title="CLI Version Resolution Failed",
                border_style="red",
            )
        )
        return 1
    console.print(
        build_tool_versions_panel(
            results=tool_version_results, tool_versions=TYPE_CHECK_TOOL_VERSIONS
        )
    )
    console.print(build_command_preview())
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
        tool_version_results=tool_version_results,
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
        result.status != SUCCESS_LABEL for result in checker_results
    ):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
