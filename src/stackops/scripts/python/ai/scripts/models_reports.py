import json
from pathlib import Path

from stackops.scripts.python.ai.scripts.constants import REPORT_SCHEMA_VERSION
from stackops.scripts.python.ai.scripts.models_core import ReportStats, ToolSpec
from stackops.scripts.python.ai.scripts.models_json import (
    extract_json_entries,
    extract_json_metadata,
    parse_json_output,
)
from stackops.scripts.python.ai.scripts.report_schema import ToolReport


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


def format_tool_report(
    spec: ToolSpec, exit_code: int, raw_output: str, stderr: str
) -> str:
    report = build_tool_report(
        spec=spec, exit_code=exit_code, raw_output=raw_output, stderr=stderr
    )
    return json.dumps(report, indent=2, ensure_ascii=False) + "\n"


def build_tool_report(
    spec: ToolSpec, exit_code: int, raw_output: str, stderr: str
) -> ToolReport:
    report = _new_tool_report(spec=spec, exit_code=exit_code, stderr=stderr)
    if raw_output.strip() == "":
        return report
    if spec.output_format == "text":
        report["status"] = "text"
        report["diagnosticCount"] = None
        report["rawOutput"] = raw_output
        return report
    try:
        parsed_output = parse_json_output(raw_output=raw_output, tool_slug=spec.slug)
    except json.JSONDecodeError as error:
        report["status"] = "parse_failed"
        report["diagnosticCount"] = None
        report["rawOutput"] = raw_output
        report["error"] = str(error)
        return report

    report["prefixText"] = parsed_output.prefix_text
    payload = parsed_output.payload
    entry_key, entries = extract_json_entries(payload=payload)
    if entries is None:
        report["status"] = "unrecognized"
        report["diagnosticCount"] = None
        report["payload"] = payload
        report["error"] = "No diagnostic collection found in tool output."
        return report
    report["status"] = "ok"
    report["diagnosticCount"] = len(entries)
    report["toolMetadata"] = extract_json_metadata(payload=payload, entry_key=entry_key) or {}
    report["diagnostics"] = [
        {"diagnosticNumber": index, "diagnosticValue": entry}
        for index, entry in enumerate(entries, start=1)
    ]
    return report


def _new_tool_report(spec: ToolSpec, exit_code: int | None, stderr: str) -> ToolReport:
    return {
        "schemaVersion": REPORT_SCHEMA_VERSION,
        "tool": spec.slug,
        "title": spec.title,
        "command": list(spec.command),
        "exitCode": exit_code,
        "capturedFormat": spec.output_format,
        "status": "empty",
        "diagnosticCount": 0,
        "prefixText": "",
        "stderr": stderr,
        "toolMetadata": {},
        "diagnostics": [],
        "rawOutput": None,
        "payload": None,
        "error": None,
    }


def read_report_stats(report_path: Path) -> ReportStats:
    if report_path.exists() is False:
        return ReportStats(line_count=0, byte_count=0)
    line_count = len(report_path.read_text(encoding="utf-8", errors="replace").splitlines())
    return ReportStats(line_count=line_count, byte_count=report_path.stat().st_size)


def write_start_failure(spec: ToolSpec, error: OSError) -> None:
    report = _new_tool_report(spec=spec, exit_code=None, stderr="")
    report["status"] = "start_failed"
    report["diagnosticCount"] = None
    report["error"] = str(error)
    spec.report_path.write_text(
        data=json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def format_command(command: tuple[str, ...]) -> str:
    return " ".join(command)
