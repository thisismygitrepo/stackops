import json
from typing import TypedDict

from stackops.scripts.python.ai.scripts.constants import REPORT_SCHEMA_VERSION
from stackops.scripts.python.ai.scripts.models import CleanupResult, ToolResult, ToolVersionResult
from stackops.scripts.python.ai.scripts.models_core import (
    COMPLETED_KIND,
    FAILURE_LABEL,
    ISSUES_LABEL,
    START_FAILED_KIND,
    SUCCESS_LABEL,
    CleanupStatus,
    ToolOutcome,
    ToolResultKind,
    ToolRunState,
)


class CleanupCommandReport(TypedDict):
    command: list[str]
    exitCode: int
    stdout: str
    stderr: str
    durationSeconds: float


class CleanupReport(TypedDict):
    schemaVersion: int
    title: str
    exitCode: int
    status: CleanupStatus
    durationSeconds: float
    commands: list[CleanupCommandReport]


class CleanupTimingReport(TypedDict):
    status: CleanupStatus
    exitCode: int
    durationSeconds: float
    report: str


class DiagnosticBucketReport(TypedDict):
    label: str
    count: int


class CheckerTimingReport(TypedDict):
    tool: str
    title: str
    state: ToolRunState
    outcome: ToolOutcome
    resultKind: ToolResultKind
    exitCode: int | None
    durationSeconds: float
    sharePercent: float
    lineCount: int
    byteCount: int
    report: str
    diagnosticCount: int | None
    classifier: str | None
    distribution: list[DiagnosticBucketReport]


class SlowestToolReport(TypedDict):
    tool: str
    title: str
    durationSeconds: float


class CliVersionReport(TypedDict):
    title: str
    version: str


class TimingReport(TypedDict):
    schemaVersion: int
    title: str
    cleanup: CleanupTimingReport
    checkerWallSeconds: float
    checkerSumSeconds: float
    parallelSpeedup: float
    durationSeconds: float
    toolCount: int
    passedTools: int
    toolsWithIssues: int
    toolErrors: int
    slowestTool: SlowestToolReport | None
    tools: list[CheckerTimingReport]
    cliVersions: list[CliVersionReport]


def format_timing_report(
    cleanup_result: CleanupResult,
    checker_results: tuple[ToolResult, ...],
    tool_version_results: tuple[ToolVersionResult, ...],
    total_duration: float,
) -> str:
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
    slowest_result = max(checker_results, key=lambda result: result.duration_seconds, default=None)
    checker_reports: list[CheckerTimingReport] = []
    for result in sorted(checker_results, key=lambda result: result.duration_seconds, reverse=True):
        diagnostics_available = result.result_kind == COMPLETED_KIND
        checker_reports.append(
            CheckerTimingReport(
                tool=result.spec.slug,
                title=result.spec.title,
                state=result.run_state,
                outcome=result.status,
                resultKind=result.result_kind,
                exitCode=None if result.result_kind == START_FAILED_KIND else result.exit_code,
                durationSeconds=result.duration_seconds,
                sharePercent=100 * result.duration_seconds / checker_sum if checker_sum > 0 else 0.0,
                lineCount=result.report_stats.line_count,
                byteCount=result.report_stats.byte_count,
                report=f"""./{result.spec.report_path.as_posix()}""",
                diagnosticCount=result.diagnostic_summary.total_count if diagnostics_available else None,
                classifier=result.diagnostic_summary.classifier if diagnostics_available else None,
                distribution=[
                    DiagnosticBucketReport(label=bucket.label, count=bucket.count)
                    for bucket in result.diagnostic_summary.buckets
                ] if diagnostics_available else [],
            )
        )
    report = TimingReport(
        schemaVersion=REPORT_SCHEMA_VERSION,
        title="Lint And Type Check Timing Summary",
        cleanup=CleanupTimingReport(
            status=cleanup_result.status,
            exitCode=cleanup_result.exit_code,
            durationSeconds=cleanup_result.duration_seconds,
            report=f"""./{cleanup_result.report_path.as_posix()}""",
        ),
        checkerWallSeconds=checker_wall,
        checkerSumSeconds=checker_sum,
        parallelSpeedup=checker_sum / checker_wall if checker_wall > 0 else 0.0,
        durationSeconds=total_duration,
        toolCount=len(checker_results),
        passedTools=sum(result.status == SUCCESS_LABEL for result in checker_results),
        toolsWithIssues=sum(result.status == ISSUES_LABEL for result in checker_results),
        toolErrors=sum(result.status == FAILURE_LABEL for result in checker_results),
        slowestTool=None if slowest_result is None else SlowestToolReport(
            tool=slowest_result.spec.slug,
            title=slowest_result.spec.title,
            durationSeconds=slowest_result.duration_seconds,
        ),
        tools=checker_reports,
        cliVersions=[
            CliVersionReport(title=result.spec.title, version=result.version)
            for result in tool_version_results
        ],
    )
    return json.dumps(report, indent=2, ensure_ascii=False) + "\n"
