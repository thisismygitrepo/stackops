from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal, TypeAlias

REPORTS_DIR: Final[Path] = Path(".ai/linters")
SUMMARY_PATH: Final[Path] = REPORTS_DIR / "timing_summary.md"

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
