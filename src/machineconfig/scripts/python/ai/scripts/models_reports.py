import json
from pathlib import Path
from typing import Final

from models import ReportStats, ToolSpec  # type: ignore[import-not-found] # sibling script, resolved at runtime via sys.path


JSON_ENTRY_KEYS: Final[tuple[str, ...]] = (
    "generalDiagnostics",
    "diagnostics",
    "messages",
    "results",
    "violations",
    "errors",
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
        return _format_json_tool_report(
            spec=spec, exit_code=exit_code, raw_output=raw_output
        )
    return _format_text_tool_report(spec=spec, exit_code=exit_code, raw_output=raw_output)


def _format_json_tool_report(spec: ToolSpec, exit_code: int, raw_output: str) -> str:
    stripped_output = raw_output.strip()
    lines = _report_header_lines(spec=spec, exit_code=exit_code)
    if stripped_output == "":
        lines.append("No output was emitted.")
        lines.append("")
        return "\n".join(lines) + "\n"
    try:
        prefix_text, payload = _parse_json_output(raw_output=raw_output)
    except json.JSONDecodeError as error:
        lines.append(f"- JSON parse failure: `{error.msg}`")
        lines.append("")
        lines.append("## Raw Output")
        lines.append("")
        _append_code_block(lines=lines, language="text", content=raw_output)
        lines.append("")
        return "\n".join(lines) + "\n"

    entry_key, entries = _extract_json_entries(payload)
    if entries is None:
        lines.append("- Diagnostic entries: `0`")
        lines.append("")
        if prefix_text != "":
            lines.append("## Prefix")
            lines.append("")
            _append_code_block(lines=lines, language="text", content=prefix_text)
            lines.append("")
        lines.append("## Payload")
        lines.append("")
        _append_code_block(
            lines=lines, language="json", content=json.dumps(payload, indent=2)
        )
        lines.append("")
        return "\n".join(lines) + "\n"

    lines.append(f"- Diagnostic entries: `{len(entries)}`")
    lines.append("")
    if prefix_text != "":
        lines.append("## Prefix")
        lines.append("")
        _append_code_block(lines=lines, language="text", content=prefix_text)
        lines.append("")
    metadata = _extract_json_metadata(payload=payload, entry_key=entry_key)
    if metadata is not None:
        lines.append("## Metadata")
        lines.append("")
        _append_code_block(
            lines=lines, language="json", content=json.dumps(metadata, indent=2)
        )
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
        _append_code_block(
            lines=lines, language="json", content=json.dumps(entry, indent=2)
        )
        lines.append("")
    return "\n".join(lines) + "\n"


def _format_text_tool_report(spec: ToolSpec, exit_code: int, raw_output: str) -> str:
    lines = _report_header_lines(spec=spec, exit_code=exit_code)
    if raw_output.strip() == "":
        lines.append("No output was emitted.")
        lines.append("")
        return "\n".join(lines) + "\n"
    lines.append("## Raw Output")
    lines.append("")
    _append_code_block(lines=lines, language="text", content=raw_output)
    lines.append("")
    return "\n".join(lines) + "\n"


def _report_header_lines(spec: ToolSpec, exit_code: int) -> list[str]:
    return [
        f"# {spec.title}",
        "",
        f"- Command: `{format_command(spec.command)}`",
        f"- Exit code: `{exit_code}`",
        f"- Captured format: `{spec.output_format}`",
        "",
    ]


def _append_code_block(lines: list[str], language: str, content: str) -> None:
    lines.append(f"```{language}")
    lines.extend(content.splitlines())
    lines.append("```")


def _split_json_prefix(raw_output: str) -> tuple[str, str | None]:
    lines = raw_output.splitlines()
    for index, line in enumerate(lines):
        stripped_line = line.lstrip()
        if stripped_line.startswith("{") or stripped_line.startswith("["):
            prefix_text = "\n".join(lines[:index]).strip()
            payload_text = "\n".join(lines[index:]).strip()
            return prefix_text, payload_text
    return "", None


def _parse_json_output(raw_output: str) -> tuple[str, object]:
    stripped_output = raw_output.strip()
    try:
        return "", _parse_json_stream(raw_output=stripped_output)
    except json.JSONDecodeError as error:
        prefix_text, payload_text = _split_json_prefix(raw_output)
        if payload_text is None:
            raise error
        return prefix_text, _parse_json_stream(raw_output=payload_text)


def _parse_json_stream(raw_output: str) -> object:
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


def _extract_json_entries(payload: object) -> tuple[str | None, tuple[object, ...] | None]:
    if isinstance(payload, list):
        return None, tuple(payload)
    if isinstance(payload, dict):
        for key in JSON_ENTRY_KEYS:
            candidate = payload.get(key)
            if isinstance(candidate, list):
                return key, tuple(candidate)
    return None, None


def _extract_json_metadata(
    payload: object, entry_key: str | None
) -> dict[str, object] | None:
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


def write_start_failure(
    report_path: Path, title: str, command: tuple[str, ...], error: OSError
) -> None:
    report_path.write_text(
        data="\n".join(
            (
                f"# {title}",
                "",
                f"- Command: `{format_command(command)}`",
                f"- Start failure: `{error}`",
                "",
            )
        )
        + "\n",
        encoding="utf-8",
    )


def format_command(command: tuple[str, ...]) -> str:
    return " ".join(command)