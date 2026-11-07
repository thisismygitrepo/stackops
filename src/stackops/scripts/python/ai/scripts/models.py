import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Final, TextIO

from stackops.scripts.python.ai.scripts import models_diagnostics as models_diagnostics_module
from stackops.scripts.python.ai.scripts import (
    models_config as models_config_module,
    models_reports as models_reports_module,
    tool_versions as tool_versions_module,
)
from stackops.scripts.python.ai.scripts.constants import (
    TYPE_CHECK_TOOLS_ENV_VAR,
    CheckerName,
    ToolVersionMode,
)
from stackops.scripts.python.ai.scripts.models_core import (
    CleanupStatus,
    COMPLETED_KIND,
    DONE_LABEL,
    ERROR_LABEL,
    FAILURE_LABEL,
    ISSUES_LABEL,
    OUTPUT_FAILED_KIND,
    REPORTS_DIR,
    RUNNING_LABEL,
    ReportStats,
    START_FAILED_KIND,
    SUCCESS_LABEL,
    SUMMARY_PATH,
    ToolOutcome,
    ToolResultKind,
    ToolRunState,
    ToolSpec,
)


DiagnosticBucket = models_diagnostics_module.DiagnosticBucket
DiagnosticSummary = models_diagnostics_module.DiagnosticSummary
ToolVersionResult = tool_versions_module.ToolVersionResult
ToolVersionSpec = tool_versions_module.ToolVersionSpec
build_diagnostic_summary = models_diagnostics_module.build_diagnostic_summary
format_diagnostic_distribution = (
    models_diagnostics_module.format_diagnostic_distribution
)


REPO_MARKER: Final[Path] = Path("pyproject.toml")
CHECKER_REFRESH_SECONDS: Final[float] = 0.15


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
        if self.result_kind != COMPLETED_KIND:
            return ERROR_LABEL
        return DONE_LABEL

    @property
    def status(self) -> ToolOutcome:
        if self.result_kind != COMPLETED_KIND:
            return FAILURE_LABEL
        if self.diagnostic_summary.total_count > 0:
            return ISSUES_LABEL
        if self.exit_code == 0:
            return SUCCESS_LABEL
        return FAILURE_LABEL


@dataclass(slots=True)
class RunningTool:
    spec: ToolSpec
    process: subprocess.Popen[bytes]
    report_handle: TextIO
    stderr_handle: TextIO
    started_at: float


PYRIGHT_CONFIG_OVERRIDE_PATH = models_config_module.PYRIGHT_CONFIG_OVERRIDE_PATH
TYPE_CHECK_EXCLUDES_ENV_VAR = models_config_module.TYPE_CHECK_EXCLUDES_ENV_VAR
build_checker_specs = models_config_module.build_checker_specs
build_cleanup_commands = models_config_module.build_cleanup_commands
build_tool_version_specs = tool_versions_module.build_tool_version_specs
load_type_check_tool_versions = models_config_module.load_type_check_tool_versions
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
TYPE_CHECK_TOOL_VERSIONS: Final[ToolVersionMode] = load_type_check_tool_versions()
SELECTED_TYPE_CHECK_TOOLS: Final[tuple[CheckerName, ...]] = (
    models_config_module.parse_type_check_tools(os.environ.get(TYPE_CHECK_TOOLS_ENV_VAR))
)
TOOL_UPGRADE_COMMAND: Final[tuple[str, ...]] = tool_versions_module.build_tool_upgrade_command(
    selected_tools=SELECTED_TYPE_CHECK_TOOLS
)
TOOL_VERSION_SPECS: Final[tuple[ToolVersionSpec, ...]] = build_tool_version_specs(
    tool_versions=TYPE_CHECK_TOOL_VERSIONS, selected_tools=SELECTED_TYPE_CHECK_TOOLS
)
CLEANUP_COMMANDS: Final[tuple[tuple[str, ...], ...]] = build_cleanup_commands(
    excluded_directories=TYPE_CHECK_EXCLUDED_DIRECTORIES,
    tool_versions=TYPE_CHECK_TOOL_VERSIONS,
    selected_tools=SELECTED_TYPE_CHECK_TOOLS,
)
CHECKER_SPECS: Final[tuple[ToolSpec, ...]] = build_checker_specs(
    excluded_directories=TYPE_CHECK_EXCLUDED_DIRECTORIES,
    tool_versions=TYPE_CHECK_TOOL_VERSIONS,
    selected_tools=SELECTED_TYPE_CHECK_TOOLS,
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
    "OUTPUT_FAILED_KIND",
    "PYRIGHT_CONFIG_OVERRIDE_PATH",
    "REPO_MARKER",
    "REPORTS_DIR",
    "RUNNING_LABEL",
    "START_FAILED_KIND",
    "SUCCESS_LABEL",
    "SUMMARY_PATH",
    "TYPE_CHECK_EXCLUDES_ENV_VAR",
    "TYPE_CHECK_EXCLUDED_DIRECTORIES",
    "TYPE_CHECK_TOOL_VERSIONS",
    "TOOL_UPGRADE_COMMAND",
    "TOOL_VERSION_SPECS",
    "CleanupResult",
    "DiagnosticBucket",
    "DiagnosticSummary",
    "ReportStats",
    "RunningTool",
    "ToolResult",
    "ToolSpec",
    "ToolVersionResult",
    "ToolVersionSpec",
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
