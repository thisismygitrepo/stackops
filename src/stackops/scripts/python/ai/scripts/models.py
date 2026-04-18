import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal, TextIO, TypeAlias, cast

try:
    import models_diagnostics as models_diagnostics_module  # type: ignore[import-not-found] # sibling script, resolved at runtime via sys.path
except ModuleNotFoundError:
    from stackops.scripts.python.ai.scripts import (
        models_diagnostics as models_diagnostics_module,
    )


DiagnosticBucket = models_diagnostics_module.DiagnosticBucket
DiagnosticSummary = models_diagnostics_module.DiagnosticSummary
build_diagnostic_summary = models_diagnostics_module.build_diagnostic_summary
format_diagnostic_distribution = (
    models_diagnostics_module.format_diagnostic_distribution
)


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
    diagnostic_summary: DiagnosticSummary
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
        if self.diagnostic_summary.total_count > 0:
            return ISSUES_LABEL
        if self.exit_code == 0:
            return SUCCESS_LABEL
        return ISSUES_LABEL


@dataclass(slots=True)
class RunningTool:
    spec: ToolSpec
    process: subprocess.Popen[bytes]
    report_handle: TextIO
    started_at: float


try:
    import models_config as models_config_module  # type: ignore[import-not-found] # sibling script, resolved at runtime via sys.path
    import models_reports as models_reports_module  # type: ignore[import-not-found] # sibling script, resolved at runtime via sys.path
except ModuleNotFoundError:
    from stackops.scripts.python.ai.scripts import (
        models_config as models_config_module,
        models_reports as models_reports_module,
    )


PYRIGHT_CONFIG_OVERRIDE_PATH = models_config_module.PYRIGHT_CONFIG_OVERRIDE_PATH
TYPE_CHECK_EXCLUDES_ENV_VAR = models_config_module.TYPE_CHECK_EXCLUDES_ENV_VAR
build_checker_specs = models_config_module.build_checker_specs
build_cleanup_commands = models_config_module.build_cleanup_commands
load_type_check_excluded_directories = (
    models_config_module.load_type_check_excluded_directories
)
format_bytes = models_reports_module.format_bytes
format_command = models_reports_module.format_command
format_duration = models_reports_module.format_duration
format_share = models_reports_module.format_share
format_tool_report = models_reports_module.format_tool_report
read_report_stats = models_reports_module.read_report_stats
relative_path = models_reports_module.relative_path
write_start_failure = models_reports_module.write_start_failure


TYPE_CHECK_EXCLUDED_DIRECTORIES: Final[tuple[str, ...]] = (
    load_type_check_excluded_directories()
)
CLEANUP_COMMANDS: Final[tuple[tuple[str, ...], ...]] = build_cleanup_commands(
    TYPE_CHECK_EXCLUDED_DIRECTORIES
)
CHECKER_SPECS: Final[tuple[ToolSpec, ...]] = cast(
    tuple[ToolSpec, ...], build_checker_specs(TYPE_CHECK_EXCLUDED_DIRECTORIES)
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
    "PYRIGHT_CONFIG_OVERRIDE_PATH",
    "REPO_MARKER",
    "REPORTS_DIR",
    "RUNNING_LABEL",
    "START_FAILED_KIND",
    "SUCCESS_LABEL",
    "SUMMARY_PATH",
    "TYPE_CHECK_EXCLUDES_ENV_VAR",
    "TYPE_CHECK_EXCLUDED_DIRECTORIES",
    "CleanupResult",
    "DiagnosticBucket",
    "DiagnosticSummary",
    "ReportStats",
    "RunningTool",
    "ToolResult",
    "ToolSpec",
    "build_diagnostic_summary",
    "format_bytes",
    "format_command",
    "format_diagnostic_distribution",
    "format_duration",
    "format_share",
    "format_tool_report",
    "read_report_stats",
    "relative_path",
    "write_start_failure",
)
