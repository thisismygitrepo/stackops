#!/usr/bin/env -S uv run
# /// script
# dependencies = ["rich"]
# ///


import os
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
from rich.text import Text

try:
    import dashboard as dashboard_module  # type: ignore[import-not-found] # sibling script, resolved at runtime via sys.path
    import models as models_module  # type: ignore[import-not-found] # sibling script, resolved at runtime via sys.path
except ModuleNotFoundError:
    from stackops.scripts.python.ai.scripts import (
        dashboard as dashboard_module,
        models as models_module,
    )


CHECKER_REFRESH_SECONDS = models_module.CHECKER_REFRESH_SECONDS
CHECKER_SPECS = models_module.CHECKER_SPECS
CLEANUP_COMMANDS = models_module.CLEANUP_COMMANDS
COMPLETED_KIND = models_module.COMPLETED_KIND
DiagnosticSummary = models_module.DiagnosticSummary
FAILURE_LABEL = models_module.FAILURE_LABEL
ISSUES_LABEL = models_module.ISSUES_LABEL
REPORTS_DIR = models_module.REPORTS_DIR
REPO_MARKER = models_module.REPO_MARKER
START_FAILED_KIND = models_module.START_FAILED_KIND
SUCCESS_LABEL = models_module.SUCCESS_LABEL
SUMMARY_PATH = models_module.SUMMARY_PATH
CleanupResult = models_module.CleanupResult
RunningTool = models_module.RunningTool
ToolResult = models_module.ToolResult
build_diagnostic_summary = models_module.build_diagnostic_summary
format_tool_report = models_module.format_tool_report
format_bytes = models_module.format_bytes
format_diagnostic_distribution = models_module.format_diagnostic_distribution
format_duration = models_module.format_duration
format_share = models_module.format_share
read_report_stats = models_module.read_report_stats
relative_path = models_module.relative_path
write_start_failure = models_module.write_start_failure
build_command_preview = dashboard_module.build_command_preview
build_final_summary = dashboard_module.build_final_summary
build_live_renderable = dashboard_module.build_live_renderable


def build_subprocess_environment() -> dict[str, str]:
    subprocess_environment = dict(os.environ)
    subprocess_environment.pop("VIRTUAL_ENV", None)
    return subprocess_environment


def run_cleanup(console: Console) -> CleanupResult:
    cleanup_path = REPORTS_DIR / "log_cleanup.md"
    started_at = time.monotonic()
    exit_code = 0
    cleanup_chunks: list[str] = []
    subprocess_environment = build_subprocess_environment()
    for command in CLEANUP_COMMANDS:
        cleanup_chunks.append(f"$ {' '.join(command)}\n")
        completed = subprocess.run(
            command,
            env=subprocess_environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        cleanup_chunks.append(completed.stdout or "")
        cleanup_chunks.append("\n")
        if completed.returncode != 0 and exit_code == 0:
            exit_code = completed.returncode
    cleanup_path.write_text("".join(cleanup_chunks), encoding="utf-8")
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
    unavailable_summary = DiagnosticSummary(
        total_count=0, classifier="unknown", buckets=()
    )
    subprocess_environment = build_subprocess_environment()
    for spec in CHECKER_SPECS:
        spec.report_path.unlink(missing_ok=True)
        spec.report_path.write_text("", encoding="utf-8")
        report_handle = tempfile.TemporaryFile(mode="w+", encoding="utf-8")
        started_at = time.monotonic()
        try:
            process = subprocess.Popen(
                spec.command,
                env=subprocess_environment,
                stdout=report_handle,
                stderr=subprocess.STDOUT,
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
                diagnostic_summary=unavailable_summary,
                result_kind=START_FAILED_KIND,
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
        running_tool.report_handle.seek(0)
        raw_output = running_tool.report_handle.read()
        running_tool.spec.report_path.write_text(
            format_tool_report(
                spec=running_tool.spec,
                exit_code=exit_code,
                raw_output=raw_output,
            ),
            encoding="utf-8",
        )
        running_tool.report_handle.close()
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
            result_kind=COMPLETED_KIND,
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
        running_tool.spec.report_path.write_text(
            format_tool_report(
                spec=running_tool.spec,
                exit_code=exit_code,
                raw_output=raw_output,
            ),
            encoding="utf-8",
        )
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
    passed_count = sum(1 for result in checker_results if result.status == SUCCESS_LABEL)
    issue_count = sum(1 for result in checker_results if result.status == ISSUES_LABEL)
    error_count = sum(1 for result in checker_results if result.status == FAILURE_LABEL)
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
        f"- Passed tools: {passed_count}/{len(checker_results)}",
        f"- Tools with issues: {issue_count}/{len(checker_results)}",
        f"- Tool errors: {error_count}/{len(checker_results)}",
        f"- Slowest tool: {slowest_result.spec.title} ({format_duration(slowest_result.duration_seconds)})",
        "",
        "| Tool | State | Outcome | Exit | Duration | Share | Lines | Size | Report |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for result in sorted(
        checker_results, key=lambda item: item.duration_seconds, reverse=True
    ):
        lines.append(
            f"| {result.spec.title} | {result.run_state} | {result.status} | {result.exit_code} | {format_duration(result.duration_seconds)} | "
            f"{format_share(result.duration_seconds, checker_sum)} | {result.report_stats.line_count} | "
            f"{format_bytes(result.report_stats.byte_count)} | `{relative_path(result.spec.report_path)}` |"
        )
    lines.extend(
        (
            "",
            "## Diagnostic Distribution",
            "",
            "| Tool | Outcome | Diagnostics | By | Distribution |",
            "| --- | --- | ---: | --- | --- |",
        )
    )
    for result in checker_results:
        diagnostic_count = str(result.diagnostic_summary.total_count)
        classifier = result.diagnostic_summary.classifier
        distribution = format_diagnostic_distribution(result.diagnostic_summary)
        if result.result_kind == START_FAILED_KIND:
            diagnostic_count = "-"
            classifier = "-"
            distribution = "start failure"
        lines.append(
            f"| {result.spec.title} | {result.status} | {diagnostic_count} | {classifier} | {distribution} |"
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
