import atexit
import json
import os
import re
import subprocess
import tomllib
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
JSON_ENTRY_KEYS: Final[tuple[str, ...]] = (
    "generalDiagnostics",
    "diagnostics",
    "messages",
    "results",
    "violations",
    "errors",
)
TYPE_CHECK_EXCLUDES_ENV_VAR: Final[str] = "MACHINECONFIG_TYPE_CHECK_EXCLUDES"
MYPY_EXCLUDE_PATTERN: Final[str] = r"(^|/|\\)gromit-mpx($|/|\\)"
PYRIGHT_CONFIG_PATH: Final[Path] = Path("pyrightconfig.json")
PYPROJECT_PATH: Final[Path] = Path("pyproject.toml")
PYRIGHT_CONFIG_OVERRIDE_PATH: Final[Path] = Path(".machineconfig.pyright.type-check.json")


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


def _remove_generated_file(path: Path) -> None:
    path.unlink(missing_ok=True)


def load_type_check_excluded_directories() -> tuple[str, ...]:
    raw_value = os.environ.get(TYPE_CHECK_EXCLUDES_ENV_VAR)
    if raw_value is None or raw_value == "":
        return ()
    try:
        payload = json.loads(raw_value)
    except json.JSONDecodeError as error:
        raise ValueError(
            f"Invalid {TYPE_CHECK_EXCLUDES_ENV_VAR} value. Expected a JSON array of strings."
        ) from error
    if not isinstance(payload, list):
        raise ValueError(
            f"Invalid {TYPE_CHECK_EXCLUDES_ENV_VAR} value. Expected a JSON array of strings."
        )
    excluded_directories: list[str] = []
    seen_directories: set[str] = set()
    for item in payload:
        if not isinstance(item, str) or item == "":
            raise ValueError(
                f"Invalid {TYPE_CHECK_EXCLUDES_ENV_VAR} value. Expected a JSON array of strings."
            )
        if item in seen_directories:
            continue
        seen_directories.add(item)
        excluded_directories.append(item)
    return tuple(excluded_directories)


def merge_distinct_strings(*groups: tuple[str, ...]) -> tuple[str, ...]:
    merged_values: list[str] = []
    seen_values: set[str] = set()
    for group in groups:
        for value in group:
            if value in seen_values:
                continue
            seen_values.add(value)
            merged_values.append(value)
    return tuple(merged_values)


def build_directory_regex(relative_directory: str) -> str:
    escaped_directory = re.escape(relative_directory).replace("/", r"(/|\\)")
    return rf"(^|/|\\){escaped_directory}($|/|\\)"


def build_combined_regex(patterns: tuple[str, ...]) -> str:
    return "|".join(f"(?:{pattern})" for pattern in patterns)


def append_repeated_option(
    command: list[str], option: str, values: tuple[str, ...]
) -> None:
    for value in values:
        command.extend((option, value))


def parse_jsonc_object(raw_text: str) -> dict[str, object]:
    text_without_comments = "\n".join(
        line for line in raw_text.splitlines() if not line.lstrip().startswith("//")
    )
    normalized_text = re.sub(r",(\s*[}\]])", r"\1", text_without_comments)
    payload = json.loads(normalized_text)
    if not isinstance(payload, dict):
        raise ValueError("Pyright configuration must be a JSON object.")
    return payload


def load_pyright_base_config() -> tuple[dict[str, object], bool]:
    if PYRIGHT_CONFIG_PATH.exists():
        return (
            parse_jsonc_object(PYRIGHT_CONFIG_PATH.read_text(encoding="utf-8")),
            True,
        )
    if PYPROJECT_PATH.exists():
        pyproject_payload = tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))
        tool_section = pyproject_payload.get("tool")
        if isinstance(tool_section, dict):
            pyright_section = tool_section.get("pyright")
            if isinstance(pyright_section, dict):
                return dict(pyright_section), False
    return {}, False


def extract_pyright_excludes(config: dict[str, object]) -> tuple[str, ...]:
    raw_excludes = config.get("exclude")
    if raw_excludes is None:
        return ()
    if not isinstance(raw_excludes, list):
        raise ValueError("Pyright config 'exclude' must be a list of strings.")
    excludes: list[str] = []
    for item in raw_excludes:
        if not isinstance(item, str):
            raise ValueError("Pyright config 'exclude' must be a list of strings.")
        excludes.append(item)
    return tuple(excludes)


def ensure_pyright_config_override(
    excluded_directories: tuple[str, ...],
) -> Path:
    base_config, has_pyright_config = load_pyright_base_config()
    merged_excludes = merge_distinct_strings(
        extract_pyright_excludes(base_config), excluded_directories
    )
    override_config: dict[str, object]
    if has_pyright_config:
        override_config = {
            "extends": f"./{PYRIGHT_CONFIG_PATH.as_posix()}",
            "exclude": list(merged_excludes),
        }
    else:
        override_config = dict(base_config)
        override_config["exclude"] = list(merged_excludes)
    PYRIGHT_CONFIG_OVERRIDE_PATH.write_text(
        json.dumps(override_config, indent=2) + "\n", encoding="utf-8"
    )
    atexit.register(_remove_generated_file, PYRIGHT_CONFIG_OVERRIDE_PATH)
    return PYRIGHT_CONFIG_OVERRIDE_PATH


