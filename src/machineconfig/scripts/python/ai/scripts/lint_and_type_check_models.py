from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal, TextIO, TypeAlias

import subprocess


REPO_MARKER: Final[Path] = Path("pyproject.toml")
REPORTS_DIR: Final[Path] = Path(".ai/linters")
SUMMARY_PATH: Final[Path] = REPORTS_DIR / "timing_summary.md"
CHECKER_REFRESH_SECONDS: Final[float] = 0.15
CleanupStatus: TypeAlias = Literal["PASS", "FAIL"]
ToolRunState: TypeAlias = Literal["RUNNING", "DONE", "ERROR"]
ToolOutcome: TypeAlias = Literal["PASS", "ISSUES", "FAIL"]
ToolResultKind: TypeAlias = Literal["completed", "start_failed"]
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
        command=("uv", "run", "--frozen", "--with", "pyright", "pyright", "--threads", "10", "."),
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
            "uv", "run", "--frozen", "--with", "pylint", "pylint",
            "--recursive=y", "--jobs=5", "--ignore=.venv", ".",
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
    line_count = len(report_path.read_text(encoding="utf-8", errors="replace").splitlines())
    return ReportStats(line_count=line_count, byte_count=report_path.stat().st_size)


def write_start_failure(report_path: Path, title: str, command: tuple[str, ...], error: OSError) -> None:
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


def format_command(command: tuple[str, ...]) -> str:
    return " ".join(command)
