import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal, TextIO, TypeAlias


REPO_MARKER: Final[Path] = Path("pyproject.toml")
REPORTS_DIR: Final[Path] = Path(".ai/linters")
SUMMARY_PATH: Final[Path] = REPORTS_DIR / "timing_summary.md"
CHECKER_REFRESH_SECONDS: Final[float] = 0.15
CleanupStatus: TypeAlias = Literal["PASS", "FAIL"]
ToolRunState: TypeAlias = Literal["RUNNING", "DONE", "ERROR"]
ToolOutcome: TypeAlias = Literal["PASS", "ISSUES", "FAIL"]
ToolResultKind: TypeAlias = Literal["completed", "start_failed"]
ToolOutputFormat: TypeAlias = Literal["json", "text"]
SUCCESS_LABEL: Final[Literal["PASS"]] = "PASS"
FAILURE_LABEL: Final[Literal["FAIL"]] = "FAIL"
ISSUES_LABEL: Final[Literal["ISSUES"]] = "ISSUES"
RUNNING_LABEL: Final[Literal["RUNNING"]] = "RUNNING"
DONE_LABEL: Final[Literal["DONE"]] = "DONE"
ERROR_LABEL: Final[Literal["ERROR"]] = "ERROR"
COMPLETED_KIND: Final[Literal["completed"]] = "completed"
START_FAILED_KIND: Final[Literal["start_failed"]] = "start_failed"


@dataclass(frozen=True, slots=True)
class ToolSpec:
    slug: str
    title: str
    report_path: Path
    command: tuple[str, ...]
    output_format: ToolOutputFormat


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
    def status(self) -> CleanupStatus:
        if self.exit_code == 0:
            return SUCCESS_LABEL
        return FAILURE_LABEL


@dataclass(frozen=True, slots=True)
class ToolResult:
    spec: ToolSpec
    exit_code: int
    started_at: float
    finished_at: float
    report_stats: ReportStats
    result_kind: ToolResultKind

    @property
    def duration_seconds(self) -> float:
        return self.finished_at - self.started_at

    @property
    def run_state(self) -> ToolRunState:
        if self.result_kind == START_FAILED_KIND:
            return ERROR_LABEL
        return DONE_LABEL

    @property
    def status(self) -> ToolOutcome:
        if self.result_kind == START_FAILED_KIND:
            return FAILURE_LABEL
        if self.exit_code == 0:
            return SUCCESS_LABEL
        return ISSUES_LABEL


@dataclass(slots=True)
class RunningTool:
    spec: ToolSpec
    process: subprocess.Popen[bytes]
    report_handle: TextIO
    started_at: float


from models_config import (  # type: ignore[import-not-found] # sibling script, resolved at runtime via sys.path
    build_checker_specs,
    build_cleanup_commands,
    load_type_check_excluded_directories,
)
from models_reports import (  # type: ignore[import-not-found] # sibling script, resolved at runtime via sys.path
    format_bytes,
    format_command,
    format_duration,
    format_share,
    format_tool_report,
    read_report_stats,
    relative_path,
    write_start_failure,
)


TYPE_CHECK_EXCLUDED_DIRECTORIES: Final[tuple[str, ...]] = (
    load_type_check_excluded_directories()
)
CLEANUP_COMMANDS: Final[tuple[tuple[str, ...], ...]] = build_cleanup_commands(
    TYPE_CHECK_EXCLUDED_DIRECTORIES
)
CHECKER_SPECS: Final[tuple[ToolSpec, ...]] = build_checker_specs(
    TYPE_CHECK_EXCLUDED_DIRECTORIES
)

__all__ = (
    "CHECKER_REFRESH_SECONDS",
    "CHECKER_SPECS",
    "CLEANUP_COMMANDS",
    "COMPLETED_KIND",
    "DONE_LABEL",
    "ERROR_LABEL",
    "FAILURE_LABEL",
    "ISSUES_LABEL",
    "REPO_MARKER",
    "REPORTS_DIR",
    "RUNNING_LABEL",
    "START_FAILED_KIND",
    "SUCCESS_LABEL",
    "SUMMARY_PATH",
    "TYPE_CHECK_EXCLUDED_DIRECTORIES",
    "CleanupResult",
    "ReportStats",
    "RunningTool",
    "ToolResult",
    "ToolSpec",
    "format_bytes",
    "format_command",
    "format_duration",
    "format_share",
    "format_tool_report",
    "read_report_stats",
    "relative_path",
    "write_start_failure",
)