def build_cleanup_commands(
    excluded_directories: tuple[str, ...],
) -> tuple[tuple[str, ...], ...]:
    excluded_patterns = tuple(
        build_directory_regex(directory) for directory in excluded_directories
    )
    cleanpy_command = ["uv", "run", "--frozen", "--with", "cleanpy", "-m", "cleanpy"]
    append_repeated_option(
        command=cleanpy_command, option="--exclude", values=excluded_patterns
    )
    cleanpy_command.append(".")
    ruff_fix_command = [
        "uv",
        "run",
        "--frozen",
        "--with",
        "ruff",
        "ruff",
        "check",
        "--fix",
    ]
    if len(excluded_directories) > 0:
        ruff_fix_command.append("--force-exclude")
        append_repeated_option(
            command=ruff_fix_command,
            option="--extend-exclude",
            values=excluded_directories,
        )
    ruff_fix_command.append(".")
    return (
        tuple(cleanpy_command),
        ("uv", "run", "--frozen", "--with", "ruff", "-m", "ruff", "clean"),
        tuple(ruff_fix_command),
    )


def build_checker_specs(
    excluded_directories: tuple[str, ...],
) -> tuple[ToolSpec, ...]:
    excluded_patterns = tuple(
        build_directory_regex(directory) for directory in excluded_directories
    )
    mypy_excludes = merge_distinct_strings((MYPY_EXCLUDE_PATTERN,), excluded_patterns)
    pyright_command = [
        "uv",
        "run",
        "--frozen",
        "--with",
        "pyright",
        "pyright",
        "--outputjson",
        "--threads",
        "10",
    ]
    if len(excluded_directories) > 0:
        pyright_command.extend(
            ("--project", str(ensure_pyright_config_override(excluded_directories)))
        )
    pyright_command.append(".")
    mypy_command = ["uv", "run", "--frozen", "--with", "mypy", "mypy", "-O", "json"]
    append_repeated_option(command=mypy_command, option="--exclude", values=mypy_excludes)
    mypy_command.append(".")
    pylint_command = [
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
    ]
    if len(excluded_patterns) > 0:
        pylint_command.extend(
            ("--ignore-paths", build_combined_regex(excluded_patterns))
        )
    pylint_command.append(".")
    pyrefly_command = [
        "uv",
        "run",
        "--frozen",
        "--with",
        "pyrefly",
        "pyrefly",
        "check",
        "--summary=none",
        "--output-format",
        "json",
    ]
    append_repeated_option(
        command=pyrefly_command,
        option="--project-excludes",
        values=excluded_directories,
    )
    pyrefly_command.append(".")
    ty_command = [
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
    ]
    if len(excluded_directories) > 0:
        ty_command.append("--force-exclude")
        append_repeated_option(command=ty_command, option="--exclude", values=excluded_directories)
    ty_command.append(".")
    ruff_command = [
        "uv",
        "run",
        "--frozen",
        "--with",
        "ruff",
        "ruff",
        "check",
        "--output-format",
        "json",
    ]
    if len(excluded_directories) > 0:
        ruff_command.append("--force-exclude")
        append_repeated_option(
            command=ruff_command,
            option="--extend-exclude",
            values=excluded_directories,
        )
    ruff_command.append(".")
    return (
        ToolSpec(
            slug="pyright",
            title="Pyright Type Checker",
            report_path=REPORTS_DIR / "issues_pyright.md",
            command=tuple(pyright_command),
            output_format="json",
        ),
        ToolSpec(
            slug="mypy",
            title="MyPy Type Checker",
            report_path=REPORTS_DIR / "issues_mypy.md",
            command=tuple(mypy_command),
            output_format="json",
        ),
        ToolSpec(
            slug="pylint",
            title="Pylint Code Analysis",
            report_path=REPORTS_DIR / "issues_pylint.md",
            command=tuple(pylint_command),
            output_format="json",
        ),
        ToolSpec(
            slug="pyrefly",
            title="Pyrefly Type Checker",
            report_path=REPORTS_DIR / "issues_pyrefly.md",
            command=tuple(pyrefly_command),
            output_format="json",
        ),
        ToolSpec(
            slug="ty",
            title="Ty Type Checker",
            report_path=REPORTS_DIR / "issues_ty.md",
            command=tuple(ty_command),
            output_format="json",
        ),
        ToolSpec(
            slug="ruff",
            title="Ruff Linter",
            report_path=REPORTS_DIR / "issues_ruff.md",
            command=tuple(ruff_command),
            output_format="json",
        ),
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
    try:
        prefix_text, payload = parse_json_output(raw_output=raw_output)
    except json.JSONDecodeError as error:
        lines.append(f"- JSON parse failure: `{error.msg}`")
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


def parse_json_output(raw_output: str) -> tuple[str, object]:
    stripped_output = raw_output.strip()
    try:
        return "", parse_json_stream(raw_output=stripped_output)
    except json.JSONDecodeError as error:
        prefix_text, payload_text = split_json_prefix(raw_output)
        if payload_text is None:
            raise error
        return prefix_text, parse_json_stream(raw_output=payload_text)


def parse_json_stream(raw_output: str) -> object:
    stripped_output = raw_output.strip()
    if stripped_output == "":
        raise json.JSONDecodeError("Expecting value", raw_output, 0)
    decoder = json.JSONDecoder()
    decoded_items: list[object] = []
    index = 0
    while index < len(stripped_output):
        while index < len(stripped_output) and stripped_output[index].isspace():
            index += 1
        if index >= len(stripped_output):
            break
        payload, end_index = decoder.raw_decode(stripped_output, index)
        decoded_items.append(payload)
        index = end_index
    if len(decoded_items) == 1:
        return decoded_items[0]
    return decoded_items


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
