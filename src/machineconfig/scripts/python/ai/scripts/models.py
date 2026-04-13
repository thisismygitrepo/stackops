import json
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
ToolOutputFormat: TypeAlias = Literal["json", "text"]
SUCCESS_LABEL: Final[Literal["PASS"]] = "PASS"
FAILURE_LABEL: Final[Literal["FAIL"]] = "FAIL"
ISSUES_LABEL: Final[Literal["ISSUES"]] = "ISSUES"
RUNNING_LABEL: Final[Literal["RUNNING"]] = "RUNNING"
DONE_LABEL: Final[Literal["DONE"]] = "DONE"
ERROR_LABEL: Final[Literal["ERROR"]] = "ERROR"
COMPLETED_KIND: Final[Literal["completed"]] = "completed"
START_FAILED_KIND: Final[Literal["start_failed"]] = "start_failed"
JSON_ENTRY_KEYS: Final[tuple[str, ...]] = (
    "generalDiagnostics",
    "diagnostics",
    "messages",
    "results",
    "violations",
    "errors",
)


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
        command=(
            "uv",
            "run",
            "--frozen",
            "--with",
            "pyright",
            "pyright",
            "--outputjson",
            "--threads",
            "10",
            ".",
        ),
        output_format="json",
    ),
    ToolSpec(
        slug="mypy",
        title="MyPy Type Checker",
        report_path=REPORTS_DIR / "issues_mypy.md",
        command=("uv", "run", "--frozen", "--with", "mypy", "mypy", "-O", "json", "."),
        output_format="json",
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
            "--jobs=5",
            "--ignore=.venv",
            "--output-format=json2",
            "--score=n",
            "--reports=n",
            ".",
        ),
        output_format="json",
    ),
    ToolSpec(
        slug="pyrefly",
        title="Pyrefly Type Checker",
        report_path=REPORTS_DIR / "issues_pyrefly.md",
        command=(
            "uv",
            "run",
            "--frozen",
            "--with",
            "pyrefly",
            "pyrefly",
            "check",
            "--no-progress-bar",
            "--summary=none",
            "--output-format",
            "json",
            ".",
        ),
        output_format="json",
    ),
    ToolSpec(
        slug="ty",
        title="Ty Type Checker",
        report_path=REPORTS_DIR / "issues_ty.md",
        command=(
            "uv",
            "run",
            "--frozen",
            "--with",
            "ty",
            "ty",
            "check",
            "--no-progress",
            "--output-format",
            "gitlab",
            ".",
        ),
        output_format="json",
    ),
    ToolSpec(
        slug="ruff",
        title="Ruff Linter",
        report_path=REPORTS_DIR / "issues_ruff.md",
        command=(
            "uv",
            "run",
            "--frozen",
            "--with",
            "ruff",
            "ruff",
            "check",
            "--output-format",
            "json",
            ".",
        ),
        output_format="json",
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


def format_tool_report(spec: ToolSpec, exit_code: int, raw_output: str) -> str:
    if spec.output_format == "json":
        return format_json_tool_report(spec=spec, exit_code=exit_code, raw_output=raw_output)
    return format_text_tool_report(spec=spec, exit_code=exit_code, raw_output=raw_output)


def format_json_tool_report(spec: ToolSpec, exit_code: int, raw_output: str) -> str:
    stripped_output = raw_output.strip()
    lines = report_header_lines(spec=spec, exit_code=exit_code)
    if stripped_output == "":
        lines.append("No output was emitted.")
        lines.append("")
        return "\n".join(lines) + "\n"
    prefix_text = ""
    try:
        payload = json.loads(stripped_output)
    except json.JSONDecodeError as error:
        recovered_prefix, recovered_payload = split_json_prefix(raw_output)
        if recovered_payload is None:
            lines.append(f"- JSON parse failure: `{error.msg}`")
            lines.append("")
            lines.append("## Raw Output")
            lines.append("")
            append_code_block(lines=lines, language="text", content=raw_output)
            lines.append("")
            return "\n".join(lines) + "\n"
        prefix_text = recovered_prefix
        try:
            payload = json.loads(recovered_payload)
        except json.JSONDecodeError as recovered_error:
            lines.append(f"- JSON parse failure: `{recovered_error.msg}`")
            lines.append("")
            lines.append("## Raw Output")
            lines.append("")
            append_code_block(lines=lines, language="text", content=raw_output)
            lines.append("")
            return "\n".join(lines) + "\n"

    entry_key, entries = extract_json_entries(payload)
    if entries is None:
        lines.append("- Diagnostic entries: `0`")
        lines.append("")
        if prefix_text != "":
            lines.append("## Prefix")
            lines.append("")
            append_code_block(lines=lines, language="text", content=prefix_text)
            lines.append("")
        lines.append("## Payload")
        lines.append("")
        append_code_block(lines=lines, language="json", content=json.dumps(payload, indent=2))
        lines.append("")
        return "\n".join(lines) + "\n"

    lines.append(f"- Diagnostic entries: `{len(entries)}`")
    lines.append("")
    if prefix_text != "":
        lines.append("## Prefix")
        lines.append("")
        append_code_block(lines=lines, language="text", content=prefix_text)
        lines.append("")
    metadata = extract_json_metadata(payload=payload, entry_key=entry_key)
    if metadata is not None:
        lines.append("## Metadata")
        lines.append("")
        append_code_block(lines=lines, language="json", content=json.dumps(metadata, indent=2))
        lines.append("")
    lines.append("## Diagnostics")
    lines.append("")
    if len(entries) == 0:
        lines.append("No diagnostics reported.")
        lines.append("")
        return "\n".join(lines) + "\n"
    for index, entry in enumerate(entries, start=1):
        lines.append(f"### Diagnostic {index}")
        lines.append("")
        append_code_block(lines=lines, language="json", content=json.dumps(entry, indent=2))
        lines.append("")
    return "\n".join(lines) + "\n"


def format_text_tool_report(spec: ToolSpec, exit_code: int, raw_output: str) -> str:
    lines = report_header_lines(spec=spec, exit_code=exit_code)
    if raw_output.strip() == "":
        lines.append("No output was emitted.")
        lines.append("")
        return "\n".join(lines) + "\n"
    lines.append("## Raw Output")
    lines.append("")
    append_code_block(lines=lines, language="text", content=raw_output)
    lines.append("")
    return "\n".join(lines) + "\n"


def report_header_lines(spec: ToolSpec, exit_code: int) -> list[str]:
    return [
        f"# {spec.title}",
        "",
        f"- Command: `{format_command(spec.command)}`",
        f"- Exit code: `{exit_code}`",
        f"- Captured format: `{spec.output_format}`",
        "",
    ]


def append_code_block(lines: list[str], language: str, content: str) -> None:
    lines.append(f"```{language}")
    lines.extend(content.splitlines())
    lines.append("```")


def split_json_prefix(raw_output: str) -> tuple[str, str | None]:
    lines = raw_output.splitlines()
    for index, line in enumerate(lines):
        stripped_line = line.lstrip()
        if stripped_line.startswith("{") or stripped_line.startswith("["):
            prefix_text = "\n".join(lines[:index]).strip()
            payload_text = "\n".join(lines[index:]).strip()
            return prefix_text, payload_text
    return "", None


def extract_json_entries(payload: object) -> tuple[str | None, tuple[object, ...] | None]:
    if isinstance(payload, list):
        return None, tuple(payload)
    if isinstance(payload, dict):
        for key in JSON_ENTRY_KEYS:
            candidate = payload.get(key)
            if isinstance(candidate, list):
                return key, tuple(candidate)
    return None, None


def extract_json_metadata(payload: object, entry_key: str | None) -> dict[str, object] | None:
    if not isinstance(payload, dict):
        return None
    metadata: dict[str, object] = {}
    for key, value in payload.items():
        if isinstance(key, str) and key != entry_key:
            metadata[key] = value
    if metadata:
        return metadata
    return None


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
